# Porting OpenMANET to MorseMicro HaLow Link 2

## Hardware

- **SoC:** MediaTek MT7621 (MIPS 1004Kc, dual-core)
- **HaLow Radio:** MorseMicro MM8108 via SDIO (802.11ah Sub-1GHz)
- **WiFi:** MediaTek MT7603 (2.4GHz 802.11n) via PCIe
- **Flash:** 32MB SPI NOR
- **Ethernet:** 2x GbE (WAN + LAN) via MT7621 switch
- **Board name:** `morse,artini`
- **OpenWrt target:** `ramips/mt7621`

## Build Instructions

```bash
# From the firmware repo root:
./scripts/openmanet_setup.sh -i -b halowlink2
make download
make -j$(nproc)
```

**WSL2 Note:** If building on WSL2 with Windows PATH leaking, use a clean PATH:
```bash
PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" make -j$(nproc)
```
Windows paths containing `(x86)` cause bash syntax errors in Go build scripts.

## Flash Command

```bash
sysupgrade -F -n /tmp/sysupgrade.bin
```

Default IP after flash: `10.41.254.1`

## What Was Required to Port

### 1. Device Definition (firmware repo)

**DTS file:** `target/linux/ramips/dts/mt7621_morse_artini.dts`
- Full device tree with SDHCI, RGB LEDs (PWM-GPIO), PCIe WiFi, ethernet switch
- SDHCI node uses `ralink,mt7620-sdhci` compatible with fixed 48MHz clock
- MM8108 child node on SDIO bus with reset/power GPIOs

**Image definition:** `target/linux/ramips/image/mt7621.mk`
```makefile
define Device/morse_artini
  $(Device/dsa-migration)
  IMAGE_SIZE := 32448k
  DEVICE_VENDOR := MorseMicro
  DEVICE_MODEL := Artini
  DEVICE_PACKAGES := kmod-mmc kmod-sdhci-mt7620 kmod-mt7603 \
    kmod-morse netifd-morse morse-fw-6108 morse-fw-8108
endef
TARGET_DEVICES += morse_artini
```

### 2. Board Support Package (packages repo: `boards/bsp-halowlink2/`)

**`bsp-halowlink2`** package depends on `bsp-common` and provides:

- **`uci-defaults/10_halowlink_wireless`** - Sets default channel 28 on morse radio
- **`init.d/halowlink-morse-fix`** - Patches morse_overrides.sh at boot for SAE mesh fix

### 3. Patches (firmware repo: `patches/halowlink2/`)

Applied automatically by `openmanet_setup.sh -i -b halowlink2`:

- **`002-mac80211-uc-skip-morse-devices.patch`** - Prevents mac80211.uc from creating a duplicate radio for the morse SDIO device. Without this, both mac80211 and morse.sh detect the same hardware.

- **`004-openmanetd-mips32-sqlite-fix.patch`** - Swaps `modernc.org/sqlite` (no MIPS support) for `mattn/go-sqlite3` (CGO-based, all architectures). Also fixes alfred bindings cross-compilation for MIPS.

- **`005-add-morse-artini-device.patch`** - Adds the device definition and DTS to the ramips target.

### 4. Image Size Constraint

The HaLow Link 2 has 32MB flash with ~32MB for firmware. The full OpenMANET common config produces a ~37MB image. `tailscale` (9MB) must be set to `=m` (module, not in image) in `target_diffconfig` to fit. It can still be installed via opkg if overlay storage is available.

## Key Technical Issues Discovered

### SDHCI Driver
The MT7621 SDHCI controller requires `kmod-sdhci` + `kmod-sdhci-mt7620`. The DTS must use `ralink,mt7620-sdhci` compatible string with explicit fixed clocks (48MHz) and regulators (3.3V + 1.8V IO).

### mac80211.uc Duplicate Radio
The morse SDIO device is detected by both `mac80211.uc` (OpenWrt wifi-scripts) and `morse.sh` (morse-feed). mac80211.uc creates a bogus `mac80211` type radio that must be suppressed. Solution: check `/sys/class/ieee80211/<phy>/device/uevent` for `DRIVER=morse` and skip.

### S1G Channel Mapping and VHT 160MHz
HaLow S1G channels are internally mapped to 5GHz channel numbers by mac80211. No actual 5GHz transmission occurs. Channel 44 (924 MHz, 8MHz BW) maps to 5GHz channel 163, which is a VHT 160MHz center frequency. `wpa_supplicant_s1g` auto-enables VHT 160MHz and the kernel rejects the extension channels, causing `mesh join error=-22`.

