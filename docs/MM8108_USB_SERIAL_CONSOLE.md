# MM8108 USB timeouts caused by the GPS serial console

## Fix

The Raspberry Pi image command line no longer enables `console=serial0`.
OpenMANET's GPS service uses this UART, which resolves to `/dev/ttyAMA0` on
the tested hardware. Sharing it with the kernel console can delay USB interrupt
handling long enough to time out the MM8108 transport.

The `tty1` and optional `ttyUSB0,115200` consoles remain configured. Kernel
messages remain available through `dmesg` and the system log. GPS, radio power,
firmware, driver timeouts, and driver parameter logging are unchanged.

This changes the default for bcm27xx images. Serial-header kernel output is no
longer available by default. A dedicated debug UART must not also be used by GPS;
simply restoring the old console argument recreates the tested failure condition.

## Controlled reproduction on manet03, November 8, 2026

Hardware: Raspberry Pi 4B, MM8108 USB, xHCI. Driver: 2.2.3-g270da473.
Firmware CRC: 15d8d055. GPS and the PL011 console shared ttyAMA0 at 9,600 baud.
All observed xHCI interrupts were handled by CPU 0.

Linux's PL011 console writer disables local interrupts while transmitting and
waiting for the transmitter to drain. The Morse USB URB timeout is 250 ms.

We generated the installed boot-banner output once (503 bytes) and wrote it to
`/dev/kmsg`, pinning only the writer process to a specified CPU. Independent
management used conventional Wi-Fi directly to manet03. Before/after CLI
statistics, kernel logs, USB transfers, boot IDs, console settings, serial speed,
and mesh state were retained. Each sequence stopped at its first failure.

| Condition | Banner write | Result |
| --- | ---: | --- |
| Serial console enabled, console level 4, CPU 0 | 0.020 ms | Pass |
| Serial console enabled, console level 7, CPU 1 | 790.726 ms | Pass |
| Serial console enabled, console level 7, CPU 0 | 872.166 ms | USB failure |
| Serial console removed, console level 7, CPU 0 | 0.055–0.057 ms | Eight consecutive passes |
| Original serial console restored, console level 7, CPU 0 | 936.606 ms | Failure on first attempt |
| Serial console removed again, console level 7, CPU 0 | 0.054–0.074 ms | Eight more consecutive passes |

The first failed trace contains a bulk-OUT transfer delayed 820.113 ms while
the banner was being printed. The driver reported a timeout, then overflow
(`-75`) and repeated timeout/cancellation errors (`-110`/`-2`). CLI statistics
failed even though the station table still reported an established peer.
Therefore peer presence alone is not a sufficient recovery check.

With the serial console removed, GPS remained at 9,600 baud and full console
level 7 and parameter logging remained enabled. All eight matching USB traces
had zero completion errors and zero collector-reported drops; the longest
matched bulk-OUT completion was 0.070 ms. Some captures retained a few queued
tail events when collection ended, so this is not a claim of exhaustive tail
capture. Restoring the original console argument brought back the failure.

The live-node change edits only `/boot/cmdline.txt` and requires a reboot.
Back up the original file first, remove only `console=serial0`, and preserve the
root partition arguments and remaining consoles. Do not replace the entire file
with another node's command line. Verify `/proc/consoles` after reboot.

## Scope and remaining validation

This establishes a host-side cause and a fix for the reproduced enumerated-device
USB transport failure. It does not prove that every historical startup fault
shares this cause, nor does it explain devices disappearing from USB enumeration.
Manet02 was unavailable during this test. The earlier logging-sensitive
firmware-version timeout did not recur in eight fixed-console warm starts on
manet01; that is supporting evidence, not proof that every startup fault is fixed.

The source change matches the live boot-argument intervention. No new firmware
image has yet been built or flashed for this change. Both fixed-configuration boots completed without captured USB completion errors.
The second eight-trial series also passed at 9,600 baud, with zero recorded USB
completion errors or collector drops and a maximum matched bulk-OUT delay of
0.060 ms. Final CLI statistics and three mesh-peer pings succeeded. The fix
remains applied on manet03; temporary boot recorders are disabled. This validates
the reproduced mode on manet03; manet01 validation is recorded below.

Raw evidence is retained locally under
`/home/jmcgeeal/openmanet/usb-startup-investigation/`, including
`CAUSAL-USB-REPRODUCTION.md`, `manet03-banner-cpu-20261108/`,
`manet03-no-serial-cpu-validation/`, and `manet03-serial-restored-cpu/`.
The prior investigation is documented in [MORSE_2.2_USB_AUDIT.md](MORSE_2.2_USB_AUDIT.md).

