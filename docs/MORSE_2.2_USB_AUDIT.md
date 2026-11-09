# MM8108 USB initialization audit

Current status: see [MORSE_2.2_HANDOFF.md](MORSE_2.2_HANDOFF.md) for November 5 hardware results. Historical pending-test statements below describe the state at each build date.

Audit date: 2026-11-02 (America/Denver). Scope: the exact failing image and
workspace-only initialization tracing. No device was flashed by this audit.

## Result

The tested image contains the intended upstream MM8108 2.2.3 driver and firmware.
No substituted firmware or missing USB frontend was found. The first hardware
failure cannot be localized to a particular address from the existing logs.
A diagnostic-only patch and successfully cross-compiled module are prepared to
capture that information. This is not a root-cause fix or a hardware-validated build.

The USB memory read/write functions and ELF segment loader are byte-for-byte
unchanged between upstream mm8108-2.0.0 and mm8108-2.2.3. The MM8108 digital-reset,
slow-clock enable, and PMU-disable functions are unchanged after symbol renaming.
The firmware payload and other initialization details do change. A broad claim
that the new reset implementation itself caused the failure is not established.

## Exact build and payload

- Firmware build commit: `63724b0be32ce9d3abb06b49e2214be220f38254`.
- Packages commit: `0005a14dcbb3a19bc9459373ab98b9e04e41c7d6`.
- Image: `bin/targets/bcm27xx/bcm2711/openmanet-1.8.1-rpi4-mm8108-usb-squashfs-sysupgrade.img.gz`.
- Image SHA256: `5404d380cad4001db96dcca13ce35777dab433b39c9d288b1655e45fae34b540`.
- Extracted `morse.ko`: `4e61dbe100ac9a3dad887efb48f46db31dfde5ba2fac3297f49482ed23859b37`.
- Extracted firmware: `44ebafb072c480f5df1cdd72549893265f23812567ea3777340cdf3217acb72e`.
- Extracted `bcf_boardtype_0807.bin`: `263f840958785e0664f6735f605963c352e253bc285dcc30061c48a7371b248a`.

The image rootfs verification script passes. Both downloaded source archives
match the hashes in `scripts/morse-2.2/sources.json`.

The driver tag resolves to `270da4733cd4dc62e78e897746f98f6dfb3bef80`, with MMRC
submodule `9d4d6fe3db2dc64690c42bc0e67a7f3783858ca4`.
Firmware commit `db4b69fd212990c59c5f1712e23060cbb94276ec` is upstream's
"Firmware binaries for 2.2 releases" commit, currently on `main`. No 2.2 firmware
tag or GitHub release entry was advertised during this audit. The actual binary
contains `rel_mm8108_2_2_3_2026_Oct_13`, is 506120 bytes, and matches the device's
reported CRC `0x15d8d055`.

The retained 0807 BCF comes from `morse-board-config mm8108-2.0.0-r1` and matches
both devices' prior working calibration. It differs from the newer upstream
`bcf/morsemicro/bcf_mf15457.bin` (SHA256
`500f0c02be66d6601d3a7da58022472d7ca62241950c8dcde95e27a9f7ae761d`).
That is a compatibility question, not proof of a fault. Both firmware and BCF
"Loaded ..." messages occur when files are requested from the host filesystem,
before their contents have successfully been transferred to the chip.

## Build options and patch inventory

The recorded Kbuild invocation uses kernel 6.6.138 and mac80211 backports 6.12.61:
USB=y, SDIO=y, SPI=n, SDIO alignment=4, user access=y, vendor commands=y,
MMRC=y, monitor=y, debugfs=y, country=US, power-save default=0.
Upstream also compiles FullMAC support by default; runtime selection is through
`enable_wiphy`, whose default is 0. Compiled FullMAC support does not mean the
FullMAC firmware was selected: this image uses `mm8108b2-rl.bin`, not `-flm-rl.bin`.
`dot11ah` is integrated into `morse.ko` upstream in 2.2; the absent separate
`dot11ah.ko` is intentional.

The six patches in the failing build are:

| Patch | Area affected |
| --- | --- |
| 008 | Disable dynamic regulatory changes in mac.c |
| 016 | BCF country fallback in firmware.c |
| 017 | AP/STA channel-switch behavior |
| 018 | Disable automatic VIF creation |
| 019 | Channel-ignore boolean handling |
| 030 | Respect packaged version string |

None edits usb.c, mm81xx.c, the ELF segment loader, or the digital-reset sequence.
The removed SPI-delay patch is irrelevant to this USB frontend. The removed TX
queue patch concerns post-initialization traffic, not firmware download.

The installed image still has hostapd_s1g 2.0.0-r6, wpa_supplicant_s1g 2.0.0-r3,
and morsecli 2.0.0-r8. These need later compatibility validation. The reproduced
failure happens inside kernel probe, before interface creation or mesh setup,
so userspace configuration is not the first failing operation in these logs.

