# Morse Micro MM6108 SPI path — analysis and BCM2711 → BCM2712/RP1 port plan

Scope: how the MM6108 HaLow radio is bound over SPI today (Pi 4 / BCM2711) and exactly
what must change for Raspberry Pi 5 (BCM2712 + RP1 southbridge).

Sources analysed (cloned at the exact pins in `feeds.conf.default`):

| Source | Pin | Scratchpad path |
|---|---|---|
| `MorseMicro/morse-feed` | `fc332b01aa2df952e057efe73763de3ff71cb3b0` | `.../scratchpad/morse-feed` |
| `Gateworks/gw-openwrt-packages` | `d1d23cd0059fbee84e8d5087b47d93213d8be587` | `.../scratchpad/gw-pkgs` |
| `OpenMANET/packages` | `4736e44791166e3252ddbc4f050a784b8b5ab062` | `.../scratchpad/om-pkgs` |
| `MorseMicro/morse_driver` | tag `1.17.8` | `.../scratchpad/morse_driver` |
| `raspberrypi/linux` `rpi-6.6.y` DTs | fetched raw | `.../scratchpad/rp1.dtsi`, `bcm2712-rpi.dtsi`, `bcm2712-rpi-5-b.dts`, `overlay_map.dts` |

---

## 1. Where the MM6108 SPI binding actually lives

**The morse feed ships no device tree at all.** `find` over the whole feed returns zero
`*.dts` / `*.dtso` / `*.dtbo` files. Every MM6108 overlay lives in *this* repository as
kernel patches:

```
target/linux/bcm27xx/patches-6.6/991-0001-dt-overlays-morse-add-sdio-overlay-fragment.patch   -> mm_wlan-overlay.dts   (SDIO)
target/linux/bcm27xx/patches-6.6/991-0003-dt-overlays-morse-add-spi-overlay-fragment.patch    -> mm610x-spi-overlay.dts, mm810x-spi-overlay.dts
target/linux/bcm27xx/patches-6.6/991-0004-dt-overlays-raven-add-overlay-fragment.patch
target/linux/bcm27xx/patches-6.6/991-0005-dt-overlays-morse-add-HAT-gpios-to-gpio-line-names.patch
target/linux/bcm27xx/patches-6.6/991-0007-spi-support-control-cs-pin-on-init.patch          -> drivers/spi/spi.c
target/linux/bcm27xx/patches-6.6/991-dt-overlays-build-morse-overlays.patch                 -> overlays/Makefile
target/linux/bcm27xx/patches-6.6/992-0001-Smuggle-board_name-model-into-userspace-via-devicetr.patch -> sysinfo-overlay.dts
```

Binding is a **platform SPI slave via device tree overlay**, not `spidev`. The overlay
explicitly disables `spidev0`/`spidev1`.

### Driver / packaging

* Kernel module source: external git, `https://github.com/MorseMicro/morse_driver.git`
  (morse feed, `essentials/morse_driver/Makefile`, version from
  `include/morse_version.mk` → **1.17.8** for MM61x). Builds `morse.ko` + `dot11ah/dot11ah.ko`,
  `PROVIDES:=kmod-morse`, `MODPARAMS.morse:=country=US`.
* SPI support is a build-time switch: `CONFIG_MORSE_SPI` (default **n**) in
  `essentials/morse_driver/Config.in`, mapped to `CONFIG_MORSE_SPI=y` in
  `include/morse_driver_common.mk`. This repo turns it on in
  `boards/common_extras/spi_diffconfig` (symlinked as `boards/ekh-bcm2711/spi_diffconfig`):

  ```
  CONFIG_MORSE_SPI=y
  CONFIG_PACKAGE_kmod-spi-bcm2835=y
  CONFIG_PACKAGE_kmod-spi-bcm2835-aux=y
  CONFIG_PACKAGE_kmod-spi-bitbang=y
  CONFIG_PACKAGE_kmod-spi-gpio=y
  ```

* Compatible strings — `morse_driver/spi.c:182`:

  ```c
  static const struct of_device_id morse_spi_of_match[] = {
      {.compatible = "morse,mm610x-spi", (const void *)&mm61xx_chip_series },
      {.compatible = "morse,mm810x-spi", (const void *)&mm81xx_chip_series },
  ```
  (SDIO path uses `morse,mm610x`, see `mm_wlan-overlay.dts`.)

* DT properties consumed — `morse_driver/of.c` (`morse_of_probe`), all via the **legacy
  integer** `of_get_named_gpio()` API:
  * `power-gpios` index 0 → `mm_wake_gpio`
  * `power-gpios` index 1 → `mm_ps_async_gpio` (BUSY)
  * `reset-gpios` index 0 → `mm_reset_gpio` (**required**, probe fails without it)
  * `spi-irq-gpios` index 0 → `mm_spi_irq_gpio` (**required for SPI**, `spi.c:1502`)

* SPI limits in `spi.c`: `MAX_SUPPORTED_SPI_CLK_SPEED = 50 MHz` (clamped),
  `SPI_MAX_TRANSACTION_SIZE = 8192`, `MM610X_BUF_SIZE = 8 KiB`,
  module params `spi_clock_speed`, `spi_inter_block_delay_bytes`, `spi_use_edge_irq`.

