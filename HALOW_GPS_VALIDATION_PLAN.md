# HaLow and GPS integration validation

Firmware PR: https://github.com/OpenMANET/firmware/pull/74
Packages PR: https://github.com/OpenMANET/packages/pull/27
Daemon PR: https://github.com/OpenMANET/openmanetd/pull/214

Firmware and packages target their respective `1.8.1-dev` branches. The daemon
PR targets `main`. The integration retains current Raven camera work, Pi Zero
2 W firmware, and the merged guarded SPI reset implementation from firmware #72.

## Implemented behavior

- Reload disk-backed wireless UCI before single/batch daemon radio writes and
  invalidate cached network state, preserving external LuCI/CLI edits.
- Keep BATMAN hard-interface choices in Quick Configuration. Restrict bridge
  adjustment to the normal DHCP/static networks managed by that page; AP saves
  must not create `br-batmesh0` or change BATMAN topology.
- Keep GPS `board=auto`. SPI profiles and non-Raven Pi 4/CM4 assume the existing
  Seeed/WM1302 wiring. Other Pi profiles may use detected Seeed identity. Explicit
  disable settings and the UART requirement remain effective. No new carrier
  mode is added; Raven and Gateworks initialization scripts are unchanged.
- Release only the matching GPS GPIO holders using libgpiod's actual process
  arguments. Use an integer delay supported by production BusyBox and report
  failures. BSP release is `1.0-r16`.
- Enable the existing guarded WM6108 SPI boot reset by default.
- Fetch recovered AISCoT/ADSBCOT archives from OpenMANET mirrors with unchanged
  source hashes, original licenses/attribution and the decoder MIT notice.
- Exclude only BCM2708 from GitHub CI discovery; local discovery is unchanged.

## Build and automated verification

The successful local build used firmware `fe7a2b2`, packages
`931f6846694fce7148da17b3795c665caed87d87`, daemon
`9992ab8806ebcd7d88a91f0408378974691fa537` (`main-r5`), and the
`ekh-bcm2711` setup. Setup, download and `make -j8` passed on the first attempt.

All three images passed SHA-256, sysupgrade metadata extraction, gzip integrity
and installed-content checks, including profile drivers, exact GPS scripts,
GPS defaults, BSP r16, daemon r5, pkill, boot entries and LuCI `931f684`.

| Profile | SHA-256 |
|---|---|
| mm6108-sdio | `5d8e1dff75222753bfc3a1c193e7c91187a3497d8e6308cac275eabb0abab4d5` |
| mm6108-spi | `c4e14fc9271e2358ea7d68be2b425b1c8881cf686c0619dae9f01aa41e0f6c76` |
| mm8108-usb | `c2a630e40219a4c5578e0e626ce04ac6ab3bbc99fbc275ceb8ca2462bfe28831` |

Eight GPS board/boot groups, four reset groups, Quick Configuration topology
regressions and existing BATMAN setup tests pass. The topology test reproduces
creation of `br-batmesh0` on the preceding code, preserves the network tree
through repeated SSID changes with the fix, and checks normal bridge creation.
Daemon race tests, lint and CI pass. Fresh TLS-verified downloads and target
builds of AISCoT `7.3.2-r3` and ADSBCOT `9.0.1-r2` pass; those optional packages
are not installed in these Pi images.

CI requested refreshes of five existing bcm27xx patches. The refreshed patches
apply with zero fuzz and produce byte-identical affected kernel source files to
the tested local build; only patch context, positions and formatting change.
Final CI results must be checked separately from the recorded local build.

## Hardware evidence — October 23, 2026

On the Pi/MM6108 SPI device, the operator confirmed completed GPIO17 radio reset,
GPS initialization completion, both GPS GPIO holders at 12 0 and 25 0, and u-blox
NMEA output from `/dev/ttyAMA0`. GPSD restart preserves holders and serial output.

The preceding image reproduced a Quick Configuration defect: an AP SSID save
created `br-batmesh0`, stopped router pings and left network commands hanging.
Deleting only `network.batmesh0.device` and rebooting restored connectivity.

On the replacement image with LuCI `931f684`, changing the onboard AP SSID did
not drop packets. The operator also changed HaLow settings and confirmed that
connectivity returned after matching the downstream settings.

## Remaining limits and merge requirements

GNSS acquisition is deferred: the tested unit has no antenna and reports
`ANTENNA OPEN`. Do not interpret serial output as a successful position fix.
Raven/Gateworks exclusions have automated coverage; they were not hardware-tested
in this session. Three-node multihop and extended soak testing are not recorded.

Merge in dependency order: daemon #214, packages #27, then firmware #74. The daemon
repository requires external approval from someone other than the last pusher.
Review CI on the final commits and preserve traceability of any updated pins.

Local evidence is under `logs/pr74-quick-config-20261023/`,
`logs/source-mirror-validation/` and `logs/pr74-issue-tracking/` (ignored).