Later ACK-timeout work exists in the package checkout and installed feed, including
package release 2 and patch 040. It was NOT in the tested release-1 image. The
diagnostic build reconstructs only the exact six patches at 0005a14 and leaves
that later work untouched.

## Failure path

The USB probe validates chip access, then calls `morse_firmware_prepare()` with
`reset_hw=false`. It requests the firmware and BCF, extracts firmware metadata,
and enters up to three initialization attempts:

1. Digital reset: enable internal slow clock, disable PMU CPU control, issue USB
   non-destructive reset, wait the configured reset delay (400 ms).
2. Optional chip pre-load hook, invalidate host pointer, download ELF load segments.
3. Set the security manifest pointer and boot address, then transfer BCF data.
4. Trigger firmware, obtain host table, verify magic and compatibility.

The visible first failure is `morse_usb_mem_write error -2` followed by
`morse_usb_dm_write failed`. Either an ELF segment write or BCF write can reach
this path; the existing messages do not identify which. Later boot-register and
retry-reset operations time out. The slow-clock/PMU/reset failures printed later
are not proof that those operations failed before the initial write.

For a data write, the driver sends a command containing direction/address/length,
submits a bulk data URB, and waits 250 ms. On timeout it calls `usb_kill_urb()`.
The completion callback stores the cancellation status, potentially `-ENOENT`
(-2), which is then printed as a write error. Thus -2 here can describe a canceled
USB transfer, not a missing firmware file. Instrumentation is needed to distinguish
that path from other cancellation/completion causes.

Two pre-existing error-propagation weaknesses can obscure the first failure:

- `morse_usb_cmd()` can return the requested command length after the completion
  callback stored an error, without propagating that callback error.
- `morse_firmware_load()` breaks after a segment error but continues manifest and
  boot-address processing; the boot-address result can overwrite the prior error.

Both behaviors also exist in 2.0. They are not independently established as the
2.2 regression. The diagnostic patch observes them without changing returns,
timeouts, retry counts, firmware data, or transfer sizes.

The two firmware ELF files contain 14 PT_LOAD segments at the same base addresses
and entry point `0x2a0080`, but their lengths/content differ. In particular the
segment at `0x2a0000` grows from 11432 to 21712 bytes, crossing the USB 16 KiB
chunk boundary. This is a candidate to inspect, not an identified failing segment.
Other segments already exceeded 16 KiB in 2.0.

## Diagnostic artifact and validation

Patch: `scripts/morse-2.2/diagnostics/050-usb-init-diagnostics.patch`.
Reproduction: `python3 scripts/morse-2.2/diagnostics/build.py` from this tree.
The script requires a fresh diagnostic destination and reuses the recorded
successful Kbuild command and existing normal build toolchain. It compiles an
isolated external module under `build_dir/morse22-diagnostic/diagnostic/`.
This is a module compile check, not a replacement image-build workflow.

Version marker: `2.2.3-g270da473-diag1`. Logs have the prefix `MM22DIAG` and include
attempt number, initialization stage/results, segment address/length, BCF transfer,
boot-address write, and USB failure address/length/endpoint/submission/timeout/
completion status/actual length. They do not dump firmware payloads or keys.
Logging is deliberately visible without changing the global debug mask. It may
affect timing, so any eventual reproduction must account for that limitation.

Cross-compilation and module linking passed using the original build flags, with no
compiler warnings. Diagnostic module SHA256:
`56058ddc3df4c79f59eb9c2989e071c76e9fa0128c78d96332b932dfb97736a5`.
No hardware execution or fix validation has occurred. At the isolated-module audit stage, the original downloadable image was unchanged.
The normal image build described below now supersedes that output; no diagnostic
module has been installed on a device.
Raw inventory and build logs are in `logs/morse-2.2/audit-2026-11-02/`.

The next hardware experiment should collect the first `MM22DIAG` failure on one
node. Do not change firmware, BCF, timeout, and driver logic simultaneously. If the
failure precedes BCF transfer, deprioritize the BCF mismatch. If it consistently
hits a specific ELF segment/chunk, investigate that chip memory range and payload
with upstream. A successful build alone cannot settle these questions.

## Upstream references

- https://github.com/MorseMicro/morse_driver/tree/mm8108-2.2.3
- https://github.com/MorseMicro/morse_driver/compare/mm8108-2.0.0...mm8108-2.2.3
- https://github.com/MorseMicro/morse-firmware/commit/db4b69fd212990c59c5f1712e23060cbb94276ec

## Normal diagnostic image build (2026-11-03)

MM8108 USB diagnostic image, built 2026-11-03

Driver version: 2.2.3-g270da473-diag1; package release: 1.diag1.
This adds MM22DIAG startup logging; it is not a validated fix.
Normal firmware build: board setup ekh-bcm2711, dependency download,
make -j8 V=sc. No image repacking. No device flashed.
Firmware and BCF are byte-identical to the original 2.2 image.
Compared with that image, rootfs file content changes are limited to morse.ko,
its package metadata (control/status), and LuCI script cache query strings.

