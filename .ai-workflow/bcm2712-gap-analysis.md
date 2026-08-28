# BCM2712 Gap Analysis — what must exist for `bcm2712_mm6108-spi` + `boards/ekh-bcm2712`

Scope: exhaustive read-only survey of `C:\AI-Projects\OpenMANET-Pi5\firmware`
(branch `pi5-wm6108-port`) for everything bcm2711-specific that needs a bcm2712
equivalent. Feeds are not checked out in the tree; the two pinned feeds
(`openmanet` @ `4736e447`, `morse` @ `fc332b01`) were cloned read-only into the
scratchpad and inspected — findings from those are marked **[feed]**.

Kernel: `include/kernel-6.6` → `LINUX_VERSION-6.6 = .138` (6.6.138).
Patch count in `target/linux/bcm27xx/patches-6.6/`: 1317.

---

## 0. Executive summary of the gaps

| # | Gap | Severity |
|---|-----|----------|
| 1 | `bcm2712/config-6.6` has **no SPI subsystem at all** (no `CONFIG_SPI`, `CONFIG_SPI_MASTER`, `CONFIG_SPI_DESIGNWARE`, `CONFIG_SPI_DW_MMIO`, `CONFIG_SPI_BCM2835`) | **Blocker** for MM6108-over-SPI |
| 2 | No `Device/bcm2712_mm6108-spi` in `target/linux/bcm27xx/image/Makefile` | **Blocker** |
| 3 | The Morse SPI overlay (`mm610x-spi-overlay.dts`) is BCM2835/2711-only — pin/`&spi0` semantics differ on RP1, and its `compatible` list stops at `brcm,bcm2711` | **Blocker** for HaLow bring-up |
| 4 | `991-0005` (MM_RESET/MM_WAKE/MM_BUSY `gpio-line-names`) patches only `arch/arm/boot/dts/broadcom/bcm2711-rpi-4-b.dts` | **High** — Morse userspace `chipreset.sh` keys off these names |
| 5 | `boards/ekh-bcm2712/` does not exist | **Blocker** |
| 6 | `patches/ekh-bcm2712/` does not exist (feed patches incl. the golang GCC-15 fix are applied per-board) | **High** — likely build failure |
| 7 | `persistent-vars-storage-bcm2711` **[feed]** is hard-gated `@TARGET_bcm27xx_bcm2711` | **Medium** |
| 8 | `image/boards/ekh01/distroconfig.txt` has `[pi4]`/`[cm4]` blocks only; `dtoverlay=uart5` and `dtoverlay=ramoops` are Pi4-shaped | **Medium** |
| 9 | `bcm2712/config-6.6` lacks `CONFIG_PSTORE*` (ramoops) and `CONFIG_USB_SERIAL*` (`cmdline.txt` sets `console=ttyUSB0`) | **Medium** |
| 10 | No CI workflow / release job registers a `ekh-bcm2712` board | **Medium** |
| 11 | `kmod-codec-bcm2835` + `kmod-camera-bcm2835-unicam` (camera diffconfig) have no Pi 5 equivalent in-tree | **Low** (defer) |

**Good news already in the tree/feeds:**
- `SUBTARGETS:=bcm2708 bcm2709 bcm2710 bcm2711 bcm2712` already includes bcm2712.
- `bcm2712/target.mk` + `bcm2712/config-6.6` exist and are complete for RP1 clock/pinctrl/PCIe/Ethernet.
- Full RPi RP1 patch stack is present (`950-0526..0543`, `950-1180`, `950-1423` macb, `950-1382..1389` mailbox/firmware/PIO).
- `base-files/etc/board.d/02_network` and `lib/preinit/05_set_preinit_iface_brcm2708` already list `raspberrypi,5-model-b`, `raspberrypi,500`, `raspberrypi,5-compute-module`.
- **[feed]** `bsp-bcm271x/files/board.d/03_openmanet_eth` **already** lists `bcm2712,mm6108-spi`, `bcm2712,mm6108-sdio`, `bcm2712,mm8108-spi`, `bcm2712,mm8108-sdio`.
- **[feed]** `bsp-common/files/uci-defaults/99_morse_radio_defaults` **already** maps `bcm2712,mm6108-spi` → `bcf_fgh100mhaamd.bin` and `bcm2712,mm6108-sdio` → `bcf_mf04151.bin`, with `country='US'`, `channel='42'`.
  → **The board name `bcm2712,mm6108-spi` is already the blessed convention. Use exactly that.**

---

## 1. `target/linux/bcm27xx/` — target plumbing

### 1.1 `target/linux/bcm27xx/Makefile`
```
ARCH:=arm
BOARD:=bcm27xx
FEATURES:=audio boot-part display ext4 fpu gpio rootfs-part rtc squashfs usb usbgadget
SUBTARGETS:=bcm2708 bcm2709 bcm2710 bcm2711 bcm2712
KERNEL_PATCHVER:=6.6
DEFAULT_PACKAGES += bcm27xx-gpu-fw bcm27xx-utils kmod-usb-hid \
	kmod-sound-core kmod-sound-arm-bcm2835 kmod-fs-vfat kmod-nls-cp437 \
	kmod-nls-iso8859-1 partx-utils mkf2fs e2fsprogs
KERNELNAME:=Image dtbs
```
**No change needed.** bcm2712 is already a subtarget. There is no `KERNEL_TESTING_PATCHVER` and no per-subtarget patch dir — all 1317 patches in `patches-6.6/` apply to every bcm27xx subtarget.

### 1.2 `bcm2711/target.mk` vs `bcm2712/target.mk`
```
# bcm2711                          # bcm2712
ARCH:=aarch64                      ARCH:=aarch64
SUBTARGET:=bcm2711                 SUBTARGET:=bcm2712
BOARDNAME:=BCM2711 boards (64 bit) BOARDNAME:=BCM2712 boards (64 bit)
CPU_TYPE:=cortex-a72               CPU_TYPE:=cortex-a76
                                   FEATURES+=pci pcie
```
Consequences:
- CPU arch dir for packages is `aarch64_cortex-a76` (not `-a72`). Matters for
  `cpu_arch:` in `build-release.yml` and for `openmanet_setup.sh -E` toolchain
  download.
- `FEATURES+=pci pcie` → `scripts/target-metadata.pl:32-33` turns these into
  `select PCI_SUPPORT` / `select PCIE_SUPPORT`. bcm2711 does **not** have the
  `pci` feature, so `CONFIG_PACKAGE_kmod-r8125=y` in
  `boards/ekh-bcm2711/target_diffconfig:51` depends on `@PCI_SUPPORT`
  (`package/kernel/r8125/Makefile:22`) and is therefore almost certainly being
  silently dropped by `make defconfig` on Pi 4 today. *(Inference from the
  metadata script; not verified by running a build.)* On bcm2712 it **will** be
  selectable — which is arguably wrong, since the Pi 5 has no onboard RTL8125.

### 1.3 `bcm2711/config-6.6` vs `bcm2712/config-6.6` (full symmetric diff)