* Chip-select quirk: the chip needs 74 clocks with **CS high** before CMD0
  (`morse_spi_initsequence()`), so the driver toggles `SPI_CS_HIGH` via `spi_setup()`.
  Kernel ≥6.1 forces `SPI_CS_HIGH` for GPIO descriptor CS, which breaks this. The driver
  sets `spi->controller->flags |= SPI_CONTROLLER_ENABLE_CS_GPIOD` (`spi.c:1456`), a flag
  that **only exists because of** `991-0007-spi-support-control-cs-pin-on-init.patch`,
  which patches generic `drivers/spi/spi.c` + `include/linux/spi/spi.h`. Being generic
  core-SPI code, it applies equally to the RP1 DesignWare controller — **no change needed**,
  but it must stay applied for the bcm2712 subtarget.

---

## 2. The SPI overlay (the critical piece)

### 2.1 Full current text — `mm610x-spi-overlay.dts`

From `target/linux/bcm27xx/patches-6.6/991-0003-dt-overlays-morse-add-spi-overlay-fragment.patch`
(the `mm810x-spi-overlay.dts` in the same patch is byte-identical except
`mm8108`/`morse,mm810x-spi`):

```dts
/dts-v1/;
/plugin/;

/ {
	compatible = "brcm,bcm2835", "brcm,bcm2836", "brcm,bcm2837",
	             "brcm,bcm2708", "brcm,bcm2709", "brcm,bcm2710", "brcm,bcm2711";

	fragment@0 {
		target = <&spi0>;
		frag0: __overlay__ {
			pinctrl-0 = <&spi0_pins &spi0_cs_pins &morse_wake &morse_busy &morse_irq &morse_reset>;
			cs-gpios = <&gpio 8 1>;
			#address-cells = <1>;
			#size-cells = <0>;
			status = "okay";

			mm6108: mm6108@0 {
				compatible = "morse,mm610x-spi";
				reg = <0>; /* CE0 */
				reset-gpios = <&gpio 17 0>;
				power-gpios = <&gpio 23 0>,
				              <&gpio 24 0>;
				spi-irq-gpios = <&gpio 5 0>;
				spi-max-frequency = <50000000>;
				status = "okay";
			};

			spidev0: spidev@0 {
				reg = <0>; /* CE0 */
				status = "disabled";
			};

			spidev1: spidev@1 {
				reg = <1>; /* CE1 */
				status = "disabled";
			};
		};
	};

	fragment@1 {
		target = <&gpio>;
		__overlay__ {
			spi0_cs_pins: spi0_cs_pins {
				brcm,pins = <8>;
				brcm,function = <1>; /* BCM2835_FSEL_GPIO_OUT */
				brcm,pull = <2>;     /* SET SPI PINS AS PULL HIGH */
			};
			spi0_pins: spi0_pins {
				brcm,pins = <9 10 11>;
				brcm,function = <4>; /* BCM2835_FSEL_ALT0 (SPI0) */
				brcm,pull = <2 2 2>; /* SET SPI PINS AS PULL HIGH */
			};

			morse_wake: morse_wake {
				brcm,pins = <23>;
				brcm,function = <0>; /* BCM2835_FSEL_GPIO_IN */
				brcm,pull = <2>;     /* PULL UP */
			};

			morse_busy: morse_busy {
				brcm,pins = <24>;
				brcm,function = <0>; /* BCM2835_FSEL_GPIO_IN */
				brcm,pull = <1>;     /* PULL DOWN */
			};

			morse_irq: morse_irq {
				brcm,pins = <5>;
				brcm,function = <0>; /* BCM2835_FSEL_GPIO_IN */
				brcm,pull = <2>;     /* PULL UP */
			};

			morse_reset: morse_reset {
				brcm,pins = <17>;
				brcm,function = <0>; /* BCM2835_FSEL_GPIO_IN */
				brcm,pull = <2>;     /* PULL UP */
			};

		};
	};
};
```

### 2.2 Signal map (unchanged by the port — same 40-pin header pins)

| Function | BCM GPIO | Header pin | DT property |
|---|---|---|---|
| SPI0 CE0 (chip select) | GPIO8 | 24 | `cs-gpios = <&gpio 8 1>` (`GPIO_ACTIVE_LOW`), `reg = <0>` |
| SPI0 MISO / MOSI / SCLK | GPIO9 / 10 / 11 | 21 / 19 / 23 | `spi0_pins` |
| MM_RESET | GPIO17 | 11 | `reset-gpios = <&gpio 17 0>` |
| MM_WAKE | GPIO23 | 16 | `power-gpios[0]` |
| MM_BUSY (ps-async) | GPIO24 | 18 | `power-gpios[1]` |
| MM SPI IRQ | GPIO5 | 29 | `spi-irq-gpios = <&gpio 5 0>` |
| Max SPI clock | — | — | `spi-max-frequency = <50000000>` |

Note the OpenMANET wiring deviates from the Morse eval kit: `991-0005` documents that the
Seeed WM1302 Pi HAT uses **reset GPIO17, wake GPIO23, busy GPIO24** where Morse upstream
used GPIO5/GPIO3/GPIO7.

### 2.3 SDIO overlay for reference — `mm_wlan-overlay.dts`

`target = <&mmc>`, `compatible = "morse,mm610x"`, `reg = <2>`, `bus-width = <4>`,
`reset-gpios = <&gpio 17 0>`, `power-gpios = <&gpio 3 0>, <&gpio 7 0>`, SDIO pins
GPIO22–27 (`ALT3`), chip IRQ on GPIO1. **This overlay is BCM2711-only in a hard way**:
`&mmc` (the legacy `sdhost`/`mmc` block) does not exist on BCM2712 — SDIO on Pi 5 is
RP1/`&sdio1`/`&sdio2`. SDIO is out of scope for the production path but worth noting.

### 2.4 How the overlay is selected at boot

