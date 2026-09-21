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
| Raven | GPS reset works without pkill; carrier-specific GPIO behavior preserved |
| Three-node mesh | Multihop traffic and gateway selection survive repeated AP saves; not just ESTAB peering |
| L76K versus supported u-blox module | Raw/read-only/normal experiment establishes whether scoped GPSD changes are needed |

Reproduce external UCI edits while openmanetd remains alive, followed by an AP-only save. Capture before/after wireless and network configs, browser request endpoint/payload, installed binary version, batctl if/neighbors/gateways, and per-node traffic. Check both LuCI and daemon UI routes; the current daemon API has no writable band field.

Build the reported rpi4-mm8108-usb profile using scripts/openmanet_setup.sh and the repository's board profile mapping; follow the workspace .codex clean-build instructions if a clean rebuild is needed. Confirm the resulting image's package versions and command availability, not only .config. No target hardware was accessed during this investigation.