Only in **bcm2711**:
```
# CONFIG_BCM2835_SMI is not set
# CONFIG_BCM2835_THERMAL is not set
# CONFIG_CPU_FREQ_DEFAULT_GOV_ONDEMAND is not set
# CONFIG_MTD is not set
# CONFIG_PSTORE_{842,LZ4,LZ4HC,LZO,ZSTD}_COMPRESS is not set
# CONFIG_PSTORE_CONSOLE is not set
# CONFIG_PSTORE_PMSG is not set
CONFIG_ARM64_ERRATUM_1319367=y
CONFIG_CAVIUM_ERRATUM_{22375,23154,27456}=y
CONFIG_CPU_FREQ_DEFAULT_GOV_PERFORMANCE=y
CONFIG_PSTORE=y
CONFIG_PSTORE_COMPRESS=y
CONFIG_PSTORE_COMPRESS_DEFAULT="deflate"
CONFIG_PSTORE_DEFLATE_COMPRESS=y
CONFIG_PSTORE_DEFLATE_COMPRESS_DEFAULT=y
CONFIG_PSTORE_RAM=y
CONFIG_SERIAL_RPI_FW=y
CONFIG_SPI=y
CONFIG_SPI_BCM2835=y
CONFIG_SPI_BCM2835AUX=y
CONFIG_SPI_BITBANG=y
CONFIG_SPI_DYNAMIC=y
CONFIG_SPI_GPIO=y
CONFIG_SPI_MASTER=y
CONFIG_USB_SERIAL=y
CONFIG_USB_SERIAL_CONSOLE=y
CONFIG_USB_SERIAL_CP210X=y
CONFIG_USB_SERIAL_FTDI_SIO=y
CONFIG_USB_SERIAL_GENERIC=y
CONFIG_USB_SERIAL_PL2303=y
```
Only in **bcm2712** (abridged to the load-bearing entries):
```
CONFIG_ARCH_BRCMSTB=y
CONFIG_BCM2712_IOMMU=y  CONFIG_BCM2712_MIP=y
CONFIG_PINCTRL_BCM2712=y  CONFIG_PINCTRL_RP1=y  CONFIG_PINCTRL_BCM2835=y  CONFIG_PINCTRL=y
CONFIG_MFD_RP1=y  CONFIG_COMMON_CLK_RP1=y  CONFIG_COMMON_CLK_RP1_SDIO=y  CONFIG_PWM_RP1=y
CONFIG_GPIO_BRCMSTB=y  CONFIG_GPIO_GENERIC=y  CONFIG_GPIOLIB_IRQCHIP=y
  CONFIG_GPIO_BCM_VIRT=y  CONFIG_GPIO_CDEV=y  CONFIG_GPIO_RASPBERRYPI_EXP=y
  CONFIG_RASPBERRYPI_GPIOMEM=y  CONFIG_OF_GPIO=y
CONFIG_MACB=y  CONFIG_MACB_PCI=y  CONFIG_MACB_USE_HWSTAMP=y  CONFIG_BROADCOM_PHY=y
  CONFIG_PHYLINK=y  CONFIG_PHYLIB=y  CONFIG_MDIO_BCM_UNIMAC=y  CONFIG_MICROCHIP_PHY=y
CONFIG_PCI=y  CONFIG_PCIE_BRCMSTB=y  CONFIG_PCI_MSI=y  CONFIG_PCIEASPM(_POWERSAVE)=y
  CONFIG_PCIE_DW{,_HOST,_PLAT,_PLAT_HOST}=y  CONFIG_PCI_ECAM/HOST_COMMON/HOST_GENERIC=y
CONFIG_IOMMU_{API,DMA,IOVA,SUPPORT}=y  CONFIG_OF_IOMMU=y
CONFIG_MMC_SDHCI_BRCMSTB=y  CONFIG_MMC_SDHCI_OF_DWCMSHC=y  CONFIG_MMC_CQHCI=y
CONFIG_BLK_DEV_NVME=y  CONFIG_NVME_CORE=y
CONFIG_USB_DWC3=y  CONFIG_USB_DWC3_HOST=y  CONFIG_PHY_BRCM_USB=y
CONFIG_SERIAL_8250_BCM7271=y
CONFIG_BCM2835_SMI=y  CONFIG_BCM2835_SMI_DEV=m  CONFIG_BCM2835_THERMAL=y
CONFIG_ARM_BRCMSTB_AVS_CPUFREQ=y  CONFIG_CPU_FREQ_DEFAULT_GOV_ONDEMAND=y
CONFIG_SENSORS_RASPBERRYPI_HWMON=y  CONFIG_RTC_DRV_{BRCMSTB,RPI}=y
CONFIG_CRYPTO_*_ARM64_CE=y (AES/GHASH/SHA1/SHA2/SHA3/SHA512/SM3/SM4)
# CONFIG_FIRMWARE_RP1 is not set   # CONFIG_MBOX_RP1 is not set
# CONFIG_RP1_PIO is not set        # CONFIG_SENSORS_RP1_ADC is not set
```
(the `# ... is not set` RP1 entries are deliberate — those are shipped as
kmods, see §7.)

Both files share `CONFIG_ARCH_BCM2835=y` (line 5), which is what gates
`dtbo-$(CONFIG_ARCH_BCM2835)` in `arch/arm/boot/dts/overlays/Makefile`, so
custom overlays do get built for bcm2712 too.

### 1.4 `base-files/`
`target/linux/bcm27xx/base-files/` is **shared across all subtargets** — there
are no per-subtarget base-files dirs. Files:
```
etc/board.d/01_leds
etc/board.d/02_network
etc/diag.sh
etc/inittab
etc/uci-defaults/99-migrate-led-configs
lib/preinit/01_sysinfo
lib/preinit/05_set_preinit_iface_brcm2708
lib/preinit/79_move_config
lib/preinit/81_set_root_part
lib/upgrade/keep.d/platform
lib/upgrade/platform.sh
```
- `02_network` and `05_set_preinit_iface_brcm2708` already handle
  `raspberrypi,5-model-b|500|5-compute-module` → `eth0`. **No change needed for
  the generic rpi-5 device.**
- **Neither file lists `bcm2711,mm6108-spi`** either — the OpenMANET product
  board names are handled by the feed's
  `bsp-bcm271x/files/board.d/03_openmanet_eth` **[feed]**, which already covers
  `bcm2712,mm6108-spi`. The in-tree `02_network` `morse,ekh01*` entries are
  legacy.
- `01_leds` gates the HaLow ACT-LED trigger on `morse,ekh01*` only — it does
  **not** match `bcm2711,mm6108-spi` today, so no bcm2712 regression is created
  by leaving it alone (but adding `bcm2712,mm6108-spi` there would be a real
  improvement; note the Pi 5 ACT LED is on a different GPIO, see patch
  `950-0871-ARM-dts-bcm2712-rpi-5-b-Add-act_led_gpio.patch`).
- `lib/upgrade/platform.sh` is generic (partition/PARTUUID based,
  `bcm27xx_set_root_part()` rewrites `/boot/cmdline.txt`). **No change needed.**
- `etc/diag.sh` keys off `/sys/class/leds/ACT`. Works on Pi 5 (`950-0820`
  standardises the LED label to `ACT`).