`target/linux/bcm27xx/image/Makefile`, `Build/boot-ekh01` concatenates
`boards/ekh01/distroconfig.txt` + `boards/ekh01/distroconfig-$(DISTROCONFIG_EXTRA).txt`
+ a generated `dtoverlay=sysinfo,...` line into `/boot/distroconfig.txt`.

`target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm610x-spi.txt` (entire file):

```
dtparam=spi=on
dtoverlay=mm610x-spi
```

and `Device/bcm2711_mm6108-spi` sets `DISTROCONFIG_EXTRA := mm610x-spi`,
`SUPPORTED_DEVICES += ... bcm2711,mm6108-spi`.

`boards/ekh01/distroconfig.txt` also carries `[pi4] dtoverlay=miniuart-bt`,
`dtoverlay=uart5`, `dtoverlay=ramoops`, `dtparam=act_led_trigger=none`,
`camera_auto_detect=1`. Several of these need Pi 5 review (`uart5` and `miniuart-bt`
do not exist / behave differently on BCM2712; `ramoops-pi4` vs `ramoops`).

---

## 3. What BCM2712/RP1 changes — the concrete deltas

Ground truth from `raspberrypi/linux` `rpi-6.6.y`:

* `arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts:20` does `#define spi0 _spi0` … `#undef spi0`
  around the BCM2712 include, then `bcm2712-rpi.dtsi:363` re-labels:
  ```dts
  spi0: &rp1_spi0 { };
  spi1: &rp1_spi1 { };
  ...
  ```
  → **`&spi0` on Pi 5 already resolves to the RP1 controller.** The label target does *not*
  need changing. The BCM2712 native SPI0 is renamed `spi10`.
* `rp1.dtsi:179` — `rp1_spi0: spi@50000 { compatible = "snps,dw-apb-ssi"; ... num-cs = <2>; status = "disabled"; }`
  → driver is **`spi-dw-mmio`**, not `spi-bcm2835`.
* `bcm2712-rpi-5-b.dts:236` — `gpio: &rp1_gpio { }` → **`&gpio` resolves to `rp1_gpio`**
  (`compatible = "raspberrypi,rp1-gpio"`), so `<&gpio 17 0>` style phandles keep working
  and land on the same physical header pins. GPIO numbering 0–53 is preserved.
* `bcm2712-rpi.dtsi:428` **already defines the labels the morse overlay tries to create**:
  ```dts
  spi0_pins: &rp1_spi0_gpio9 {};
  spi0_cs_pins: &rp1_spi0_cs_gpio7 {};

  &spi0 {
  	pinctrl-names = "default";
  	pinctrl-0 = <&spi0_pins &spi0_cs_pins>;
  	cs-gpios = <&gpio 8 1>, <&gpio 7 1>;
  	spidev0: spidev@0 { ... };
  	spidev1: spidev@1 { ... };
  };
  ```
  and `bcm2712-rpi.dtsi:224` has `spi = <&spi0>, "status";` so `dtparam=spi=on` still works.
* RP1 pin groups (`rp1.dtsi:910`) use the **generic pinconf binding**, not `brcm,*`:
  ```dts
  rp1_spi0_gpio9: rp1_spi0_gpio9 {
  	function = "spi0";
  	pins = "gpio9", "gpio10", "gpio11";
  	bias-disable;
  	drive-strength = <12>;
  	slew-rate = <1>;
  };
  rp1_spi0_cs_gpio7: rp1_spi0_cs_gpio7 {
  	function = "spi0";
  	pins = "gpio7", "gpio8";
  	bias-pull-up;
  };
  ```

### Consequences for `mm610x-spi-overlay.dts` on Pi 5

| Item | Pi 4 (BCM2711) | Pi 5 (BCM2712/RP1) | Action |
|---|---|---|---|
| `target = <&spi0>` | `spi@7e204000` (bcm2835) | `rp1_spi0` (`snps,dw-apb-ssi`) | **keep** |
| `target = <&gpio>` (fragment@1) | `bcm2835-gpio` | `rp1_gpio` | keep label, **rewrite contents** |
| `brcm,pins` / `brcm,function` / `brcm,pull` | valid | **not understood by `pinctrl-rp1`** | rewrite as `function`/`pins`/`bias-*` |
| Redefining `spi0_pins` / `spi0_cs_pins` labels | needed (overlay creates them) | **they already exist** in `bcm2712-rpi.dtsi`; overlay redefinition collides / injects bogus `brcm,*` props into `rp1_gpio` | drop; reuse base labels |
| `cs-gpios = <&gpio 8 1>` | needed | base already sets `<&gpio 8 1>, <&gpio 7 1>` | harmless to restate as CE0-only, or omit |
| `spidev0` / `spidev1` disable | needed | still needed (base enables them) | keep |
| `compatible` header list | lists bcm2708…bcm2711 | must include `brcm,bcm2712` | add |
| Overlay name | `mm610x-spi` | needs a distinct `mm610x-spi-pi5` (see §3.1) | new file |
| `spi-max-frequency = <50000000>` | bcm2835 divides core clock | DW-SSI on RP1 derives from `RP1_CLK_SYS`; 50 MHz is within range but should be validated on hardware; driver clamps at 50 MHz anyway | keep 50 MHz, fall back via `spi_clock_speed` modparam if unstable |
| `SPI_CONTROLLER_ENABLE_CS_GPIOD` patch | required | required (generic `drivers/spi/spi.c`) | keep applied for bcm2712 |
| `MM_RESET`/`MM_WAKE`/`MM_BUSY` gpio-line-names (`991-0005`) | patches `bcm2711-rpi-4-b.dts` | Pi 5 names live in `bcm2712-rpi-5-b.dts:681` `&rp1_gpio { gpio-line-names = ... }` | **new patch needed** |