**Safe 8MHz channels (US):** 12 (->5g 50), 28 (->5g 114). Channel 28 is the default.

Channel mapping reference (US, 8MHz BW):
| S1G Channel | Freq (MHz) | 5GHz Map | VHT 160 Issue |
|-------------|-----------|----------|---------------|
| 12          | 908       | 50       | No (valid center) |
| 28          | 916       | 114      | No (valid center) |
| 44          | 924       | 163      | **YES** (edge, rejects extensions) |

### SAE (WPA3) Mesh Authentication

**Problem:** `Mesh RSN: frame verification failed!` followed by `MESH-SAE-AUTH-FAILURE`

**Root cause:** The morse driver reports `PMF:0` for mesh mode because kernel 6.6 mac80211 doesn't expose `MFP_CAPABLE` for mesh interfaces. When `ieee80211w=1` or `ieee80211w=2` is set, the RSN Information Element advertises MFPC=1, but the driver's actual capability is PMF:0. The peer sees this inconsistency and rejects the peering frame.

**Solution:** Set `ieee80211w=0` for mesh mode in `morse_overrides.sh`. This makes the RSN IE consistent with the driver's PMF:0 capability. SAE authentication itself still works - PMF protection of management frames is what's disabled.

Additionally, `sae_pwe` must be set to `0` (hunting-and-pecking) instead of the morse default of `1` (H2E only) for mesh compatibility.

The fix is applied at boot by `bsp-halowlink2`'s init.d script, patching `morse_overrides.sh`:
```sh
# ieee80211w=0 for mesh mode only (non-mesh keeps ieee80211w=2)
# sae_pwe=0 (hunting-and-pecking) instead of 1 (H2E only)
```

### openmanetd MIPS32 Build

`openmanetd` uses `modernc.org/sqlite` which has no MIPS little-endian support. The fix swaps it for `mattn/go-sqlite3` (CGO-based) which works on all architectures. The alfred C bindings also need explicit cross-compilation flags for the MIPS target.

### wifi reload vs wifi down/up

`wifi reload` does not always restart `wpa_supplicant_s1g` (same PID, old config). Use `wifi down; sleep 2; wifi up` for config changes to take effect.

## Driver and Firmware Sources

| Component | Source | Version |
|-----------|--------|---------|
| morse_driver (kernel module) | github.com/MorseMicro/morse_driver | 1.14.1 (morse-feed) |
| morse chip firmware (mm8108b2) | github.com/MorseMicro/morse-firmware | via morse-feed |
| wpa_supplicant_s1g | github.com/MorseMicro/hostap | 1.14.1 (morse-feed) |
| hostapd_s1g | github.com/MorseMicro/hostap | 1.14.1 (morse-feed) |
| netifd-morse | morse-feed | Scripts for netifd wireless integration |

All pulled automatically by the morse feed in `feeds.conf.default`.

## Mesh Setup

After flashing, use the LuCI mesh wizard at `http://10.41.254.1`:
1. Select batman-adv mesh mode
2. Set Mesh ID and SAE passphrase
3. Channel defaults to 28 (916 MHz, 8 MHz BW)
4. Flash both devices, run wizard on each

batman-adv uses BATMAN_V protocol. Alfred provides network visualization.

## File Locations on Device

| File | Purpose |
|------|---------|
| `/lib/netifd/morse/morse_overrides.sh` | SAE/PMF defaults (patched at boot) |
| `/lib/netifd/wireless/morse.sh` | Main netifd wireless driver script |
| `/lib/wifi/morse.sh` | Radio detection script |
| `/lib/wifi/mac80211.uc` | mac80211 radio detection (patched to skip morse) |
| `/etc/uci-defaults/10_halowlink_wireless` | First-boot channel default |
| `/usr/share/morse-regdb/channels.csv` | S1G channel to 5GHz mapping table |
| `/var/run/wpa_supplicant-morse*.conf` | Runtime wpa_supplicant config |

## SSH Quick Fix for SAE Mesh (without reflash)

```bash
ssh root@<IP> "sed -i 's/set_default ieee80211w [12]/set_default ieee80211w 0/;s/set_default sae_pwe 1/set_default sae_pwe 0/' /lib/netifd/morse/morse_overrides.sh && wifi down && sleep 2 && wifi up"
```