### 1.5 `image/`
```
target/linux/bcm27xx/image/Makefile
target/linux/bcm27xx/image/cmdline.txt
target/linux/bcm27xx/image/config.txt
target/linux/bcm27xx/image/distroconfig.txt
target/linux/bcm27xx/image/gen_rpi_sdcard_img.sh
target/linux/bcm27xx/image/boards/ekh01/distroconfig.txt
target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm610x-spi.txt
target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm610x-sdio.txt
target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm610x-spi-and-sdio.txt
target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm810x-spi.txt
target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm810x-spi-and-sdio.txt
target/linux/bcm27xx/image/boards/ekh01/distroconfig-mmx10x-sdio.txt
target/linux/bcm27xx/image/boards/ekh01/distroconfig-raven.txt
```
`gen_rpi_sdcard_img.sh`, `cmdline.txt` and `config.txt` are SoC-agnostic; no
change needed. `cmdline.txt` contains `console=ttyUSB0,115200` — see §9 on
missing `CONFIG_USB_SERIAL*` in bcm2712.

`image/boards/ekh01/distroconfig.txt` (the OpenMANET product boot config) is
Pi-4-shaped and needs Pi-5 handling:
```
[pi3]  dtoverlay=disable-bt ; dtparam=i2c1=on
[pi4]  dtoverlay=miniuart-bt ; dtparam=i2c1=on
[cm4]  dtoverlay=pcie-32bit-dma ; dtoverlay=dwc2,dr_mode=host
[all]  disable_overscan=1 ; gpu_mem_*=128 ; uart_enable=1 ;
       dtoverlay=uart5 ;                      # <-- no uart5 on Pi 5 (RP1 UARTs)
       dtparam=act_led_trigger=none ;
       dtoverlay=ramoops ;                    # <-- needs PSTORE_RAM, absent on bcm2712
       camera_auto_detect=1
```
Notes: `dtoverlay=ramoops` **is** mapped for Pi 5 in the kernel
(`950-1288-dts-overlay_map-ramoops-pi4-works-on-Pi-5.patch` adds
`bcm2712 = "ramoops-pi4"`), so only the kernel config is missing.
`dtoverlay=uart5` will fail on Pi 5. `gpu_mem_*` is ignored on Pi 5.

`distroconfig-mm610x-spi.txt` is just:
```
dtparam=spi=on
dtoverlay=mm610x-spi
```
That is reusable **if** an `mm610x-spi-pi5` overlay + overlay_map entry is
added (see §7.3); otherwise a separate `distroconfig-mm610x-spi-pi5.txt` naming
the pi5 overlay directly is needed.

---

## 2. Raspberry Pi boot firmware — where `start4.elf` etc. come from, and what Pi 5 needs

**Source:** `package/kernel/bcm27xx-gpu-fw/Makefile`
- `PKG_SOURCE:=raspi-firmware_1.2025.04.30.orig.tar.xz` from
  `https://github.com/raspberrypi/firmware/releases/download/1.2025.04.30`
- It installs **nothing** into the rootfs (`Package/.../install: true`); its
  entire job is `Build/InstallDev`, which `$(CP)`s the boot blobs into
  `$(KERNEL_BUILD_DIR)` (== `$(KDIR)`):
  `bootcode.bin`, `LICENCE.broadcom`, `start.elf`, `start_cd.elf`,
  `start_x.elf`, `start4.elf`, `start4cd.elf`, `start4x.elf`, `fixup.dat`,
  `fixup_cd.dat`, `fixup_x.dat`, `fixup4.dat`, `fixup4cd.dat`, `fixup4x.dat`.
- It is in the target's `DEFAULT_PACKAGES` (`DEPENDS:=@TARGET_bcm27xx`,
  `DEFAULT:=y if TARGET_bcm27xx`), so it is built for bcm2712 as well.

**Image assembly** (`image/Makefile`):
- `Build/boot-common` copies: `COPYING.linux`, **`LICENCE.broadcom`**,
  `cmdline.txt`, `config.txt`, `distroconfig.txt`, `partuuid.txt`, the kernel
  as `$(KERNEL_IMG)`, each `$(DEVICE_DTS).dtb` (flattened to basename at the
  FAT root), and `overlays/*.dtbo` + `overlays/README`.
- `Build/boot-2708` / `boot-2710` add `bootcode.bin` + `start*.elf` +
  `fixup*.dat` (Pi 0–3).
- `Build/boot-2711` adds `start4.elf start4cd.elf start4x.elf fixup4.dat
  fixup4cd.dat fixup4x.dat` (Pi 4 / CM4).
- **There is no `Build/boot-2712`,** and `Device/rpi-5` (lines 231–258) uses
  `IMAGE/sysupgrade.img.gz := boot-common | sdcard-img | gzip | append-metadata`
  — i.e. **boot-common only**.

**Conclusion:** this is correct and matches upstream OpenWrt. The Pi 5 VPU
firmware lives in the on-board SPI EEPROM bootloader; the FAT partition only
needs `config.txt` (+ the included `distroconfig.txt`), `cmdline.txt`,
`kernel_2712.img`, the `bcm2712-*.dtb`, and `overlays/`. `LICENCE.broadcom`
still comes from `$(KDIR)` via `bcm27xx-gpu-fw`, which is why `boot-common`
alone is sufficient. **No new `Build/boot-2712` macro is required**, and the
new device must **not** inherit `boot-2711`.

`Device/rpi-5` sets `KERNEL_IMG := kernel_2712.img`, which is the name the Pi 5
bootloader looks for by default on BCM2712.

---

## 3. `package/` — bsp-bcm271x, persistent-vars-storage, and board gating

Neither package is in this repo; both are feed packages. Grep results in-tree:
```
boards/ekh-bcm2710/target_diffconfig:10:CONFIG_PACKAGE_bsp-bcm271x=y
boards/ekh-bcm2711/target_diffconfig:43:CONFIG_PACKAGE_bsp-bcm271x=y
boards/ekh-bcm2711/target_diffconfig:47:CONFIG_PACKAGE_persistent-vars-storage-bcm2711=y
boards/raven/target_diffconfig:21:CONFIG_PACKAGE_persistent-vars-storage-bcm2711=y
```

### 3.1 `bsp-bcm271x` **[feed openmanet @ 4736e447: `boards/bsp-bcm271x/`]**
```
DEPENDS:=+bsp-common +kmod-fs-configfs +usbgadget +gpsd \
	+PACKAGE_libcamera-utils:libcamera-utils \
	+PACKAGE_mediamtx:mediamtx \
	+PACKAGE_camera-onvif-server:camera-onvif-server
```
**Not** gated on any target/subtarget symbol → selectable on bcm2712 as-is.
Ships: `etc/board.d/03_openmanet_eth`, `etc/init.d/{bcm2710-morse-fix,
gpsboard.init,rpi-camera-services}`, `etc/config/{ethtool,gpsd}`,
`etc/hotplug.d/iface/{90-ethtool,95-camera-onvif-server-interface}`,
`etc/sysctl.d/25-bcm271x-net.conf`, `etc/uci-defaults/*`, and
**`lib/firmware/morse/bcf_mf04151.bin`**.

Its `03_openmanet_eth` already contains `bcm2712,mm6108-sdio`,
`bcm2712,mm6108-spi`, `bcm2712,mm8108-sdio`, `bcm2712,mm8108-spi`,
`raspberrypi,5-model-b`, `raspberrypi,5-compute-module` → `eth0`.
**Reusable unchanged.** `bcm2710-morse-fix` only fires on `bcm2710,*`.