### 3.1 Overlay naming: the platform remap map is NOT available in OpenWrt images

`raspberrypi/linux` normally disambiguates same-named overlays per SoC via
`arch/arm/boot/dts/overlays/overlay_map.dts` → `overlay_map.dtb`, e.g.:

```dts
disable-bt { bcm2835; bcm2711; bcm2712 = "disable-bt-pi5"; };
disable-bt-pi5 { bcm2712; };
```

But `Build/boot-common` in `target/linux/bcm27xx/image/Makefile` copies only:

```
mcopy -i $@.boot $(DTS_DIR)/overlays/*.dtbo ::/overlays/
mcopy -i $@.boot $(DTS_DIR)/overlays/README ::/overlays/
```

`overlay_map` is a `dtb-` target (`overlays/Makefile:3`: `dtb-$(CONFIG_ARCH_BCM2835) += overlay_map.dtb hat_map.dtb`),
so **`overlay_map.dtb` never reaches `/boot/overlays`** and the firmware performs no
per-SoC remapping or rejection. Therefore: do **not** rely on `bcm2712 = "mm610x-spi-pi5"`.
Ship a separately-named overlay and select it explicitly from the Pi 5 `distroconfig`.

### 3.2 Proposed Pi 5 overlay

New file `arch/arm/boot/dts/overlays/mm610x-spi-pi5-overlay.dts` (added by a new
`target/linux/bcm27xx/patches-6.6/991-0008-*` patch, plus one line in the
`991-dt-overlays-build-morse-overlays.patch` Makefile hunk):

```dts
/dts-v1/;
/plugin/;

/ {
	compatible = "brcm,bcm2712";

	fragment@0 {
		target = <&spi0>;			/* == rp1_spi0 on BCM2712 */
		__overlay__ {
			/* base bcm2712-rpi.dtsi already sets spi0_pins + spi0_cs_pins;
			 * append only the morse control-line pin groups.
			 */
			pinctrl-names = "default";
			pinctrl-0 = <&spi0_pins &spi0_cs_pins
			             &morse_wake &morse_busy &morse_irq &morse_reset>;
			cs-gpios = <&gpio 8 1>;
			#address-cells = <1>;
			#size-cells = <0>;
			status = "okay";

			mm6108: mm6108@0 {
				compatible = "morse,mm610x-spi";
				reg = <0>;			/* CE0 */
				reset-gpios = <&gpio 17 0>;
				power-gpios = <&gpio 23 0>,
				              <&gpio 24 0>;
				spi-irq-gpios = <&gpio 5 0>;
				spi-max-frequency = <50000000>;
				status = "okay";
			};
		};
	};

	fragment@1 {
		target = <&spidev0>;
		__overlay__ { status = "disabled"; };
	};

	fragment@2 {
		target = <&spidev1>;
		__overlay__ { status = "disabled"; };
	};

	fragment@3 {
		target = <&gpio>;			/* == rp1_gpio on BCM2712 */
		__overlay__ {
			morse_wake: morse_wake {
				function = "gpio";
				pins = "gpio23";
				bias-pull-up;
			};
			morse_busy: morse_busy {
				function = "gpio";
				pins = "gpio24";
				bias-pull-down;
			};
			morse_irq: morse_irq {
				function = "gpio";
				pins = "gpio5";
				bias-pull-up;
			};
			morse_reset: morse_reset {
				function = "gpio";
				pins = "gpio17";
				bias-pull-up;
			};
		};
	};
};
```

Notes:
* `spidev0`/`spidev1` are disabled by phandle fragments instead of re-declaring child nodes,
  because the base dtsi already declares them under `&spi0`.
* If overlay compilation complains about the `&spi0_pins` / `&spi0_cs_pins` phandles not
  resolving (they are defined in the base DT, so `__fixups__` should handle it), the
  fallback is to omit them from `pinctrl-0` — the base `&spi0` node already applies them —
  and use a second `pinctrl-1`/hog-style approach for the morse lines.
* Alternative, lower-risk first cut: **drop `fragment@3` and the morse pinctrl entries
  entirely**. `pinctrl-rp1` muxes a pin to `gpio` automatically on `gpiod` request via
  `gpio-ranges`, and the WM1302 HAT provides its own pull resistors. Only bias configuration
  is lost. Try this if pinctrl fixups misbehave.

### 3.3 Companion kernel patch — gpio-line-names on Pi 5

`991-0005` renames GPIO17/23/24 to `MM_RESET`/`MM_WAKE`/`MM_BUSY` in
`arch/arm/boot/dts/broadcom/bcm2711-rpi-4-b.dts`. This is **load-bearing**, not cosmetic:
* `morse-feed/hardware/morse-bundle/files/morse/scripts/chipreset.sh` does
  `gpioinfo -s --by-name MM_RESET` and `exit 1` if absent;
* `netifd-morse` `get_vfem_4v3_bcf()` probes `gpioinfo -s --by-name MM_BOOST`.

A matching patch must edit `arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts`, in the
`&rp1_gpio { gpio-line-names = ... }` block (line ~681), replacing `"GPIO17"` → `"MM_RESET"`,
`"GPIO23"` → `"MM_WAKE"`, `"GPIO24"` → `"MM_BUSY"`.