Driver source: 270da4733cd4dc62e78e897746f98f6dfb3bef80
Firmware source: db4b69fd212990c59c5f1712e23060cbb94276ec
Baseline package recipes: 0005a14dcbb3a19bc9459373ab98b9e04e41c7d6
Packaged module SHA256:
fc04c5c1da8e078a2112bbcdbf1038ed6492d11b097c76f5bdd2f87e5ef332ec

The floating openmanetd main download could not refresh its SSH submodules.
The original cached source was pinned by SHA256 for this build:
3554664da9d8d55a0222dcb3349c199b7e8560af7fe42ea59ba5b5249db1b263
Its files are unchanged in the rootfs comparison.

Build logs, exact diagnostic package recipes, previous outputs and rootfs
comparison: firmware/logs/morse-2.2/diag1-image/
Preexisting feed edits were restored after the build. To reproduce this
particular diagnostic, use diagnostic-build-recipes from that log directory,
plus firmware/scripts/morse-2.2/diagnostics/050-usb-init-diagnostics.patch.

Validation passed: normal build, generated checksums, rootfs --diagnostic
checks, artifact checks, gzip integrity after removing the OpenWrt trailer.
Hardware validation remains pending. Capture full dmesg after boot and retain
MM22DIAG entries, especially the first failure.

Image: `bin/targets/bcm27xx/bcm2711/diagnostics/openmanet-1.8.1-rpi4-mm8108-usb-morse-2.2.3-diag1-squashfs-sysupgrade.img.gz`.

Image SHA256: `8194f4d578e51473edaefb78d093fcddb2d7b7ccf7293c1f3be85ca9a9560546`.

## Hardware result and next experiment (2026-11-04)

The user tested diag1 on manet01 (CM4, DWC2, USB hub 1a40:0201).
Capture: attachment 42d76ca6-db60-42d3-92ae-c90b4938018c.
Both the first probe and the startup module reload completed on attempt 1.
All 14 segments, including the 21712-byte segment at 0x002a0000, returned 0.
BCF transfer, firmware trigger, host-table lookup and magic verification passed.
The wlh0 AP appeared and its bridge entered forwarding state. The follow-up at
about two minutes showed no Morse transfer failures; no clients were associated.
This establishes startup success, not mesh/traffic stability or a root cause.

The diag2 experiment removes all successful-path MM22DIAG printing and reset
helper instrumentation from diag1, retaining only usb.c failure logging. No
explicit delay, timeout, transfer-size, firmware, BCF or return-value changes
are introduced. In particular, this does not test a guessed arbitrary delay.
If the original failure returns, USB failure messages should identify its
address, length, submission state, timeout and completion status. If diag2 also
works, repeatability and hardware state remain competing explanations; the
single diag1 success cannot establish that logging was responsible.

Source patch: scripts/morse-2.2/diagnostics/051-usb-failure-diagnostics.patch.
This patch replaces 050; do not apply them together. Driver version suffix:
-diag2, package release 1.diag2. The successful diag1 image is preserved in
bin/targets/bcm27xx/bcm2711/diagnostics/ for comparison.

### Packaged diag2 result

MM8108 USB diag2 startup experiment, 2026-11-04
Image SHA256: 0a424995c408b72f132dfe830e491668d9d2d8721785e973acd4f71092b81708
Driver: 2.2.3-g270da473-diag2, package 1.diag2
Packaged module SHA256: da32f2b14b47bb13888422ea322297b897bc13b17aa8d3da057800a5cc21ab5e

Normal ekh-bcm2711 setup, make download, make -j8 V=sc completed.
Initial restricted-network attempts failed fetching dependencies; the network-enabled
retry succeeded. See firmware/logs/morse-2.2/diag2-image/ for full logs and recipes.
The successful-path logs in diag1 were removed. Only USB failure logging remains.
No explicit delays, timeout, firmware, calibration or transfer-size changes.
Rootfs content comparison with diag1: only morse.ko, its control/status metadata,
and the LuCI header script cache query strings changed. Firmware/BCF unchanged.
Rootfs diagnostic checks, artifact checks and generated checksums passed.
Hardware testing is pending. No device flashed by the build process.
Previous working diag1 image is retained alongside this image.

Build uses the same baseline package recipes and pinned cached openmanetd source
as diag1. Preexisting feed edits restored after build. Reproduction recipes are
saved in logs/morse-2.2/diag2-image/mm8108-driver and mm6108-driver; apply only
the failure diagnostic patch, not both diagnostic patches.

Download path: `bin/targets/bcm27xx/bcm2711/diagnostics/openmanet-1.8.1-rpi4-mm8108-usb-morse-2.2.3-diag2-squashfs-sysupgrade.img.gz`.
