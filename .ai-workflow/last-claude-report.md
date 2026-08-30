# Last Claude Report — Raspberry Pi 5 Port, Session 5

Date: 2026-08-30
Branch: `pi5-wm6108-port` · Baseline: `365b276`
Mode: UART operator — all software-side work done over the 3-pin JST-SH console
(`.ai-workflow/pi5-uart.ps1`, COM4). No owner keystrokes required for any of it.

## Status: §14 Phase 1 re-regression is PARTIAL — blocked on one credential

Phase 1 remains **HARDWARE VERIFIED** from the 2026-08-28 run. This session
re-verified the current image on the live unit. Both subsystems check out
individually; the two-node mesh test could not be completed.

### Verified clean this session

**MM6108 / HaLow** — restored using the image's own shipped one-shot default script
(`/rom/etc/uci-defaults/99_morse_radio_defaults`), not hand-written config. Full
path confirmed: `morse_spi spi0.0` probe → GPIO reset → firmware `mm6108.bin`
(crc32 `0xbe7b5c8f`) → **US BCF `bcf_fgh100mhaamd.bin`** (crc32 `0x941b2a82`) →
`wlh0` up and `AP-ENABLED`. Driver reports `country: US`,
`enable_ext_xtal_init: Y`. `hostapd_s1g` logs `s1g_chan_center=42,
ht_center_chan=159`.

So RP1 → SPI → DW AXI DMA → MM6108 → firmware → BCF is intact on this image.

**RTL8822BU / USB3** — still **SuperSpeed (5000)**, so patch 054 holds across
reboots. AP up on ch36 VHT80; client connected 3350 s at 292.5 Mbit/s VHT-MCS7
NSS1, **0 tx retries**, −27 dBm. Only the known benign reserved-page/beacon pair
appeared — the non-fatal pattern recorded in `8bd27bb`, session unaffected.
Boot-order recovery (patch 0011) confirmed present on-device.

### Why it stopped

**The 802.11s mesh SAE passphrase is unrecoverable and must match the Pi 4.**
`/etc/config/wireless` was regenerated during USB testing, so the passphrase from
the validated Phase 1 run is gone. Inventing one is forbidden by the operator
rules, and a mismatch means the mesh will not associate at all.

### The important finding — do NOT just run the wizard

I traced the LuCI EKH wizard to source and corroborated it against a captured real
before/after UCI dump in `openmanetd-1.3.10/testfixtures/setup-wizard/` (a genuine
Pi 4 + MM6108-over-SPI wizard run). `resetUci()` / `resetUciNetworkTopology()`
(`tools/morse/wizard.js:412-542`) run unconditionally on wizard **entry**, before
any user choice, and would:

- delete every `firewall` rule and replace them with the wizard's own 13
- set the **wan** zone to `input/output/forward=ACCEPT` (stock default is REJECT)
- disable every forwarding, including stock `lan → wan`
- set `ignore=1` on every DHCP pool
- delete every bridge section including `br-lan`, leaving `lan` deviceless
- force `disabled=1` on every wifi-iface and strip `default_radio1` to 7 options
- silently convert the open RTL8822BU AP to `psk2`, then block progress until a
  passphrase is supplied

That is a real security and configuration regression on this box, so the wizard
should not be clicked through blindly here.

**The good news:** the transformation is fully reproducible as a plain `uci` shell
sequence — nothing on the Mesh Point path depends on a live scan, iwinfo probe, or
DOM state. Only three values are random (`ahwlan` IP, `dhcp.ahwlan.start`,
`br-ahwlan` MAC) and they are free choices. So this can be applied over UART with
those pinned, skipping the destructive global resets.

Also worth knowing: `device_mode_meshpoint` is forced to `bridge` in the OpenMANET
fork (`meshwizard.js:485-486`, `readonly = true`), so "Mesh Point" always yields the
bridge topology regardless of the none/extender selection.

### Owner action required (one thing)

Supply the mesh SAE passphrase — or authorise a specific one to be set on **both**
nodes — and confirm the Pi 4 is powered on and provisioned as Mesh Gate with
`mesh_id=openmanet`, channel 42, US.

Be aware: restoring the validated topology necessarily moves the RTL8822BU AP onto
`ahwlan`, which will disconnect whatever is currently associated at `10.41.0.225`.
The intended design merges `lan` and `ahwlan` into one `10.41.0.0/16` network
(`br-ahwlan` carries `eth0` + `bat0`), so a mesh-only partial replay would collide
on the subnet.

### Safety state

Full config backup is on the device at `/root/cfgbak/` (`network`, `wireless`,
`firewall`, `dhcp`, `mesh11sd`, plus `.pre-wizard` copies). The UART console is
independent of networking, so no network change can lock us out.

Authoritative state: `PI5_PORT_STATUS.md`.