Also note `om-pkgs/boards/bsp-bcm271x/files/etc/init.d/bcm2710-morse-fix` neuters
`chipreset.sh` on `bcm2710,*` because the vendor script unbinds the first `mmc_host` before
checking for `MM_RESET`. On Pi 5 the first `mmc_host` is the RP1 SD controller that carries
the rootfs — **the same hazard exists**. Either add `bcm2712,*` to that guard, or (better)
ship the `MM_RESET` line name so `chipreset.sh` completes its rebind.

### 3.4 Kernel config for bcm2712

`target/linux/bcm27xx/bcm2712/config-6.6` currently contains **no `CONFIG_SPI*` symbols at
all** (`CONFIG_SPI`, `CONFIG_SPI_MASTER`, `CONFIG_SPI_DW*` are absent), whereas
`bcm2711/config-6.6` has `CONFIG_SPI=y`, `CONFIG_SPI_BCM2835=y`, `CONFIG_SPI_BCM2835AUX=y`,
`CONFIG_SPI_BITBANG=y`, `CONFIG_SPI_GPIO=y`, `CONFIG_SPI_MASTER=y`, `CONFIG_SPI_DYNAMIC=y`.

`Device/rpi-5` already lists `kmod-spi-bcm2835`, `kmod-i2c-designware-platform` and
`kmod-spi-dw-mmio` in `DEVICE_PACKAGES`, and `kmod-spi-dw-mmio` exists
(`package/kernel/linux/modules/spi.mk:98`, `DEPENDS:=+kmod-spi-dw`,
`KCONFIG:=CONFIG_SPI_DW_MMIO`). Those kmods will pull `CONFIG_SPI_MASTER` in, but for a
built-in-at-boot SPI slave it is far safer to make the controller **built-in**:

```
# target/linux/bcm27xx/bcm2712/config-6.6
CONFIG_SPI=y
CONFIG_SPI_MASTER=y
CONFIG_SPI_DYNAMIC=y
CONFIG_SPI_DESIGNWARE=y
CONFIG_SPI_DW_DMA=y
CONFIG_SPI_DW_MMIO=y
```

`PINCTRL_RP1=y`, `MFD_RP1=y`, `COMMON_CLK_RP1=y` are already present, and
`CONFIG_ARCH_BCM2835=y` is set for bcm2712 — so the overlays `Makefile` hunk
(`dtbo-$(CONFIG_ARCH_BCM2835) += mm610x-spi.dtbo ...`) will build the new
`mm610x-spi-pi5.dtbo` for the bcm2712 subtarget too. Both subtargets use `ARCH:=aarch64`
(`bcm2711/target.mk`, `bcm2712/target.mk`) so `DTS_DIR = arch/arm64/boot/dts` and the
overlays directory is the same shared tree.

Also create a Pi-5 board diffconfig equivalent to `boards/common_extras/spi_diffconfig`
that does **not** force `kmod-spi-bcm2835*` (harmless but useless on RP1) and instead
selects `kmod-spi-dw` / `kmod-spi-dw-mmio` if they are kept modular.

### 3.5 Image plumbing

New files/edits:

1. `target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm610x-spi-pi5.txt`:
   ```
   dtparam=spi=on
   dtoverlay=mm610x-spi-pi5
   ```
2. `target/linux/bcm27xx/image/Makefile`: a `Device/morse_pi5_base` deriving from
   `Device/rpi-5` (mirroring `Device/morse_ekh01_base`, but with the Pi 5 image recipe —
   `boot-common | boot-ekh01 | sdcard-img | gzip | append-metadata`; **no `boot-2711`**,
   Pi 5 boots from EEPROM and needs no `start4.elf`/`fixup4.dat`), plus:
   ```make
   define Device/bcm2712_mm6108-spi
     $(Device/morse_pi5_base)
     DEVICE_MODEL := RPI5-MM6108
     DEVICE_VARIANT := SPI
     SYSINFO_MODEL := $$(DEVICE_VENDOR) $$(DEVICE_MODEL) ($$(DEVICE_VARIANT))
     DEVICE_PACKAGES += kmod-mm6108 netifd-morse mm6108-firmware ...
     SUPPORTED_DEVICES += bcm2712,mm6108-spi
     DISTROCONFIG_EXTRA := mm610x-spi-pi5
   endef
   ifeq ($(SUBTARGET),bcm2712)
     TARGET_DEVICES += bcm2712_mm6108-spi
   endif
   ```
   `KERNEL_IMG := kernel_2712.img` comes from `Device/rpi-5`.
3. New `boards/ekh-bcm2712/` with `target_diffconfig` (+ symlinks) modelled on
   `boards/ekh-bcm2711/target_diffconfig`, setting
   `CONFIG_TARGET_bcm27xx_bcm2712=y` and
   `CONFIG_TARGET_DEVICE_bcm27xx_bcm2712_DEVICE_bcm2712_mm6108-spi=y`.
   Note `openmanet_setup.sh` **requires every non-`target_diffconfig` file in a board dir to
   be a symlink** (it aborts otherwise).
4. `boards/ekh01/distroconfig.txt` (the shared prologue) — review `[pi4]`-gated lines and
   add a `[pi5]` section; `dtoverlay=uart5` and `dtoverlay=miniuart-bt` are BCM2711-era.

**Good news:** `om-pkgs/boards/bsp-common/files/uci-defaults/99_morse_radio_defaults`
**already** matches `bcm2712,mm6108-spi` and `bcm2712,mm6108-sdio` — the Pi 5 board names
are pre-wired on the userspace side. `persistent-vars-storage-bcm2711` is `@TARGET_bcm27xx_bcm2711`
gated, so a Pi 5 board needs its own (or none — `build_mod_params()` degrades gracefully
when `persistent_vars_storage.sh` is missing).