## Independent reproduction on manet01 (CM4 / DWC2)

Management used native Ethernet, independent of HaLow. With the serial console
still enabled, the fourth repeated CPU-0 banner test failed at 4,800 baud:
the 845-byte write took 2,427.484 ms, and a matched bulk-OUT transfer took
2,382.029 ms. The driver reported `-110` and firmware command timeouts while
USB remained enumerated. The late USB completion had status zero, demonstrating
why zero USB completion errors alone do not exclude a driver wait timeout.
GPS changed UART speed between trials; this comparison does not assume fixed baud.

Removing only `console=serial0` and restarting produced a recorded boot with
34,139 USB completions, zero completion errors and zero collector drops.
Eight CPU-0 banner trials then passed: writes took 0.066–0.076 ms, maximum
matched bulk-OUT duration was 0.149 ms, and captures had zero completion errors
or collector drops. Sampled UART speeds included 9,600 baud.

Eight additional driver unbind/bind starts with full parameter logging enabled
also passed. Matched firmware-version responses arrived in 1.652–2.653 ms;
all eight collectors reported zero dropped or queued events. The prior
`log_modparams_on_boot=0` mitigation was then removed, restoring default logging
(`Y`). CLI statistics succeeded. Initial pings during interface recovery failed;
a subsequent BATMAN ping and IP pings in both directions passed three of three.
These are short health checks, not a multicast performance measurement.

During the induced failure, network-management commands blocked and ordinary
forced reboot did not finish within 40 seconds. Saved blocked-task stacks and
logs show repeated failed coredump reads. After preserving evidence and syncing
files, emergency software restart succeeded without physical power cycling.
The coredump implementation continues through 235 regions after individual read
errors; prolonged recovery is a separate follow-up, not a proven permanent
lock deadlock. USB disappearance from enumeration remains unexplained.

The console fix remains applied on both tested nodes. Temporary boot recorders
are disabled; their inactive helper files and evidence remain available.
Manet01 evidence: `manet01-banner-cpu-repeat/`,
`manet01-no-serial-console-01/`, `manet01-no-serial-cpu-validation/`, and
`manet01-no-serial-warm-probes/` under the local investigation directory.
No newly built firmware image has been tested.

## Recovery follow-up: measured failed-read sequence

The preserved manet01 blocked-task log contains 215 failed region reads at
215 distinct addresses, from uptime 65767.631928 to 65907.628967: an observed
139.997039-second span. This is a partial retained log, not total recovery time.
The SysRq task snapshot was taken during that sequence. Several network clients
were waiting on RTNL or netlink locks; stripped module addresses prevent complete
identification of the lock owners from this snapshot alone.

Source inspection confirms `elf_copy_memory_regions()` continues to the next
region after a read failure. Watchdog recovery holds `mors->lock` around its
restart procedure, but checks chip access before attempting a coredump. Therefore
this path must not be generalized to every startup/probe failure. The actual
call chain holding the blocked locks still needs confirmation.

A bounded follow-up can compare recovery with the runtime `enable_coredump`
parameter disabled, preserving the USB trace and first-fault kernel log in both
conditions. It must restore the parameter afterward; suppressing crash evidence
is not proposed as the production fix. If this isolates the delay, a candidate
source fix should stop further memory reads on transport-fatal errors while
preserving a valid partial dump. That candidate has not been implemented or
validated. The console fix remains the only intentional live-node change.

The machine has only about 223 MiB free, so a full image rebuild has not been
attempted. Source and live boot arguments match, but image-level validation is
still outstanding. Raw recovery counts are in local `recovery-read-audit.json`.

## Goal completion audit

The goal's stated completion gate is a supported diagnosis and repeatably
validated fix for a clearly identified failure mode, with remaining distinct
modes explicitly tracked. That gate is satisfied for console-induced,
still-enumerated MM8108 USB transport failure. It is not a claim that all USB
faults have been eliminated.

