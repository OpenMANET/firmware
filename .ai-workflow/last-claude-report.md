# Last Claude Report — Raspberry Pi 5 Port, Session 3

Date: 2026-08-28
Branch: `pi5-wm6108-port` · Head: `a3b80a1` · Baseline: `365b276`

## COMPLETED

### HARDWARE VERIFIED — the Pi 5 MM6108-over-SPI path works on real hardware

Pi 5 boots; serial console on the dedicated 3-pin JST-SH debug UART as `ttyAMA10` at
115200; RP1 initialises; DW AXI DMA initialises; MM6108 probes on `spi0.0`; GPIO
reset succeeds; MM6108 firmware loads; correct US BCF `bcf_fgh100mhaamd.bin` loads;
radio reports `country=US`; `wlh0` UP/LOWER_UP.

That closes items 1-6 of the CLAUDE.md priority list. It also vindicates two
pre-hardware calls: the `CONFIG_DW_AXI_DMAC=y` blocker (without it the SPI controller
would have failed to probe silently) and the `ttyAMA10` console routing.

### Root cause of "no batman-adv": the device is un-provisioned, not defective

Two independent investigations of the repo and every feed agree. Nothing in the image
— on Pi 4 or Pi 5 — creates `bat0` at boot. Only three things in the whole tree write
`proto 'batadv'`: the LuCI wizard JS (`tools/morse/uci.js:444-518`, called from
`wizard.js:1214 save()`), openmanetd's `ApplySetup` RPC phase 10
(`setup_phases.go:1150-1181`), and a migration script that is dead code (gated on
`/etc/config/batman-adv`, which no package ships).

The observed wireless state is the correct factory default, byte-for-byte the output
of `netifd-morse/lib/wifi/morse.sh:90-97` plus `morse-wireless-defaults:153-157`. A
fresh Pi 4 produces the identical thing with a `BCM2711-` SSID prefix.

The `config interface 'bat0'` / `multicast_mode '0'` stub is a red herring:
openmanetd's `configureBatmanForceflood` (`mgmt.go:105`) writes it through
`uci_network.go:238`, which calls `AddSection()` unconditionally and never sets
`proto`. netifd ignores a proto-less section. Upstream behaviour, identical on Pi 4;
deliberately not changed.

`persistent_vars_storage.sh` is **not** causal. `morse-wireless-defaults` has no
`set -e` and lines 19/24 are plain command substitutions, so a missing binary yields
`""` and the script continues on its designed fallback path. On Pi 4 the script
exists but runs under `set -eu` and greps `vcgencmd bootloader_config` for keys absent
on stock hardware, so it exits 1 with empty stdout there too — both boards get
identical values.

### Two genuine port gaps found while proving that, and fixed (`a3b80a1`)

Both board-scoped to `ekh-bcm2712`; no shared file touched.

- `0009` — relaxes `persistent-vars-storage-bcm2711`'s `@TARGET_bcm27xx_bcm2711` gate
  to `bcm2711||bcm2712` and selects it. Parity and boot-log noise only.
- `0010` — adds `bcm2712,mm6108-spi` to openmanetd's board enum. All three capability
  switches (`GNSSsupoorted`, `BLOSsupported`, `CommsSupported`) end in
  `default: return false`, so the Pi 5 was silently reporting them unsupported. This
  is what would have made the WM1302 GPS look broken later.

Verified in the built rootfs, not inferred: `/sbin/persistent_vars_storage.sh` present,
and `strings usr/bin/openmanetd` contains `bcm2712,mm6108-spi` exactly once — the same
count as `bcm2711,mm6108-spi`.

## CURRENT

Mesh services, batman association and the two-node link remain NOT hardware
validated. Everything needed is on the device already.

## OWNER ACTION — no re-flash needed for this

1. Browse to `http://10.41.254.1/` and run **Wizards** (the homepage is already
   `admin/morse/landing`). That creates `bat0`, `batmesh0`/`batmesh1` and wires the
   HaLow interface into the mesh.
2. Confirm with `batctl if`, `ip -d link show type batadv`, `uci show network`.
3. Repeat on a second unit, then `batctl n` / `batctl o` / ping across.

Re-flash at your convenience — required only before the GPS work:

```
C:\AI-Projects\OpenMANET-Pi5\images\openmanet-1.8.0-rpi5-mm6108-spi-squashfs-sysupgrade.img.gz
sha256 1cfccb4c92020021e8eda9ca481cebecdd55897d4cca47297c47d82605a8d837
53,401,122 bytes
```

## NEXT

Two-node HaLow mesh association and IP traffic across BATMAN — the remaining Phase 1
items. After that: WM1302 GPS (unblocked by `0010`) and the USB Wi-Fi AC dongle for
local EUD/ATAK access, both previously deferred.
