#!/usr/bin/env python3
"""Compare group forwarding and raw broadcast on an existing mesh."""
import argparse
import csv
import json
from pathlib import Path
import re
import secrets
import selectors
import shlex
import signal
import subprocess
import sys
import time
from contextlib import ExitStack


def ssh(host, command):
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
            "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2",
            host, command]


def run(host, command, **kwargs):
    return subprocess.run(ssh(host, command), check=True, timeout=kwargs.pop("timeout", 15),
                          **kwargs)


def wait_ready(processes):
    with selectors.DefaultSelector() as pending:
        for proc in processes:
            pending.register(proc.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + 8
        while pending.get_map():
            events = pending.select(max(0, deadline - time.monotonic()))
            if not events:
                raise RuntimeError("Receiver startup timed out")
            for key, _ in events:
                if key.fileobj.readline() != b"ready\n":
                    raise RuntimeError("Receiver failed to start")
                pending.unregister(key.fileobj)


def stop(proc):
    if proc.poll() is None:
        proc.kill()
    proc.wait()
    proc.stdout.close()


def capture_counts(pcap, token):
    marker = b"OMCT" + token.to_bytes(4, "big")
    command = ["tshark", "-n", "-r", str(pcap), "-Y", "frame contains " + marker.hex(":"),
               "-T", "fields", "-e", "eth.dst", "-E", "occurrence=f"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    counts = {"group": 0, "unicast": 0}
    for address in result.stdout.splitlines():
        group = int(address.split(":")[0], 16) & 1
        counts["group" if group else "unicast"] += 1
    return counts


def trial(args, remote, folder, mode):
    token = secrets.randbits(32)
    raw = mode == "raw"
    count = args.seconds * 60
    folder.mkdir()
    with ExitStack() as stack:
        processes = {}
        for host in args.receivers:
            cmd = shlex.join([remote + "/probe", "recv", "raw" if raw else "udp",
                              args.hardif if raw else args.bridge, str(token),
                              str(args.seconds), "60", "50"])
            proc = subprocess.Popen(ssh(host, "exec " + cmd), stdout=subprocess.PIPE)
            stack.callback(stop, proc)
            processes[host] = proc
        wait_ready(processes.values())
        cmd = shlex.join(["sh", remote + "/send.sh", remote, args.mesh, args.hardif,
                          args.bridge, mode, str(token), str(args.seconds), str(args.settle)])
        with (folder / "sender.log").open("wb") as log:
            run(args.sender, cmd, stdout=log, stderr=subprocess.STDOUT,
                timeout=args.seconds + args.settle + 25)
        with (folder / "out.pcap").open("wb") as out:
            run(args.sender, f"cat {remote}/out.pcap", stdout=out, timeout=90)
        capture_log = run(args.sender, f"cat {remote}/capture.log", capture_output=True).stdout
        (folder / "capture.log").write_bytes(capture_log)
        counts = capture_counts(folder / "out.pcap", token)
        (folder / "forwarding.json").write_text(json.dumps(counts) + "\n")
        if not sum(counts.values()) or not re.search(rb"(?m)^0 packets dropped by kernel", capture_log):
            print(f"{folder}: incomplete forwarding evidence; inspect capture.log and route",
                  file=sys.stderr)
        rows = []
        for host, proc in processes.items():
            output, _ = proc.communicate(timeout=args.seconds + 40)
            if proc.returncode:
                raise RuntimeError(f"Receiver failed: {host}")
            (folder / f"{host}.sequences").write_bytes(output)
            seen = dict(tuple(map(int, line.split())) for line in output.splitlines())
            duplicates = sum(n - 1 for n in seen.values())
            rows.append([folder.name, host, count, len(seen), count - len(seen), duplicates,
                         counts["group"], counts["unicast"]])
        return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sender", required=True)
    parser.add_argument("--receivers", nargs="+", required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--mesh", default="bat0")
    parser.add_argument("--bridge", required=True)
    parser.add_argument("--hardif", required=True)
    parser.add_argument("--seconds", type=int, default=10)
    parser.add_argument("--settle", type=int, default=10)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    hosts = [args.sender, *args.receivers]
    if len(set(hosts)) != len(hosts) or any(
            not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.@-]*", h) for h in hosts):
        parser.error("use distinct SSH aliases or user@host destinations")
    if any(not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,14}", iface)
           for iface in (args.mesh, args.bridge, args.hardif)):
        parser.error("invalid network interface")
    if not (1 <= args.seconds <= 600 and 0 <= args.settle <= 15 and args.repeat >= 1):
        parser.error("seconds must be 1–600, settle 0–15, repeat positive")
    subprocess.run(["tshark", "--version"], check=True, stdout=subprocess.DEVNULL)
    binary = args.probe.read_bytes()
    script = Path(__file__).with_name("send.sh").read_bytes()
    args.output.mkdir(mode=0o700)
    remote = "/tmp/openmanet-multicast-" + secrets.token_hex(8)
    staged = []
    try:
        for host in hosts:
            run(host, f"umask 077 && mkdir {remote}")
            staged.append(host)
            run(host, f"cat > {remote}/probe && chmod 700 {remote}/probe", input=binary)
        run(args.sender, f"cat > {remote}/send.sh", input=script)
        for host in hosts:
            command = (f"uname -r && batctl -v && ip link show dev {args.hardif} && "
                       f"ip -4 addr show dev {args.bridge} && "
                       f"batctl meshif {args.mesh} interface && batctl meshif {args.mesh} originators")
            with (args.output / f"{host}.inventory").open("wb") as inventory:
                run(host, command, stdout=inventory)
        with (args.output / "summary.csv").open("w", newline="") as out:
            writer = csv.writer(out)
            writer.writerow(["trial", "receiver", "sent", "unique", "missing", "duplicates",
                             "sender_group_frames", "sender_unicast_frames"])
            for i in range(args.repeat):
                order = ("disabled", "enabled") if i % 2 == 0 else ("enabled", "disabled")
                for mode in (*order, "raw"):
                    folder = args.output / f"{i + 1}-{mode}"
                    writer.writerows(trial(args, remote, folder, mode))
                    out.flush()
    finally:
        for host in staged:
            try:
                run(host, f"rm -rf {remote}")
            except (OSError, subprocess.SubprocessError) as exc:
                print(f"Cleanup failed on {host} for {remote}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        sys.exit(f"Multicast test failed: {exc}")
