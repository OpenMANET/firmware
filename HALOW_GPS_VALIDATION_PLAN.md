# HaLow/GPS integration plan (issues 1–4)

Investigation branch: investigate/halow-band-gps, based on fix/wm6108-spi-reset at 54f8880. No build or image changes yet. Pre-existing untracked scripts/tests is outside this work. Issue 5 excluded.

The packages feed currently pins dc866bd143d9502b5201b34eec7183ef7bc86a37. Stack the integration MR on fix/wm6108-spi-reset, after the daemon cache-preservation and GPS board/reset fixes are ready. Update package feed and daemon source/version pins to reviewed commits, with package release bumps as needed. Do not merge a no-fix hypothesis into receiver defaults without the controlled experiment.

Related plans:
- ../openmanetd/docs/halow-gps-investigation.md
- ../packages/investigations/halow-gps/README.md

Validation matrix:

| Configuration | Required evidence |
|---|---|
| Reported CM4 + MM8108 USB + WM1302 | GPS initialized automatically after reboot; correct wake/reset waveform; AP settings changes preserve batmesh0 and wlh0 active |
| SPI HaLow + WM1302 | Existing radio/GPS boot paths remain functional |
| Raspberry Pi without WM1302 | GPS-specific pins not claimed based solely on radio or UART presence |
| Raven | Installed pkill releases reset requests; carrier-specific GPIO behavior preserved |
| Three-node mesh | Multihop traffic and gateway selection survive repeated AP saves; not just ESTAB peering |
| L76K versus supported u-blox module | Raw/read-only/normal experiment establishes whether scoped GPSD changes are needed |

Reproduce external UCI edits while openmanetd remains alive, followed by an AP-only save. Capture before/after wireless and network configs, browser request endpoint/payload, installed binary version, batctl if/neighbors/gateways, and per-node traffic. Check both LuCI and daemon UI routes; the current daemon API has no writable band field.

Build the reported rpi4-mm8108-usb profile using scripts/openmanet_setup.sh and the repository's board profile mapping; follow the workspace .codex clean-build instructions if a clean rebuild is needed. Confirm the resulting image's package versions and command availability, not only .config. No target hardware was accessed during this investigation.

## Implemented build inputs

- Packages branch: fix/halow-gps, commit b76405d86439bd5a70ffa21e8e0ad391a7f287b9.
- Daemon branch: fix/halow-gps, commit e639e9a7ed6c2d590059c723078217bc41fa23b6 (pinned by that packages commit).
- Both tracked feeds.conf.default and the local active feeds.conf use the same packages commit. The old local source override was saved under logs/halow-gps before replacing it.
- GPIO initialization defaults to HAT identity detection. Synthetic identity fixtures pass; actual WM1302 EEPROM data is not yet available. Missing identity skips GPIO manipulation; verified boards without EEPROM data can explicitly set gpsd.core.board=wm1302.
- Both BSPs install procps-ng and procps-ng-pkill. GPSD read-only mode is available but remains off by default; issue 4 acquisition behavior needs hardware diagnosis.
- Fresh configuration exposed an OpenVLM sound-core dependency cycle; the package now explicitly selects sound-core. Regenerated config selects bsp-bcm271x, procps-ng, procps-ng-pkill, gpiod-tools, gpsd and openmanetd.

Pre-build checks: daemon full host build, internal unit suite, integration suite, vet, full golangci-lint (0 issues), and network/handler race tests passed. Package GPIO/identity/migration and GPSD argument tests passed. Profile: ekh-bcm2711 (MM8108 USB and MM6108 SPI/SDIO).

## Build results — 2026-09-21

Build passed with firmware input commit edf9634 on fix/halow-gps, packages b76405d86439bd5a70ffa21e8e0ad391a7f287b9 and daemon e639e9a7ed6c2d590059c723078217bc41fa23b6. This report is a documentation-only follow-up to the built firmware inputs.

The ekh-bcm2711 profile produced all three images under bin/targets/bcm27xx/bcm2711/. The final make -j8 exited 0. The daemon's upstream submodule SSH URLs required a scoped HTTPS rewrite for download and build:

```sh
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=url.https://github.com/.insteadOf GIT_CONFIG_VALUE_0=git@github.com: make -j8
```

No global Git configuration was changed. Build log: logs/halow-gps/build-retry.log (local, ignored). The earlier attempt failed retrieving SSH submodules; the retry succeeded.

| Image | SHA-256 |
|---|---|
| openmanet-1.8.1-rpi4-mm6108-sdio-squashfs-sysupgrade.img.gz | b9a5d49833c975fb2fcfa3516989f617c502779592fbbb7c22357714b4df06a9 |
| openmanet-1.8.1-rpi4-mm6108-spi-squashfs-sysupgrade.img.gz | 16fba210cf7ca5ff78cd5b520bdedbae40fe6e2340de2f9eb7ef24a88fbe63c1 |
| openmanet-1.8.1-rpi4-mm8108-usb-squashfs-sysupgrade.img.gz | 616860fd9125025946718e3164895447a9a6a63d16f3d358ce703964652a336d |

All three image hashes match sha256sums. All three gzip payload integrity checks passed after fwtool extracted the appended sysupgrade metadata. USB image inspection verified:

- Installed gpsboard.init and gpsd scripts exactly match the committed packages sources.
- gpsd.core.board defaults to auto and readonly defaults to 0.
- BSP 1.0-r12, GPSD 3.25-r4, procps-ng and procps-ng-pkill 4.0.4-r1, daemon main-r3.
- ARM64 daemon embeds version main-e639e9a; the feed buildinfo records packages b76405d.
- pkill executable and alternative symlink are present; development Go commands are absent.
- MM8108 USB driver is present and MM6108 driver absent from the USB image.
- GPS board boot service S21, GPSD S50, and board-selection migration script are installed.

Local evidence: logs/halow-gps/usb-image-verification.log, usb-daemon-buildinfo.txt, gps-tests.log, daemon-race.log and daemon-targeted-lint.log.

Hardware validation remains outstanding: actual WM1302 EEPROM identity/provisioning, GPS reset waveform, L76K acquisition, and mesh traffic after AP saves. Auto detection was tested with synthetic HAT identities; missing or unmatched identity leaves GPIOs untouched. Explicit gpsd.core.board=wm1302 remains available for a verified carrier without usable EEPROM identity. Read-only GPSD is a diagnostic option, not a confirmed acquisition fix. Issue 5 remains excluded.