---

## 4. Firmware + BCF packages

Two competing sources are in play. **The one this repo actually builds is Gateworks', not
the morse feed's.**

### 4.1 `mm6108-firmware` (Gateworks — the one referenced by `image/Makefile`)

`gw-pkgs/gateworks/morse-micro/mm6108-firmware/Makefile`, version `2.0.1`,
tarball `https://dev.gateworks.com/sources/mm6108-firmware-2.0.1-gateworks.tar.gz`:

```make
define Package/mm6108-firmware/install
	$(INSTALL_DIR) $(1)/lib/firmware/morse
	$(INSTALL_DATA) "$(PKG_BUILD_DIR)/mm6108-$(PKG_VERSION)/silex_1_16_4_5V.bin" $(1)/lib/firmware/morse/
	$(LN) silex_1_16_4_5V.bin $(1)/lib/firmware/morse/bcf_default.bin
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/mm6108-$(PKG_VERSION)/mm6108.bin $(1)/lib/firmware/morse/
endef
```

→ `/lib/firmware/morse/mm6108.bin` (chip firmware),
`/lib/firmware/morse/silex_1_16_4_5V.bin` (BCF), `bcf_default.bin` → symlink to it.

### 4.2 `morse-fw` / `morse-board-config` (morse feed — the full BCF set)

* `morse-feed/essentials/morse-fw/Makefile` → `morse-fw-6108` installs `mm6108.bin`
  (also `-tlm` thin-LMAC variant) into `/lib/firmware/morse/`. Source
  `https://github.com/MorseMicro/morse-firmware.git` @ `1.17.8`.
* `morse-feed/essentials/mm-board-config/Makefile` (`PKG_NAME:=morse-board-config`) installs
  **every** `bcf/**/*.bin` from the morse-firmware repo into `/lib/firmware/morse/`, plus
  `files/lib/firmware/morse/bcf_failsafe.bin`, symlinks `bcf_default.bin` → `bcf_failsafe.bin`,
  and installs `/usr/share/morse-bcf/db.txt`.
* `db.txt` maps OTP `board_type` → module id / chip:
  ```
  0801,05us,mf08651_us,MM6108
  0804,01,mf15457,M8108
  0805,06,mf16858,MM6108
  0807,01,mf15457,MM8108
  0808,02US,mm8108_m20_us,MM8108
  0a02,01,mf15457,MM8108
  ```
  It is used only by `morse-board-config-hotplug-model`
  (`/etc/hotplug.d/ieee80211/20-module-type`) to prettify `/tmp/sysinfo/model` — **not** for
  BCF selection.

### 4.3 How a BCF is actually chosen

Order of precedence, per `morse-feed/essentials/netifd-morse/lib/netifd/wireless/morse.sh`
(`build_mod_params`, ~line 133):

1. `uci get wireless.radioN.bcf` — explicit, wins.
2. else `persistent_vars_storage.sh READ mm_sku` → try `bcf_<sku>.bin`.
3. else nothing is passed and the driver loads `bcf_default.bin` (`firmware.c`) — or, when
   the chip has OTP board-type bits burnt, `bcf_boardtype_<id>.bin`.
4. If `vfem_4v3=1`, the name is rewritten `bcf_x.bin` → `bcf_x_4v3.bin` (requires an
   `MM_BOOST` gpio-line-name and the file to exist).

The value ends up as the `bcf=` module parameter on `morse.ko`.

`uci` default comes from
`om-pkgs/boards/bsp-common/files/uci-defaults/99_morse_radio_defaults`:

```sh
morse,mm6108-ekh01-spi|\
bcm2711,mm6108-spi|\
bcm2710,mm6108-spi|\
bcm2712,mm6108-spi)
        bcf=bcf_fgh100mhaamd.bin
;;
# This is the default build target for OpenMANET
morse,ekh01)
        bcf=bcf_fgh100mhaamd.bin
;;
```

**→ The BCF for the OpenMANET SPI HaLow module (WM1302 / Wio-WM6108 path) is
`bcf_fgh100mhaamd.bin`**, and the Pi 5 board name `bcm2712,mm6108-spi` is already mapped
to it. The SDIO variant uses `bcf_mf04151.bin`, which `bsp-bcm271x` ships explicitly
(`om-pkgs/boards/bsp-bcm271x/files/lib/firmware/morse/bcf_mf04151.bin`).

**Action item:** `bcf_fgh100mhaamd.bin` is not in the Gateworks `mm6108-firmware` package
(which only ships `silex_1_16_4_5V.bin`) and is not shipped in `bsp-bcm271x`. It must be
coming from `morse-board-config` (the morse-firmware `bcf/` directory). Confirm it is
present in a built rootfs at `/lib/firmware/morse/bcf_fgh100mhaamd.bin`; if not, the Pi 5
BSP package must ship it the way `bsp-bcm271x` ships `bcf_mf04151.bin`.

The same script sets the rest of the radio defaults, including regulatory:

```sh
uci -q set wireless."${config}".channel='42'
uci -q set wireless."${config}".country='US'
uci -q set wireless."${config}".enable_ps=0
...
[ -f /etc/modules.d/mm6108 ] && uci -q set wireless."${config}".enable_ext_xtal_init=1
```

`enable_ext_xtal_init=1` matters for SPI: `spi.c` uses it to force an early digital reset and
to assume the MM610x chip series before the chip ID is readable.

---

## 5. Userspace: netifd-morse, hostapd_s1g, morsecli