### 3.2 `persistent-vars-storage-bcm2711` **[feed morse @ fc332b01: `hardware/persistent-vars-storage-bcm2711/`]**
```
PROVIDES:=persistent-vars-storage
DEPENDS:= +bcm27xx-userland @TARGET_bcm27xx_bcm2711     # <-- HARD-GATED
```
The payload is a single shell script `/sbin/persistent_vars_storage.sh` whose
only SoC-specific call is `vcgencmd bootloader_config` — which works identically
on Pi 5 (the bootloader EEPROM config). `WRITE`/`ERASE` are unimplemented.
Consumers **[feed morse]**: `hardware/virtual-wire/Makefile:16` and
`hardware/morse-modeswitch-button/Makefile:18` (`DEPENDS:=... persistent-vars-storage`).
Neither is enabled in `boards/ekh-bcm2711`, so it is currently only providing the
script (`bcm27xx-userland` is `PROVIDES`d by `package/utils/bcm27xx-utils`).

**Needed for Pi 5:** either (a) simply omit it from `boards/ekh-bcm2712` for
Phase 1, or (b) add a `patches/ekh-bcm2712/000X-...patch` that relaxes the
`DEPENDS` to `@TARGET_bcm27xx_bcm2711||TARGET_bcm27xx_bcm2712` in
`feeds/morse/hardware/persistent-vars-storage-bcm2711/Makefile`. Option (a) is
recommended for the sprint.

### 3.3 Other board/model gating in `package/`
Grepping the whole `package/` tree for `raspberrypi,4-model-b` / similar returns
**nothing** — no in-repo package gates on a Pi model compatible. Target gating
that exists:
```
package/kernel/bcm27xx-gpu-fw/Makefile        DEPENDS:=@TARGET_bcm27xx
package/utils/bcm27xx-utils/Makefile:28       DEPENDS:=@TARGET_bcm27xx +libfdt  (PROVIDES:=bcm27xx-userland)
package/kernel/mac80211/broadcom.mk:435       default y if TARGET_bcm27xx
package/libs/wolfssl/Makefile:91,114,163      TARGET_bcm27xx conditionals
package/kernel/linux/modules/netdevices.mk:173,190,720
                                              +(...||TARGET_bcm27xx_bcm2708||...):kmod-of-mdio
config/Config-images.in:297                   TARGET_KERNEL_PARTSIZE default 64 if TARGET_bcm27xx
config/Config-kernel.in:100                   depends on ... && TARGET_bcm27xx
package/kernel/r8125/Makefile:22              DEPENDS:=@PCI_SUPPORT +kmod-libphy
```
All are target-level (`bcm27xx`), not subtarget-level, except the
`bcm27xx_bcm2708` of-mdio workarounds (irrelevant here). **No package edits
required.**

---

## 4. Board/model detection — how `bcm2711,mm6108-spi` reaches userspace

The chain, end to end:

1. **Kernel overlay** —
   `target/linux/bcm27xx/patches-6.6/992-0001-Smuggle-board_name-model-into-userspace-via-devicetr.patch`
   adds `arch/arm/boot/dts/overlays/sysinfo-overlay.dts` and registers
   `sysinfo.dtbo` under `dtbo-$(CONFIG_ARCH_BCM2835)`. It writes two root
   properties via `__overrides__`: `sysinfo-model` and `sysinfo-board-name`.
   (`CONFIG_ARCH_BCM2835=y` is set in **both** `bcm2711/config-6.6:5` and
   `bcm2712/config-6.6:5`, so `sysinfo.dtbo` is built for bcm2712 too.)

2. **Image build** — `Build/boot-ekh01` in `image/Makefile` (lines ~85–96)
   concatenates `boards/ekh01/distroconfig.txt` +
   `boards/ekh01/distroconfig-$(DISTROCONFIG_EXTRA).txt` + a generated
   `dtoverlay=sysinfo,board-name="$(SYSINFO_BOARD_NAME)",model="$(SYSINFO_MODEL)"`
   line, and mcopies the result over `::/distroconfig.txt`.

3. **`SYSINFO_BOARD_NAME`** is derived in `Device/morse_ekh01_base`
   (`image/Makefile:262`): `SYSINFO_BOARD_NAME := $(subst _,$(comma),$(1))`
   — i.e. the device name `bcm2711_mm6108-spi` becomes `bcm2711,mm6108-spi`.
   `SUPPORTED_DEVICES := $$(SYSINFO_BOARD_NAME)`.
   `SYSINFO_MODEL` is set per-device, e.g. `RPI RPI4-MM6108 (SPI)`.
   Both are in `DEVICE_VARS` (line 9).

4. **Runtime** — `base-files/lib/preinit/01_sysinfo` runs
   `do_sysinfo_dtoverlay` on `preinit_main`, copying
   `/proc/device-tree/sysinfo-board-name` → `/tmp/sysinfo/board_name` and
   `sysinfo-model` → `/tmp/sysinfo/model`, ahead of OpenWrt's generic
   `02_sysinfo`. `board_name()` in `/lib/functions.sh` then returns
   `bcm2711,mm6108-spi`.

5. **Consumers** — `bsp-bcm271x`'s `03_openmanet_eth` and `bsp-common`'s
   `99_morse_radio_defaults` **[feed]**, both of which already handle
   `bcm2712,mm6108-spi`.

**What needs a bcm2712 entry:**
- Nothing in the feeds (already done).
- In-tree, only optionally `base-files/etc/board.d/01_leds` (HaLow ACT-LED
  trigger) — it currently matches only `morse,ekh01*` and would need
  `bcm2712,mm6108-spi` (and, for parity, `bcm2711,mm6108-spi`) added.
- The `Device/bcm2712_mm6108-spi` definition itself supplies the board name
  automatically via the `$(subst _,$(comma),$(1))` rule — so naming the device
  exactly `bcm2712_mm6108-spi` yields `bcm2712,mm6108-spi` for free.

---

## 5. `boards/ekh-bcm2711/*` — what the bcm2712 mirror must change

All files except `target_diffconfig` are **git symlinks** (mode `120000`) into
`../common_extras/`; `openmanet_setup.sh:267-274` **aborts** if a non-`target_diffconfig`
file in the board dir is not a symlink. Full list:
```
camera_diffconfig      -> ../common_extras/camera_diffconfig
cameraapp_diffconfig   -> ../common_extras/cameraapp_diffconfig
dppqrcode_diffconfig   -> ../common_extras/dppqrcode_diffconfig
languages_diffconfig   -> ../common_extras/languages_diffconfig
morseguide_diffconfig  -> ../common_extras/morseguide_diffconfig
prplmesh_diffconfig    -> ../common_extras/prplmesh_diffconfig
rangetest_diffconfig   -> ../common_extras/rangetest_diffconfig
spi_diffconfig         -> ../common_extras/spi_diffconfig
usb_diffconfig         -> ../common_extras/usb_diffconfig
utils_diffconfig       -> ../common_extras/utils_diffconfig
video_diffconfig       -> ../common_extras/video_diffconfig
wireshark_diffconfig   -> ../common_extras/wireshark_diffconfig
target_diffconfig      (regular file, 54 lines)
```
Assembly order (`openmanet_setup.sh:279-289`):
`boards/common/*_diffconfig` → then either `boards/<B>/target_diffconfig` (with
`-m`) or `boards/<B>/*_diffconfig` (glob, so `target_diffconfig` lands
alphabetically **after** `spi_/rangetest_` and before `usb_/utils_/video_/…`)
→ then any `-x <extra>` from `common_extras`. Then `make defconfig`.

