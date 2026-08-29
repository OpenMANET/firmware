# Last Claude Report — Raspberry Pi 5 Port, Session 4

Date: 2026-08-28
Branch: `pi5-wm6108-port` · Baseline: `365b276`

# PHASE 1 COMPLETE — HARDWARE VERIFIED

The Raspberry Pi 5 OpenMANET port is **HARDWARE VERIFIED, not merely BUILD VERIFIED.**
The full physical path is demonstrated on real hardware:

```
Pi 5 -> RP1 -> SPI -> MM6108 -> 923 MHz Wi-Fi HaLow -> 802.11s -> BATMAN-adv -> Pi 4
```

## What was verified on hardware

**Platform:** Pi 5 boots OpenMANET; the dedicated 3-pin JST-SH UART carries
bootloader, kernel AND interactive console at 115200; RP1 initialises; SPI/DW-SSI and
DW AXI DMA initialise.

**Radio:** MM6108 probes on `spi0.0`; GPIO reset works; firmware loads; US BCF
`bcf_fgh100mhaamd.bin` loads; country = US; `wlh0` comes up.

**Mesh:** provisioning creates `wlh0 -> batmesh0 -> bat0 -> br-ahwlan`;
algorithm `BATMAN_V`; Pi 5 as Mesh Point, Pi 4 as Mesh Gate; Mesh ID `openmanet`,
2 MHz, channel 42 / 923 MHz. Station dump: plink ESTAB, authorized/authenticated/
associated yes, ~-46 dBm, ~7.52 Mbps expected throughput. BATMAN neighbour
`a8:dd:9f:4d:c0:e3` via `wlh0` (~7.2); originator table shows the Pi 4.
End-to-end ping Pi 5 -> Pi 4: **4/4, 0% loss, 3.620/3.892/4.105 ms**.

Two pre-hardware calls were vindicated: `CONFIG_DW_AXI_DMAC=y` (without it the SPI
controller would have failed to probe silently) and the `ttyAMA10` console routing.

## Recorded for the next unit

- **The missing `bat0` before provisioning was expected factory/unprovisioned
  behaviour, not a defect.** Nothing in the image — Pi 4 or Pi 5 — creates a batman
  device at boot.
- **Quick Config alone was NOT sufficient** on the Pi 4 to rebuild the BATMAN
  topology; running the **full 802.11s wizard** corrected it. Quick Config does not
  reach `wizard.js:1214 save()` -> `uci.js:444-518`, the only path that creates
  `bat0`/`batmesh0`/`batmesh1` and appends `bat0` to `br-ahwlan`.

## Next hardware-validation areas

1. **Flash the current image first — required before GPS.** The unit that passed
   Phase 1 predates commit `a3b80a1`, so openmanetd still reports GNSS unsupported on
   it and the GPS would look broken for an unrelated reason.

   ```
   C:\AI-Projects\OpenMANET-Pi5\images\openmanet-1.8.0-rpi5-mm6108-spi-squashfs-sysupgrade.img.gz
   sha256 1cfccb4c92020021e8eda9ca481cebecdd55897d4cca47297c47d82605a8d837
   53,401,122 bytes
   ```

   Re-provision with the full wizard afterwards and re-confirm the Phase 1 path.
2. **WM1302 HAT GPS/GNSS** — `patches/ekh-bcm2712/0007` (chip- and SPI-path-agnostic
   `gpsboard.init`) and `0010` (openmanetd GNSS capability) are both unexercised on
   hardware.
3. **External USB Wi-Fi AC dongle** for local EUD/ATAK access. HaLow stays the MANET
   transport; do not redesign around Pi 5 onboard Wi-Fi.
4. **NVMe — deferred** until the core radio / GPS / USB-Wi-Fi stack is validated.

## Housekeeping

`build-ekh-bcm2712` is still not wired into `build-release.yml` — unblocked since the
build went green, but CI wiring cannot be validated without pushing the branch.

Authoritative state: `PI5_PORT_STATUS.md`.