| Requirement | Authoritative evidence and outcome |
| --- | --- |
| Supported diagnosis, not only passing tests | CPU-0 failure versus CPU-1 and suppressed-console controls on manet03; enabled/removed/restored/removed console sequence; independent CM4 reproduction on manet01; matching delayed USB transfers and PL011 interrupt-disabled console source. |
| Repeatable live fix | 16 CPU-0 fixed-console trials on manet03 and eight on manet01 passed. Raw USB traces were reparsed during the audit: zero completion errors in all 24 fixed trials. Eight full-logging warm starts also passed. |
| Independent management and first-fault preservation | Conventional Wi-Fi directly to manet03; native Ethernet to manet01. Trial scripts preserve USB/kernel evidence and stop at first failure; boot IDs and capture loss accounting retained. |
| Account for older manet03 teardown | Console changes used full node reboot, not blind interface restarts. Warm unbind/bind experiments were confined to manet01. |
| Distinguish firmware-response timing | Matched version replies recorded; eight fixed-console starts responded within 1.652–2.653 ms. Earlier logging-sensitive timeout is not declared universally resolved. |
| Distinguish USB disappearance | No claim of reproduction or fix. Manet02 remains unreachable at its last known address, 10.41.31.159. Include it when available. |
| Restore temporary changes | Current node snapshots confirm full logging Y, coredumps Y, console level 7, and both temporary boot recorders disabled. Prior manet01 logging-suppression UCI setting removed. Only the intentional boot-console fix remains. |
| Preserve and document source change | Firmware diff removes only console=serial0; documentation includes rollback implications. Diff whitespace check passes. No commit, flash, or full image build claimed. |
| Keep separate from multicast | Short pings and CLI reads are health checks only. No multicast-performance conclusion is drawn. |

Current-state snapshots are saved locally as
`completion-state-192.168.1.73.txt` and `completion-state-10.41.1.1.txt` in the
investigation directory. Both nodes answered CLI statistics successfully; final
manet01-to-manet03 IP health check passed three of three.

Remaining work is explicitly tracked: (1) natural startup/long-run characterization,
(2) USB-enumeration disappearance when reproducible, (3) bounded recovery after
transport failure and coredump read errors, (4) manet02 validation when reachable,
and (5) a new firmware-image build/flash after disk space is available. These are
not represented as solved by this validated console change.

## Built image validation on manet01

The November 8, 2026 BCM2711 build packaged the console fix. Manet01
accepted the MM8108 USB image and its installed filesystem, boot kernel,
and Morse module hashes matched the artifact. The first boot and one
controlled restart passed with zero recorded USB completion errors.
Eight CPU 0 banner trials passed with full driver logging and a maximum
matched USB bulk-OUT completion of 0.193 ms. Final CLI diagnostics and
three mesh pings passed after temporary instrumentation was disabled.

Image SHA-256:
`955b4a0557888288255b318b14410e77efeb91085781518314171cec2c00a27f`.

The earlier audit above describes the state before this build. The local
hardware validation report, image, and traces are in
`/home/jmcgeeal/openmanet/image-console-fix-20261108/`. The USB traces
begin shortly after firmware load and cover the delayed banner. The
kernel logs cover enumeration and probe. USB disappearance and prolonged
recovery remain separate follow-up work.

## Recovery image follow-up

The later BCM2711 recovery image combines the console change, the GPS lock
fix and the bounded MM8108 coredump path. Its SHA-256 is
`b8acb3c298ab404e8bca9c8d75f13f425ec3fe724706e98ddbee6b12f7cdef58`.
The installed root filesystem and production Morse module were verified
on manet01 and manet03.

- **Slow transport recovery.** In a matched manet01 hardware test, injected
  timeouts stalled wired network queries with the read cutoff disabled.
  Enabling the cutoff ended coredump reads after one failed region.
  Firmware restarted and the CLI returned in 2.255 seconds. The partial
  ELF contained 704,512 bytes of chip memory and its 596-byte note area.
  The normal production dump exported all 235 memory regions. The lab
  driver was removed and the production driver hash was verified.
- **GPS backup lock.** The BCM271x GPS boot hook launches GPIO holders
  without the procd wrapper. On both test nodes the holders retained
  GPIO12 and GPIO25 without inheriting the service lock, and settings
  backups completed. Manet03 supplied position reports with a 3D fix
  after booting the packaged hook.
- **USB enumeration.** A single guarded port cycle restored a logically
  removed MM8108 on manet01's DWC2 controller and manet03's xHCI controller.
  On manet01 a DWC2 controller rebind also restored a logically removed
  parent hub and both downstream devices. These are recovery results for
  controlled host-side absence. The spontaneous disappearance that has
  survived a software reboot remains open.

Preserve a kernel log and topology snapshot before resetting a missing
device. Check the host controller, parent hub, sibling devices and port
status separately. The guarded bench procedures require an independent
management link and known USB topology. A host-reported port-power state
does not establish that the radio supply was physically removed.

The image, prior rollback images, private settings backups and detailed
test evidence remain in the local
`/home/jmcgeeal/openmanet/remaining-fixes-20261108/` directory and its
referenced investigation directories. See `USB-RECOVERY.md` there for
the test boundaries, board-specific recovery procedures and rollback.