### Line-by-line delta for `boards/ekh-bcm2712/target_diffconfig`
| ekh-bcm2711 line | bcm2712 equivalent |
|---|---|
| `CONFIG_TARGET_bcm27xx_bcm2711=y` | `CONFIG_TARGET_bcm27xx_bcm2712=y` |
| `CONFIG_TARGET_DEVICE_bcm27xx_bcm2711_DEVICE_bcm2711_mm6108-spi=y` | `CONFIG_TARGET_DEVICE_bcm27xx_bcm2712_DEVICE_bcm2712_mm6108-spi=y` |
| `..._bcm2711_mm6108-sdio=y`, `..._bcm2711_mm8108-usb=y` | drop for Phase 1 (single SPI device keeps the per-device-rootfs logic trivial) |
| `CONFIG_TARGET_DEVICE_PACKAGES_bcm27xx_bcm2711_DEVICE_bcm2711_mm6108-spi="-kmod-mm8108 -mm8108-firmware -wpad-basic-mbedtls"` | `CONFIG_TARGET_DEVICE_PACKAGES_bcm27xx_bcm2712_DEVICE_bcm2712_mm6108-spi="-wpad-basic-mbedtls"` (plus `-kmod-mm8108 -mm8108-firmware` only if mm8108 is still forced `=y`) |
| `CONFIG_PACKAGE_kmod-mm6108=y` / `kmod-mm8108=y` / `mm6108-firmware=y` / `mm8108-firmware=y` | keep `kmod-mm6108`/`mm6108-firmware` `=y`; set mm8108 pair `=n` if only one device is built (the `=y` trick exists purely so `kmod-morse` dependents don't get demoted to `=m`) |
| `CONFIG_VERSION_PRODUCT="BCM2711"` | `"BCM2712"` |
| `CONFIG_PACKAGE_bsp-bcm271x=y` | unchanged — **[feed]** not target-gated, already knows bcm2712 |
| `CONFIG_PACKAGE_persistent-vars-storage-bcm2711=y` | **remove** — hard `@TARGET_bcm27xx_bcm2711` **[feed]**; see §3.2 |
| `CONFIG_PACKAGE_kmod-codec-bcm2835=y` | **remove/verify.** The kmod itself is only `@TARGET_bcm27xx` (`modules/video.mk:52`) so it *builds*, but BCM2712 has no VideoCore H.264 codec — `bcm2835-codec` will not probe on Pi 5. Also `CONFIG_BCM2835_VCHIQ_MMAL` is `# not set` in **both** subtarget configs, so the kmod may not even be buildable as configured. Treat as out-of-scope for Phase 1. |
| `CONFIG_PACKAGE_kmod-r8125=y` (`# 2.5Gb Ethernet`) | **remove.** Pi 5 has no onboard RTL8125; its 1GbE is Cadence GEM in RP1 (`CONFIG_MACB=y`, already built in). Keeping it would now actually pull the driver in, because bcm2712 has `FEATURES+=pci pcie` → `PCI_SUPPORT`. |
| `CONFIG_PACKAGE_kmod-of-mdio=y` (lan78xx workaround) | harmless but unnecessary — `Device/rpi-5` does not list `kmod-usb-net-lan78xx`/`kmod-r8169` (unlike `Device/rpi-4`). Drop. |
| `CONFIG_PACKAGE_mavp2p=m`, `CONFIG_PACKAGE_kmod-video-core=y`, `CONFIG_TARGET_ROOTFS_PARTSIZE=4092`, `CONFIG_TARGET_ROOTFS_EXT4FS=n`, `CONFIG_TARGET_MULTI_PROFILE=y`, `CONFIG_TARGET_PER_DEVICE_ROOTFS=y`, `CONFIG_TARGET_bcm27xx=y`, `CONFIG_VERSION_MANUFACTURER="Raspberry Pi"` | unchanged |
| — | **add** `CONFIG_PACKAGE_kmod-spi-dw=y` + `CONFIG_PACKAGE_kmod-spi-dw-mmio=y` unless SPI is made built-in in `bcm2712/config-6.6` (see §7.2) |

Also note the symlinked `boards/common_extras/spi_diffconfig` that
`ekh-bcm2712/spi_diffconfig` would point at:
```
CONFIG_MORSE_SPI=y
CONFIG_PACKAGE_kmod-spi-bcm2835=y
CONFIG_PACKAGE_kmod-spi-bcm2835-aux=y
CONFIG_PACKAGE_kmod-spi-bitbang=y
CONFIG_PACKAGE_kmod-spi-gpio=y
```
This does **not** enable the RP1 DesignWare controller. `CONFIG_MORSE_SPI=y` is
the Morse driver switch and must stay; `kmod-spi-dw-mmio` must be added (either
in `target_diffconfig` or by not symlinking `spi_diffconfig` and shipping a
bcm2712-specific one — but note the setup script requires everything except
`target_diffconfig` to be a symlink, so put it in `target_diffconfig`).

Also required alongside the board dir:
`patches/ekh-bcm2712/` — copy of `patches/ekh-bcm2711/`'s four patches
(`0001-add_videoparser_plugin_bad`, `0002-...collectd...`,
`0003-iperf3_3_19_1`, `0005-golang-Fix-host-build-compatibility-with-GCC-15`),
applied by `patch_feeds_packages()` (`openmanet_setup.sh:124-152`) with
`patch -N -p1` from the repo root against `feeds/...` paths.

---

## 6. CI — where a new board must be registered

There is no matrix; each board is a **separate reusable-workflow call**.
`.github/workflows/build-firmware.yml` is the reusable job. Its inputs:
`board`, `target`, `subtarget`, `description`, `releasepackages`, `cpu_arch`.
It runs `./scripts/openmanet_setup.sh -i -b ${{ inputs.board }}` then
`make download` + `make -j$(nproc) V=s`, and reads
`bin/targets/${target}/${subtarget}/`.

Existing callers:
- `.github/workflows/build-pr-bcm2711.yml` — PR trigger, paths
  `boards/ekh-bcm2711/**`, `boards/common/**`, `include/kernel*`,
  `package/kernel/**`, `target/linux/bcm27xx/**`, `feeds.conf.default`;
  `board: ekh-bcm2711, target: bcm27xx, subtarget: bcm2711`.
- `build-pr-bcm2710.yml`, `build-pr-halowlink2.yml`, `build-pr-hd01v2.yml`,
  `build-pr-venice.yml` — same shape.
- `.github/workflows/build-release.yml` — jobs `build-ekh-bcm2711`
  (`cpu_arch: aarch64_cortex-a72`), `build-ekh-bcm2710`, `build-halowlink2`,
  `build-hd01-v2`, `build-venice`. Two `needs:` lists at lines 80 and 150 name
  every build job and must be extended.

**Registration checklist for `ekh-bcm2712`:**
1. New `.github/workflows/build-pr-bcm2712.yml` (copy of the 2711 one;
   `board: ekh-bcm2712`, `subtarget: bcm2712`, description
   `"Raspberry Pi 5, CM5"`).
2. New `build-ekh-bcm2712` job in `build-release.yml` with
   `cpu_arch: aarch64_cortex-a76` (**not** `-a72`).
3. Add `build-ekh-bcm2712` to both `needs:` arrays (`publish-packages` line 80,
   `release` line 150).
4. `.github/labeler.yml` needs nothing — `target/bcm27xx` already globs
   `target/linux/bcm27xx/**`.

**Board→build mapping outside CI:** `scripts/openmanet_setup.sh` is the only
wrapper. It discovers boards purely by directory listing (`for b in boards/*`,
line 58/235) and by `sed -n 's/CONFIG_TARGET_.*_DEVICE_\(.*\)_\(.*\)=y/…/p'`
on `target_diffconfig` — so a device name can be passed to `-b` directly and it
resolves to the owning board dir. The external-toolchain path uses
`sed -nE 's/^CONFIG_TARGET_([a-z0-9]+)_([a-z0-9]+)=y/\1 \2/p'` (line 311),
which matches `bcm27xx`/`bcm2712` fine. `scripts/diffconfig.sh` is generic.
**No script changes needed.**

---

## 7. Kernel — RP1 drivers, SPI, and patches

Kernel **6.6.138** (`include/kernel-6.6`), single `patches-6.6/` dir shared by
all bcm27xx subtargets (1317 patches).

### 7.1 RP1 support present in `patches-6.6/`
Core RP1 stack is fully present:
```
950-0525/0526  dt-binding + mfd rp1 driver
950-0527/0528  clk-rp1 bindings + driver     950-0534 rp1 sdio clk
950-0530       pinctrl-rp1 driver
   + 950-1006 per-bank GPIO base, 950-1007 legacy brcm,pins on all banks,
     950-1008 IRQ affinity, 950-1009 clear events, 950-1041 gpio-ranges,
     950-1043/1082 strict_gpiod, 950-1185 PCIe-latency workaround
950-0531       pl011 rp1 uart      950-0842 rs485      950-1500 r1p5
950-0533/0718/0719  sdhci-of-dwcmshc rp1 sdio
950-0537       spi-dw: handle combined tx+rx messages      <-- DesignWare SPI = RP1 SPI
950-0538       pwm-rp1        950-0539/0540/0541 drm rp1 dsi/dpi/vec
950-0543 + ~40 fixes  media rp1-cfe (camera front end)
950-0550/0560  hwmon rp1-adc
950-0704       dts: rp1 add spi6, fix spi1 #address-cells
950-1144/1145  dw-axi-dmac fixes for RP1
950-1180       arm64-dts: move bcm2712 and rp1 here  (arch/arm64/boot/dts/broadcom)
950-1382..1389 rp1 mailbox, firmware-over-mbox, PIO driver, pwm-pio, dts nodes
950-1423/1426/1429/1430  macb: RP1 ethernet controller support + DT fixups
```
`950-1180` confirms bcm2712 DTs now live under **`arch/arm64/boot/dts/broadcom/`**
(`bcm2712-rpi-5-b.dts` etc.), and that it defines `gpio: &rp1_gpio` and the
alias `spi0 = &spi0` (RP1 SPI0). `950-0040` creates
`arch/arm64/boot/dts/overlays` as a **symlink** to the arm overlays dir, so a
single overlay source tree serves both.

### 7.2 Exact SPI / GPIO / pinctrl / PCIe / Ethernet symbols in `bcm2712/config-6.6`

**PINCTRL** (lines 291, 487–490) — complete:
```
CONFIG_GENERIC_PINCTRL_GROUPS=y
CONFIG_PINCTRL=y
CONFIG_PINCTRL_BCM2712=y
CONFIG_PINCTRL_BCM2835=y
CONFIG_PINCTRL_RP1=y
```
**GPIO** (lines 299–305, 351, 442, 501, 511, 519, 527, 561) — complete:
```
CONFIG_GPIOLIB_IRQCHIP=y  CONFIG_GPIO_BCM_VIRT=y  CONFIG_GPIO_BRCMSTB=y
CONFIG_GPIO_CDEV=y  CONFIG_GPIO_GENERIC=y  CONFIG_GPIO_RASPBERRYPI_EXP=y
CONFIG_OF_GPIO=y  CONFIG_RASPBERRYPI_GPIOMEM=y  CONFIG_LEDS_GPIO=y
CONFIG_POWER_RESET_GPIO=y  CONFIG_PWM_GPIO=y  CONFIG_REGULATOR_GPIO=y
# CONFIG_GPIO_FSM is not set
```
**PCIe** — complete (`CONFIG_PCI=y`:455, `CONFIG_PCIE_BRCMSTB=y`:464,
`CONFIG_PCI_MSI=y`:477, `PCIE_DW*`, `PCI_ECAM`, `HOTPLUG_PCI`, `PCIEASPM_POWERSAVE`).
**IOMMU** — complete (`CONFIG_BCM2712_IOMMU=y`, `IOMMU_{API,DMA,IOVA,SUPPORT}`,
`OF_IOMMU`, `IOMMU_DEFAULT_DMA_STRICT`).
**Ethernet** — complete:
```
CONFIG_MACB=y  CONFIG_MACB_PCI=y  CONFIG_MACB_USE_HWSTAMP=y
CONFIG_BROADCOM_PHY=y  CONFIG_BCM7XXX_PHY=y  CONFIG_BCM_NET_PHYLIB=y
CONFIG_PHYLIB=y  CONFIG_PHYLINK=y  CONFIG_MDIO_BCM_UNIMAC=y  CONFIG_OF_MDIO=y
```

**SPI — MISSING ENTIRELY.** `grep -E "SPI" bcm2712/config-6.6` matches only
`LOCK_SPIN_ON_OWNER`, `MUTEX_SPIN_ON_OWNER`, `QUEUED_SPINLOCKS`,
`RTC_I2C_AND_SPI`, `RWSEM_SPIN_ON_OWNER`. There is **no** `CONFIG_SPI`,
`CONFIG_SPI_MASTER`, `CONFIG_SPI_DYNAMIC`, `CONFIG_SPI_DESIGNWARE`,
`CONFIG_SPI_DW_MMIO`, `CONFIG_SPI_BCM2835`, `CONFIG_SPI_BITBANG`,
`CONFIG_SPI_GPIO`. `target/linux/generic/config-6.6:6208` has
`# CONFIG_SPI is not set`, so the default is off.

Today this "works" for the generic `Device/rpi-5` only because
`DEVICE_PACKAGES` lists `kmod-spi-bcm2835` and `kmod-spi-dw-mmio`, and
`package/kernel/linux/modules/spi.mk:77-90` (`KernelPackage/spi-dw`) forces
`CONFIG_SPI=y CONFIG_SPI_MASTER=y CONFIG_SPI_DYNAMIC=y CONFIG_SPI_DESIGNWARE`
into the kernel config as a side effect of selecting the kmod. `spi-dw-mmio`
(line 98) adds `CONFIG_SPI_DW_MMIO` and `DEPENDS:=+kmod-spi-dw`.

**Recommendation:** add to `target/linux/bcm27xx/bcm2712/config-6.6` (mirroring
what bcm2711 does), so SPI core is built in and not dependent on package
selection ordering:
```
CONFIG_SPI=y
CONFIG_SPI_MASTER=y
CONFIG_SPI_DYNAMIC=y
CONFIG_SPI_BITBANG=y
CONFIG_SPI_GPIO=y
CONFIG_SPI_BCM2835=y          # BCM2712 legacy SPI blocks
CONFIG_SPI_BCM2835AUX=y
CONFIG_SPI_DESIGNWARE=y       # RP1 SPI0..SPI6
CONFIG_SPI_DW_MMIO=y
```
(If `SPI_DESIGNWARE`/`SPI_DW_MMIO` are left `=m` via kmods, verify module load
ordering against the Morse driver's probe — `991-0007` patches
`drivers/spi/spi.c` core, which is built-in either way.)

**Also missing on bcm2712 but present on bcm2711 and needed by our boot config:**
```
CONFIG_PSTORE=y  CONFIG_PSTORE_RAM=y  CONFIG_PSTORE_COMPRESS=y
CONFIG_PSTORE_DEFLATE_COMPRESS=y  CONFIG_PSTORE_DEFLATE_COMPRESS_DEFAULT=y
CONFIG_PSTORE_COMPRESS_DEFAULT="deflate"
    -> required by `dtoverlay=ramoops` in image/boards/ekh01/distroconfig.txt
CONFIG_USB_SERIAL=y  CONFIG_USB_SERIAL_CONSOLE=y  CONFIG_USB_SERIAL_GENERIC=y
CONFIG_USB_SERIAL_CP210X=y  CONFIG_USB_SERIAL_FTDI_SIO=y  CONFIG_USB_SERIAL_PL2303=y
    -> image/cmdline.txt contains `console=ttyUSB0,115200`
CONFIG_SERIAL_RPI_FW=y   (optional; 950-1433 RPi firmware UART)
```

### 7.3 Morse / OpenMANET kernel patches — all BCM2835/2711-only

| Patch | Content | bcm2712 status |
|---|---|---|
| `991-0001-dt-overlays-morse-add-sdio-overlay-fragment.patch` | `mm_wlan-overlay.dts`, `compatible = "brcm,bcm2835","brcm,bcm2836","brcm,bcm2708","brcm,bcm2709","brcm,bcm2711"`, targets `&mmc`, `brcm,pins` on `&gpio` | **needs pi5 variant** (Pi 5 SDIO is `sdio-pi5`, see `950-1098`) |
| `991-0003-dt-overlays-morse-add-spi-overlay-fragment.patch` | `mm610x-spi-overlay.dts` + `mm810x-spi-overlay.dts`. `compatible` stops at `brcm,bcm2711`. Targets `&spi0`; `pinctrl-0 = <&spi0_pins &spi0_cs_pins &morse_wake &morse_busy &morse_irq &morse_reset>`; `cs-gpios = <&gpio 8 1>`; node `mm6108@0 { compatible="morse,mm610x-spi"; reset-gpios=<&gpio 17 0>; power-gpios=<&gpio 23 0>,<&gpio 24 0>; spi-irq-gpios=<&gpio 5 0>; spi-max-frequency=<50000000>; }`; fragment@1 defines pin groups on `&gpio` using `brcm,pins`/`brcm,function`/`brcm,pull` | **BLOCKER — needs a pi5 variant** |
| `991-0004-dt-overlays-raven-add-overlay-fragment.patch` | raven overlay, same style | 2711-only, not our target |
| `991-0005-dt-overlays-morse-add-HAT-gpios-to-gpio-line-names.patch` | renames GPIO17→`MM_RESET`, GPIO23→`MM_WAKE`, GPIO24→`MM_BUSY` in `arch/arm/boot/dts/broadcom/bcm2711-rpi-4-b.dts`. Commit message: *"The Morse 2.x userspace tooling (chipreset.sh, morse_cli.sh, switch_wifi_driver) locates the chip reset line by the MM_RESET gpio-line-name, so the names must exist in the base DT."* Targets the second (58-entry) `&gpio gpio-line-names` block added by `950-0870`. | **BLOCKER — needs an `arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts` equivalent** |
| `991-0007-spi-support-control-cs-pin-on-init.patch` | adds `SPI_CONTROLLER_ENABLE_CS_GPIOD BIT(9)` to `include/linux/spi/spi.h` and honours it in `drivers/spi/spi.c` (`spi_set_cs`, `spi_setup`) so the Morse driver can sequence CS at init | **SoC-agnostic (SPI core) — works as-is, but only if `CONFIG_SPI` is enabled** |
| `991-dt-overlays-build-morse-overlays.patch` | adds `mm610x-spi.dtbo mm810x-spi.dtbo mm_wlan.dtbo raven.dtbo` to `dtbo-$(CONFIG_ARCH_BCM2835)` in `arch/arm/boot/dts/overlays/Makefile` | needs new `*-pi5.dtbo` entries |
| `992-0001-Smuggle-board_name-model-...patch` | `sysinfo-overlay.dts`, registered under `dtbo-$(CONFIG_ARCH_BCM2835)` | **works on bcm2712 as-is** (`CONFIG_ARCH_BCM2835=y` on both) |

**Why the SPI overlay cannot simply be reused (analysis, to be confirmed on hardware):**
- On BCM2712 the label `&gpio` resolves to `rp1_gpio` (`950-1180`, `gpio: &rp1_gpio`)
  and `&spi0` to the RP1 DesignWare SSI, not the BCM2835 controller.
- `brcm,pins`/`brcm,function`/`brcm,pull` legacy properties *are* accepted by
  `pinctrl-rp1` (`950-0530` plus `950-1007-pinctrl-rp1-Allow-legacy-brcm-pins-on-all-banks.patch`,
  which supports `brcm,pins` on banks 1–2 for input/output only) — so a Pi 5
  overlay can keep the same style for bank-0 header pins, but the
  `brcm,function = <4>` (BCM2835 ALT0 = SPI0) mapping goes through
  `legacy_fsel_map[]` in `pinctrl-rp1.c` and must be validated.
- RP1 SPI max frequency and DMA behaviour differ from `spi-bcm2835`;
  `spi-max-frequency = <50000000>` may need lowering for bring-up.
- The overlay root `compatible` list must gain `"brcm,bcm2712"`.

**How RPi does per-platform overlays:** `arch/arm/boot/dts/overlays/overlay_map.dts`.
Precedents in-tree:
```
950-1098:  sdio { bcm2835; bcm2711; bcm2712 = "sdio-pi5"; };
950-1288:  ramoops { bcm2835; bcm2711 = "ramoops-pi4"; bcm2712 = "ramoops-pi4"; };
           ramoops-pi4 { bcm2711; bcm2712; };
950-0850:  arm dts overlays: add Pi 5 variants for w1-gpio overlay
950-1097:  DTS overlays: add pciex1-compat-pi5
950-0860:  pcie-32bit-dma overlay pi5
```
So the clean approach is a new `mm610x-spi-pi5-overlay.dts` plus an
`overlay_map.dts` hunk:
```
mm610x-spi { bcm2711; bcm2712 = "mm610x-spi-pi5"; };
mm610x-spi-pi5 { bcm2712; };
```
which lets `distroconfig-mm610x-spi.txt` (`dtoverlay=mm610x-spi`) stay
unchanged. Note `mm610x-spi` is currently **absent** from `overlay_map.dts`
(unlisted overlays are permitted on all platforms), so the entry must be added,
not edited.

---

## 8. Miscellaneous confirmed facts

- `.github/labeler.yml` `target/bcm27xx` already globs `target/linux/bcm27xx/**`,
  `package/kernel/bcm27xx-gpu-fw/**`, `package/utils/bcm27xx-utils/**`.
- `config/Config-images.in:297` → `TARGET_KERNEL_PARTSIZE` default `64` for all
  of `TARGET_bcm27xx`. `boards/ekh-bcm2711` sets only `TARGET_ROOTFS_PARTSIZE=4092`.
- `target/linux/armsr/armv8/config-6.6` matched the grep only incidentally
  (unrelated `BCMA`/`bcm` symbols).
- `git log` shows `target/linux/bcm27xx/bcm2712/` arrived in `8861e5a initial
  commit` (i.e. it is inherited from the OpenWrt 24.10 upstream baseline, not
  from PR #46 work in this repo).
- The `Device/rpi-5` block for reference (`image/Makefile:231-258`):
  ```
  KERNEL_IMG := kernel_2712.img
  DEVICE_DTS := broadcom/bcm2712-rpi-5-b broadcom/bcm2712-rpi-cm5-cm4io
      broadcom/bcm2712-rpi-cm5-cm5io broadcom/bcm2712-rpi-cm5l-cm4io
      broadcom/bcm2712-rpi-cm5l-cm5io broadcom/bcm2712d0-rpi-5-b
  SUPPORTED_DEVICES := raspberrypi,500 raspberrypi,5-compute-module raspberrypi,5-model-b
  DEVICE_PACKAGES := cypress-firmware-43455-sdio brcmfmac-nvram-43455-sdio
      kmod-brcmfmac wpad-basic-mbedtls kmod-i2c-bcm2835 kmod-spi-bcm2835
      kmod-i2c-brcmstb kmod-i2c-designware-platform kmod-spi-dw-mmio
      kmod-hwmon-pwmfan kmod-thermal
  IMAGE/sysupgrade.img.gz := boot-common | sdcard-img | gzip | append-metadata
  ```
  Note it does **not** include `kmod-spi-bcm2835-aux`, `kmod-usb-net-lan78xx`
  or `kmod-r8169` (all of which `Device/rpi-4` does).

---

## 9. Ordered action list

1. **`target/linux/bcm27xx/bcm2712/config-6.6`** — add the SPI block
   (`CONFIG_SPI`, `SPI_MASTER`, `SPI_DYNAMIC`, `SPI_BITBANG`, `SPI_GPIO`,
   `SPI_BCM2835`, `SPI_BCM2835AUX`, `SPI_DESIGNWARE`, `SPI_DW_MMIO`), plus
   `CONFIG_PSTORE*`/`PSTORE_RAM` and `CONFIG_USB_SERIAL*` to match bcm2711.
2. **`target/linux/bcm27xx/image/Makefile`** — add
   `Device/morse_pi5_base` (inheriting `$(Device/rpi-5)`, `IMAGE/... :=
   boot-common | boot-ekh01 | sdcard-img | gzip | append-metadata`, i.e. **no**
   `boot-2711`) and `Device/bcm2712_mm6108-spi` with
   `SUPPORTED_DEVICES += bcm2712,mm6108-spi`, `DISTROCONFIG_EXTRA := mm610x-spi`,
   `DEVICE_PACKAGES += kmod-mm6108 netifd-morse mm6108-firmware`, guarded by
   `ifeq ($(SUBTARGET),bcm2712)`. Naming the device exactly
   `bcm2712_mm6108-spi` makes `SYSINFO_BOARD_NAME` = `bcm2712,mm6108-spi`,
   which both feeds already recognise.
3. **New kernel patch `991-0006-...-mm610x-spi-pi5-overlay.patch`** (or extend
   `991-0003`): add `arch/arm/boot/dts/overlays/mm610x-spi-pi5-overlay.dts`
   targeting RP1 `&spi0`/`&gpio`, with `compatible` including `"brcm,bcm2712"`;
   add `mm610x-spi-pi5.dtbo` to `991-dt-overlays-build-morse-overlays.patch`;
   add the `overlay_map.dts` mapping `mm610x-spi { bcm2712 = "mm610x-spi-pi5"; }`.
4. **New kernel patch `991-0005`-equivalent for Pi 5** — add
   `MM_RESET`/`MM_WAKE`/`MM_BUSY` to the `gpio-line-names` in
   `arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts` (Morse `chipreset.sh`
   depends on these names).
5. **`target/linux/bcm27xx/image/boards/ekh01/distroconfig.txt`** — add a
   `[pi5]` section; move/guard `dtoverlay=uart5` so it does not apply on Pi 5;
   confirm `dtoverlay=ramoops` (needs step 1's PSTORE) and
   `dtparam=act_led_trigger=none` behave on Pi 5.
6. **`boards/ekh-bcm2712/`** — `target_diffconfig` per the table in §5, plus the
   12 symlinks into `../common_extras/` (they **must** be real symlinks —
   `openmanet_setup.sh:267-274` aborts otherwise). Drop
   `persistent-vars-storage-bcm2711`, `kmod-r8125`, `kmod-codec-bcm2835`,
   `kmod-of-mdio`; add `kmod-spi-dw`/`kmod-spi-dw-mmio` if not built in.
7. **`patches/ekh-bcm2712/`** — copy the four patches from
   `patches/ekh-bcm2711/` (especially `0005-golang-Fix-host-build-compatibility-with-GCC-15.patch`).
8. **`.github/workflows/build-pr-bcm2712.yml`** (new) and a
   `build-ekh-bcm2712` job in `build-release.yml` with
   `cpu_arch: aarch64_cortex-a76`; add it to both `needs:` lists (lines 80, 150).
9. *(optional, low risk)* **`target/linux/bcm27xx/base-files/etc/board.d/01_leds`**
   — add `bcm2712,mm6108-spi` (and `bcm2711,mm6108-spi`) to the HaLow ACT-LED case.
10. *(deferred)* Camera on Pi 5: there are no `rp1-cfe`/`pisp-be` kmod packages
    in `target/linux/bcm27xx/modules/video.mk`, and `kmod-codec-bcm2835` has no
    BCM2712 hardware behind it. Out of scope for Phase 1.

**Pi 4 regression risk of the above: none.** Every item is either a new file,
a new bcm2712-only kernel-config line, a new `ifeq ($(SUBTARGET),bcm2712)`
block, or a new CI job. The only shared files touched are
`image/Makefile` (additive device blocks), `image/boards/ekh01/distroconfig.txt`
(a new `[pi5]` section plus relocating `uart5` out of `[all]` — this one does
touch Pi 4 behaviour and must move `dtoverlay=uart5` into `[pi3]`/`[pi4]`
rather than deleting it), the morse overlay patches (additive new .dts files +
additive overlay_map entries), and optionally `01_leds` (additive case arms).
