#!/usr/bin/env python3
"""Offline: merge patched overlays with four compiled base DTBs and run the
production detector against those DTs, with the mock GPIO backend only.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def overlay_source(patch, name):
    text = patch.read_text().split("+++ b/arch/arm/boot/dts/overlays/" + name + "\n", 1)[1]
    text = text.split("--- /", 1)[0]
    return "\n".join(line[1:] for line in text.splitlines() if line.startswith("+") and not line.startswith("+++")) + "\n"


def props(dt, node="/"):
    values = {}
    for name in run("fdtget", "-p", str(dt), node).splitlines():
        if name:
            values[node + ":" + name] = run("fdtget", "-t", "bx", str(dt), node, name)
    for child in run("fdtget", "-l", str(dt), node).splitlines():
        if child:
            values.update(props(dt, node.rstrip("/") + "/" + child))
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-tree", type=Path, required=True)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--headers", required=True)
    parser.add_argument("--dtmerge", required=True, help="Raspberry Pi utils dtmerge (handles firmware overlay semantics)")
    opts = parser.parse_args()
    firmware = Path(__file__).resolve().parents[2]
    patch = firmware / "target/linux/bcm27xx/patches-6.6/991-0003-dt-overlays-morse-add-spi-overlay-fragment.patch"
    source = overlay_source(patch, "mm610x-spi-overlay.dts")
    boards = ["bcm2710-rpi-3-b", "bcm2710-rpi-zero-2-w", "bcm2711-rpi-cm4", "bcm2711-rpi-4-b"]
    bsp = opts.packages / "boards/bsp-bcm271x"
    with tempfile.TemporaryDirectory(prefix="wm6108-overlays-") as temp:
        tmp = Path(temp)
        binary = tmp / "detector"
        subprocess.run(["gcc", "-Wall", "-Wextra", "-Werror", "-DUNIT_TESTING", "-I", opts.headers,
                        str(bsp / "src/wm6108-spi-reset.c"), str(bsp / "tests/mock-gpiod.c"),
                        "-Wl,-l:libfdt.so.1", "-o", str(binary)], check=True)
        overlays = {"new": source, "baseline": source.replace("\t\t\t\topenmanet,wm6108-reset;\n", ""),
                    "mm8108": overlay_source(patch, "mm810x-spi-overlay.dts")}
        for name, text in overlays.items():
            subprocess.run(["dtc", "-q", "-@", "-I", "dts", "-O", "dtb", "-o", str(tmp / (name + ".dtbo"))],
                           input=text, text=True, check=True)
        for board in boards:
            base = opts.kernel_tree / "arch/arm64/boot/dts/broadcom" / (board + ".dtb")
            merged = {}
            for mode in overlays:
                dt = tmp / (board + "-" + mode + ".dtb")
                subprocess.run([opts.dtmerge, str(base), str(dt), str(tmp / (mode + ".dtbo"))], check=True)
                merged[mode] = dt
            spi = run("fdtget", "-t", "s", str(merged["new"]), "/aliases", "spi0")
            radio = spi + "/mm6108@0"
            gpio = run("fdtget", "-t", "s", str(merged["new"]), "/__symbols__", "gpio")
            phandle = run("fdtget", "-t", "u", str(merged["new"]), gpio, "phandle")
            for prop, expect in [("reset-gpios", "17 0"), ("spi-irq-gpios", "5 0")]:
                value = run("fdtget", "-t", "u", str(merged["new"]), radio, prop)
                assert value.split(" ", 1)[0] == phandle, (board, prop, "wrong provider")
                assert value.split(" ", 1)[1] == expect, (board, prop, value)
            assert run("fdtget", "-t", "u", str(merged["new"]), radio, "power-gpios") == f"{phandle} 23 0 {phandle} 24 0"
            a, b = props(merged["baseline"]), props(merged["new"])
            assert b.pop(radio + ":openmanet,wm6108-reset") == ""
            assert a == b, f"unexpected effective DT change on {board}"
            for mode, dt in [*merged.items(), ("usb-no-overlay", base)]:
                root = tmp / (board + "-" + mode)
                for suffix in ["tmp", "etc", "sys/firmware", "sys/bus/gpio/devices/gpiochip73",
                               "sys/firmware/devicetree/base" + radio,
                               "sys/firmware/devicetree/base" + gpio]:
                    (root / suffix).mkdir(parents=True, exist_ok=True)
                (root / "etc/wm6108-spi-reset.conf").write_text("enabled=1\n")
                (root / "sys/firmware/fdt").write_bytes(dt.read_bytes())
                (root / "sys/bus/gpio/devices/gpiochip73/of_node").symlink_to(root / ("sys/firmware/devicetree/base" + gpio))
                p = subprocess.run([str(binary), "--boot"], env={**os.environ, "TEST_ROOT": str(root)},
                                   capture_output=True, text=True, check=True)
                assert ("completed" in p.stdout) == (mode == "new"), (board, mode, p.stdout)
                if mode != "new": assert not (root / "events").exists()
            print(f"PASS {board}: merged DT changes only opt-in; correct reset/IRQ; detector accepts WM6108 only")
        usb = firmware / "target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm810x-usb.txt"
        assert all(not l.strip() or l.startswith("#") for l in usb.read_text().splitlines())
        print("PASS MM8108 USB transport fragment still adds no overlays")


if __name__ == "__main__":
    main()