| Package | Path | Notes |
|---|---|---|
| `netifd-morse` | `morse-feed/essentials/netifd-morse` | `DEPENDS:= kmod-morse +morse-regdb +wpa_supplicant_s1g +hostapd_s1g +morsecli`. Ships `/lib/wifi/morse.sh` (detect), `/lib/netifd/wireless/morse.sh` (setup, builds `MOD_PARAMS`, rewrites `/etc/modules.d/*`), `/lib/netifd/morse/morse_{overrides,utils}.sh`, uci-defaults + ieee80211 hotplug. Radio detection requires the driver dir basename to match `^morse_` and creates `wireless.radioN` with `type=morse band=s1g hwmode=11ah`. |
| `hostapd_s1g` | `morse-feed/essentials/hostapd_s1g` | Morse fork of hostap (`https://github.com/MorseMicro/hostap.git` @ `1.17.8`), `DEPENDS:= kmod-morse +kmod-cfg80211 +morsecli ...`. Config symbols `MORSE_HOSTAPD_S1G_EAP`, `MORSE_HOSTAPD_S1G_ACS`, `MORSE_HOSTAPD_APSTA_HANDLER` — the first two are enabled in `boards/common/openmanet_diffconfig`. |
| `wpa_supplicant_s1g` / `libwpa_client_s1g` | same package tree | selected via `openmanet-morse-stack`. |
| `morsecli` | `morse-feed/essentials/morsecli` | `/sbin/morse_cli`, built `CONFIG_MORSE_TRANS_NL80211=1 DEFAULT_INTERFACE_NAME=wlh0`, plus `/etc/profile.d/morse_cli.sh`. |
| `morse-bundle` | `morse-feed/hardware/morse-bundle` | `/morse/scripts/chipreset.sh` (the `MM_RESET` gpio consumer), `morse-wireless-defaults`, board.d, uci-defaults. Installs `files/etc/init.d_bcm2711/*` only when `CONFIG_TARGET_bcm27xx_bcm2711` — **needs a bcm2712 arm** if that content is wanted on Pi 5. |
| `openmanet-morse-stack` | `om-pkgs/morse-micro/openmanet-morse-stack` | Metapackage listing the whole radio-agnostic userspace; drivers/firmware deliberately excluded (they are per-board policy). Enabled once via `CONFIG_PACKAGE_openmanet-morse-stack=y` in `boards/common/openmanet_diffconfig`. **This is radio-agnostic and needs no Pi 5 change.** |

None of these packages are SoC-aware except `morse-bundle`'s `init.d_bcm2711` guard and
`persistent-vars-storage-bcm2711` (`@TARGET_bcm27xx_bcm2711`).

---

## 6. Region / country (US, 900 MHz)

Three layers, all already US-correct:

1. **Driver default** — `MODPARAMS.morse:=country=US` in the morse-feed and OpenMANET
   `morse_driver` Makefiles; `MODPARAMS.mm6108_sdio:=country=US enable_ext_xtal_init=1` in
   the Gateworks package (`CONFIG_MORSE_COUNTRY=US` build define too).
2. **UCI** — `wireless.radioN.country='US'` and `channel='42'` set by
   `om-pkgs/boards/bsp-common/files/uci-defaults/99_morse_radio_defaults`.
   `netifd-morse` passes `country` through as a `morse.ko` module param
   (`MM_MOD_STRING="serial country test_mode ..."`, `morse.sh:31`) and into the
   hostapd/wpa_supplicant config (`morse_overrides.sh:801,830`).
   `morse.sh:473` refuses a country that conflicts with an OTP-locked `mm_region`.
3. **Regulatory database** — `morse-regdb` installs `/usr/share/morse-regdb/channels.csv`
   (and `/www/halow-channels.csv`). Lookups happen in
   `netifd-morse/lib/netifd/morse/morse_utils.sh` `_get_regulatory()`. US rows
   (`morse-feed/essentials/morse-regdb/artefacts/repo_channels.csv`) — 48 entries:
   ```
   US,1,1,1,68,902.5,100.0,100.0,USA,36.0,False,0.0,0.0,0.0,132
   US,1,3,1,68,903.5,100.0,100.0,USA,36.0,False,0.0,0.0,0.0,136
   ...
   ```
   i.e. S1G op class 1 / global 68, 902.5 MHz upward, 100 % duty cycle, 36 dBm EIRP cap.
   The upstream repo is private; the package uses the cached CSV unless `REGENERATE=1`.

Also relevant: `boards/common/openmanet_diffconfig` sets
`CONFIG_CFG80211_CERTIFICATION_ONUS=y` and `CONFIG_CFG80211_REQUIRE_SIGNED_REGDB=n`.
**All of this is SoC-independent — nothing to change for Pi 5.**

---

## 7. References to BCM2712 / RP1 / Pi 5 in the morse feed

**None.** A case-insensitive grep for `bcm2712|rp1|raspberry ?pi ?5|pi-5|pi5` across the
whole feed matches only two binary PDFs
(`luci-app-halowlinkguide/root/www/HaLowLink_User_Guide_2.11-v2.pdf`,
`luci-app-morseguide/root/www/UG MM6108_MM8108 Eval Kit User Guide 2.11 - v27.pdf`).
BCM2711 references are limited to `hardware/morse-bundle/Makefile` (the `init.d_bcm2711`
install guard) and `hardware/persistent-vars-storage-bcm2711`.

**The morse feed carries zero Pi 5 support. All BCM2712 work is ours to add, in this
repository's `target/linux/bcm27xx` tree and in the OpenMANET packages feed.**

---

