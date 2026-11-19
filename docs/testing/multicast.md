# Test multicast delivery on a batman-adv mesh

Use this opt-in hardware test to compare how a single sender delivers the same IPv4 multicast stream to one or more receivers. Run it from a Linux workstation against a test mesh. The workload sends 50 short packets (96-byte payloads) and 10 larger packets (512-byte payloads) per second. Each carries a trial identifier and a sequence number.

| Trial | Traffic path | What it checks |
|---|---|---|
| Disabled | UDP to the test group on the mesh bridge with the sender’s BATMAN multicast optimization disabled | Group delivery through the mesh and its forwarding overhead |
| Enabled | Same group, bridge, listeners and offered load with optimization enabled | Which frames BATMAN emits for this topology and whether each receiver gets the stream |
| Raw | One broadcast Ethernet frame per sequence directly on the selected radio interface | One-hop group delivery below BATMAN; BATMAN stays attached and its background traffic continues |

## Prepare the nodes and workstation

- Choose a sender and at least one directly reachable radio peer. For a fanout comparison, use two receiving **nodes**. All participants need the same interface names and a probe built for their CPU/ABI. Run separate comparisons for different radios, keeping channel, width, placement and firmware fixed across trials.
- Use SSH aliases or `user@host` destinations with key/agent authentication and verified host keys. The accounts need privileges to create raw sockets, capture frames and change BATMAN settings. Check access with `ssh -o BatchMode=yes "$SENDER" id`. SSH jump hosts and ports can be set per alias in the workstation’s SSH config.
- Each node needs `ip` and `batctl`. The sender also needs `tcpdump` with outgoing Ethernet capture (`-Q out`). Each node needs a writable, executable `/tmp`. The workstation needs Python 3.8+, OpenSSH and `tshark`.
- Choose the **IP-bearing bridge** used by applications (or the BATMAN mesh interface if that carries the IP directly). Choose the underlying **BATMAN hard interface** for the radio. Inspect `ip -br addr`, `batctl meshif "$MESH" interface` and `batctl meshif "$MESH" originators` on the nodes. Confirm the receivers are reachable through the mesh and that routes have converged before starting a run. On a dual-radio mesh, make sure the selected radio carries the test paths or interpret its capture as partial. For a multi-hop receiver the raw control measures only direct radio reachability.
- The test joins IPv4 group `239.255.42.99` on UDP port `39081` and uses experimental EtherType `0x88b5` for raw frames. Reserve the test port and avoid concurrent runs on the same nodes. Changing the sender’s runtime multicast setting affects other traffic there during each trial.

Build the probe from the firmware checkout on the workstation. This example targets a 64-bit ARM Linux node; choose a compatible compiler for other targets. A static binary avoids a target C library dependency.

```sh
aarch64-linux-gnu-gcc -std=c11 -O2 -Wall -Wextra -Werror -static \
  tests/hardware/multicast/probe.c -o /tmp/multicast-probe
```

## Run

Set the variables below to your SSH destinations and device names. Change the sender between invocations to test the reverse direction. Each invocation requires a new output directory.

```sh
SENDER='root@sender.example'
RECEIVER_A='root@receiver-a.example'
RECEIVER_B='root@receiver-b.example'
MESH=bat0
BRIDGE=br-mesh
HARDIF=mesh0

python3 tests/hardware/multicast/run.py \
  --sender "$SENDER" --receivers "$RECEIVER_A" "$RECEIVER_B" \
  --mesh "$MESH" --bridge "$BRIDGE" --hardif "$HARDIF" \
  --probe /tmp/multicast-probe --seconds 10 --settle 10 --repeat 2 \
  --output ./multicast-run
```

The runner uploads temporary files over SSH, joins the receivers before sending, and waits the specified settle time for membership and forwarding changes. Each repetition exercises both BATMAN settings and the raw control. The order of the two BATMAN trials reverses on alternate repetitions. Each receiver allows a bounded startup and drain window. The sender records its original multicast setting in the trial’s `sender.log` and restores it at the end of each BATMAN trial. Restoration runs on the sender even if the workstation disconnects while the remote script completes. If the sender loses power or the remote shell is forcibly killed, check the current setting against the log before resuming. The runner removes its temporary staging directories when reachable.

## Interpret the output

- Per-node `.inventory` files record the kernel and BATMAN versions, selected interfaces and initial routes.
- `summary.csv` reports submitted packets, unique receives, missing sequence numbers and duplicate deliveries per receiver. A socket submission does not establish successful RF delivery. The files ending in `.sequences` contain the received IDs and copy counts.
- `out.pcap` captures outbound Ethernet frames on the sender’s selected hard interface. `forwarding.json` counts frames containing that trial’s marker by **outer** Ethernet destination (group or unicast). The same sender counts appear on each receiver row; count them once. An enabled setting alone does not establish that BATMAN emitted unicast copies. Check group membership, route, fanout and forwarding headers if the observed mode differs from expectations.
- `capture.log` reports capture drops. A capture with drops or no tagged frames needs investigation before drawing forwarding conclusions. The capture includes other matching BATMAN or experimental Ethernet traffic; inspect before sharing.
- To compare airtime, gather separate PHY-level measurements covering actual rates, acknowledgments, retransmissions and relay transmissions. Hard-interface frame counts alone measure none of those costs. For voice evaluation, add a receiver-side timing or playout measurement; sequence loss alone does not measure latency.