## 8. ⚠ Open issue found while tracing: the `-spi` profile may not ship an SPI driver

`Device/bcm2711_mm6108-spi` in `target/linux/bcm27xx/image/Makefile` selects
`kmod-mm6108 netifd-morse mm6108-firmware`, and
`boards/ekh-bcm2711/target_diffconfig` sets `CONFIG_PACKAGE_kmod-mm6108=y`.

`kmod-mm6108` resolves to the **Gateworks** package
`gw-pkgs/gateworks/morse-micro/mm6108-driver/Makefile`, which builds **`mm6108_sdio.ko`
only**:

```make
define KernelPackage/mm6108_sdio
  TITLE:=Morse Micro WIFI HaLow mm6108 SDIO driver
  FILES:= $(PKG_BUILD_DIR)/mm6108_sdio.ko
  AUTOLOAD:=$(call AutoProbe,mm6108_sdio)
  MODPARAMS.mm6108_sdio:=country=US enable_ext_xtal_init=1
  PROVIDES:=kmod-mm6108
endef
...
MORSE_MAKEDEFS += ... CONFIG_MORSE_SDIO=y ...   # no CONFIG_MORSE_SPI
```

There is no `CONFIG_MORSE_SPI` in that package, so the resulting module registers no
`morse,mm610x-spi` OF match and cannot bind the SPI overlay's `mm6108@0` node.

Meanwhile `CONFIG_MORSE_SPI=y` in `boards/common_extras/spi_diffconfig` belongs to a
*different* package — `kmod-morse` (`om-pkgs/drivers/morse_driver`, a Gateworks 1.16.4 fork;
the morse feed also defines a `kmod-morse`, but `openmanet_setup.sh` installs
`-p openmanet` first so the OpenMANET one wins). The comments in
`boards/ekh-bcm2711/target_diffconfig` state that the userspace stack's `kmod-morse`
dependency is satisfied by `kmod-mm6108`/`kmod-mm8108` `PROVIDES`, which implies the real
`kmod-morse` may not be built at all.

**This needs verification before Pi 5 hardware bring-up.** Check a built image for
`/lib/modules/*/morse.ko` vs `mm6108_sdio.ko` and for
`morse,mm610x-spi` in the module's `modalias`/`modinfo`. If the SPI-capable module is
absent, the fix is either:
* set `CONFIG_PACKAGE_kmod-morse=y` (OpenMANET `morse_driver`) with `CONFIG_MORSE_SPI=y`
  for the SPI board, dropping `kmod-mm6108` from that profile; or
* add an `mm6108_spi` variant to the Gateworks package (`CONFIG_MORSE_SPI=y`).

Either way the same decision has to be made for the Pi 5 profile, and it must be made
**before** the overlay can be validated on hardware.

---

## 9. Concrete change list (ordered)

1. `target/linux/bcm27xx/bcm2712/config-6.6` — add `CONFIG_SPI=y`, `CONFIG_SPI_MASTER=y`,
   `CONFIG_SPI_DYNAMIC=y`, `CONFIG_SPI_DESIGNWARE=y`, `CONFIG_SPI_DW_DMA=y`,
   `CONFIG_SPI_DW_MMIO=y`.
2. New patch `target/linux/bcm27xx/patches-6.6/991-0008-dt-overlays-morse-add-pi5-spi-overlay.patch`
   creating `arch/arm/boot/dts/overlays/mm610x-spi-pi5-overlay.dts` (text in §3.2).
3. Edit `991-dt-overlays-build-morse-overlays.patch` to add `mm610x-spi-pi5.dtbo` to
   `dtbo-$(CONFIG_ARCH_BCM2835)`.
4. New patch adding `MM_RESET`/`MM_WAKE`/`MM_BUSY` to `gpio-line-names` in
   `arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts` (`&rp1_gpio` block).
5. Keep `991-0007-spi-support-control-cs-pin-on-init.patch` (generic, needed on RP1 too).
6. New `target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm610x-spi-pi5.txt`:
   `dtparam=spi=on` + `dtoverlay=mm610x-spi-pi5`.
7. `target/linux/bcm27xx/image/Makefile` — add `Device/morse_pi5_base` (from `Device/rpi-5`,
   `boot-common | boot-ekh01 | sdcard-img | gzip | append-metadata`, no `boot-2711`) and
   `Device/bcm2712_mm6108-spi` with `DISTROCONFIG_EXTRA := mm610x-spi-pi5` and
   `SUPPORTED_DEVICES += bcm2712,mm6108-spi`.
8. Review `boards/ekh01/distroconfig.txt` for Pi 5 (`[pi5]` section; `uart5`,
   `miniuart-bt`, `ramoops` variants).
9. New `boards/ekh-bcm2712/target_diffconfig` (+ symlinked extras) modelled on
   `boards/ekh-bcm2711/`, `CONFIG_TARGET_bcm27xx_bcm2712=y`.
10. Resolve the SPI-driver question in §8 and mirror the answer into the Pi 5 board config.
11. Extend the `bcm2710-morse-fix` guard in `om-pkgs/boards/bsp-bcm271x` to cover
    `bcm2712,*`, or rely on step 4 shipping `MM_RESET`.
12. Verify `bcf_fgh100mhaamd.bin` lands in `/lib/firmware/morse/`; if not, ship it from a
    Pi 5 BSP package (pattern: `bsp-bcm271x` shipping `bcf_mf04151.bin`).

Nothing in `netifd-morse`, `hostapd_s1g`, `morsecli`, `morse-regdb`, `openmanet-morse-stack`
or the US regulatory configuration needs Pi 5 changes.
