# RP1 / BCM2712 SPI Device-Tree Research for MM6108 (Wio-WM6108 on WM1302 HAT)

Research date: 2026-08-27
Target: OpenWrt 24.10, kernel 6.6, `target/linux/bcm27xx/bcm2712`
Reference kernel tree: `raspberrypi/linux`, branch `rpi-6.6.y` (all DTS/driver quotes below are verbatim from that branch unless labelled otherwise)

Status legend used throughout:
- **[VERIFIED]** — quoted directly from raspberrypi/linux `rpi-6.6.y` source, the RPi documentation source repo, or this repository.
- **[FIELD-REPORTED]** — from Morse Micro community forum posts (named authors/dates); credible but not source-verified.
- **[UNVERIFIED]** — could not be confirmed from an authoritative source.

---

## 1. Executive summary — the short answer

On Raspberry Pi 5, `&spi0` **still resolves to the primary 40-pin-header SPI controller**, but that controller is now an RP1 Synopsys DesignWare SSI, not a BCM2835 SPI block. The label indirection is done in the Pi 5 base DTS with a C-preprocessor trick plus label re-assignment. Concretely:

| | Raspberry Pi 4 (BCM2711) | Raspberry Pi 5 (BCM2712 + RP1) |
|---|---|---|
| `&spi0` resolves to | `spi@7e204000` on the SoC | `rp1_spi0` = `/axi/pcie@1000120000/rp1/spi@50000` |
| `compatible` | `brcm,bcm2835-spi` | `snps,dw-apb-ssi` |
| Kernel driver | `spi-bcm2835.c` | `spi-dw-mmio.c` + `spi-dw-core.c` |
| Kconfig | `CONFIG_SPI_BCM2835` | `CONFIG_SPI_DESIGNWARE` + `CONFIG_SPI_DW_MMIO` (+`CONFIG_SPI_DW_DMA`) |
| `&gpio` resolves to | `gpio@7e200000` (`brcm,bcm2835-gpio`) | `rp1_gpio` (`raspberrypi,rp1-gpio`) |
| header GPIO numbering | BCM 0–27 | RP1 bank0 0–27, **same numbers** |
| `&spi0_pins` / `&spi0_cs_pins` labels | exist | **also exist** (aliased onto RP1 groups) |
| `&spidev0` / `&spidev1` labels | exist | **also exist** |
| `brcm,pins` / `brcm,function` / `brcm,pull` | native | **supported via a legacy compatibility path in `pinctrl-rp1.c`** |

**Bottom line: a single overlay written against `&spi0`, `&gpio`, `&spi0_pins`, `&spi0_cs_pins`, `&spidev0`, `&spidev1` compiles and applies unchanged on both Pi 4 and Pi 5.** The existing OpenMANET `mm610x-spi-overlay.dts` is very close to already being dual-platform. See §9 for the concrete recipe and the three real gaps.

---

## 2. Question 1 — the Pi 5 SPI controller: label, node, compatible, driver, Kconfig

### 2.1 How the `spi0` label gets moved onto RP1 [VERIFIED]

`arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts` renames the BCM2712-internal SPI blocks out of the way *before* including `bcm2712.dtsi`:

```
#define i2c0 _i2c0
#define i2c3 _i2c3
#define i2c4 _i2c4
#define i2c5 _i2c5
#define i2c6 _i2c6
#define i2s _i2s
#define pwm0 _pwm0
#define pwm1 _pwm1
#define spi0 _spi0
#define spi3 _spi3
#define spi4 _spi4
#define spi5 _spi5
#define spi6 _spi6
#define uart0 _uart0
#define uart2 _uart2
#define uart5 _uart5
```

…and then `#undef`s them after the include:

```
#undef i2c0
...
#undef spi0
#undef spi3
#undef spi4
#undef spi5
#undef spi6
#undef uart0
#undef uart2
#undef uart3
#undef uart4
#undef uart5
```

The old BCM2712 SPI0 is given the new name `spi10`:

```
spi10: &_spi0 { status = "okay"; };
```

and the header-facing `gpio` label is re-pointed at the RP1 GPIO block:

```
gpio: &rp1_gpio {
	status = "okay";
};
```

`arch/arm64/boot/dts/broadcom/bcm2712-rpi.dtsi` then attaches the familiar labels to the RP1 peripherals:

```
i2c0: &rp1_i2c0 { };
i2c1: &rp1_i2c1 { };
i2c2: &rp1_i2c2 { };
i2c3: &rp1_i2c3 { };
i2c4: &rp1_i2c4 { };
i2c5: &rp1_i2c5 { };
i2c6: &rp1_i2c6 { };
spi0: &rp1_spi0 { };
spi1: &rp1_spi1 { };
spi2: &rp1_spi2 { };
spi3: &rp1_spi3 { };
spi4: &rp1_spi4 { };
spi5: &rp1_spi5 { };
```

…defines the pin-group aliases used by overlays:

```
spi0_pins: &rp1_spi0_gpio9 {};
spi0_cs_pins: &rp1_spi0_cs_gpio7 {};
spi2_pins: &rp1_spi2_gpio1 {};
spi3_pins: &rp1_spi3_gpio5 {};
spi4_pins: &rp1_spi4_gpio9 {};
spi5_pins: &rp1_spi5_gpio13 {};
```

…and configures `&spi0` exactly the way Pi 4 does, including the two `spidev` children whose labels overlays target:

```
&spi0 {
	pinctrl-names = "default";
	pinctrl-0 = <&spi0_pins &spi0_cs_pins>;
	cs-gpios = <&gpio 8 1>, <&gpio 7 1>;
	spidev0: spidev@0 {
		compatible = "spidev";
		reg = <0>;	/* CE0 */
		#address-cells = <1>;
		#size-cells = <0>;
		spi-max-frequency = <125000000>;
	};
	spidev1: spidev@1 {
		compatible = "spidev";
		reg = <1>;	/* CE1 */
		#address-cells = <1>;
		#size-cells = <0>;
		spi-max-frequency = <125000000>;
	};
};
```

The aliases block (also `bcm2712-rpi.dtsi`) confirms the numbering exposed to userspace:

```
aliases: aliases {
	...
	gpio0 = &gpio;
	gpio1 = &gio;
	gpio2 = &gio_aon;
	gpio3 = &pinctrl;
	gpio4 = &pinctrl_aon;
	gpiochip0 = &gpio;
	gpiochip10 = &gio;
	...
	spi0 = &spi0;
	spi1 = &spi1;
	spi10 = &spi10;
	spi2 = &spi2;
	spi3 = &spi3;
	spi4 = &spi4;
	spi5 = &spi5;
	...
};
```

> **Trap:** `spi10` is the *BCM2712 on-die* SPI used for the boot/EEPROM path on GPIO 1–4 with `cs-gpios = <&gio 1 1>`. It is **not** the 40-pin header SPI. A Morse forum contributor lost time on exactly this: *"Target `&spi0` (RP1 SPI) NOT `&spi10` (BCM2712 boot SPI — wrong controller entirely)"* [FIELD-REPORTED — boltythedoge, 2026-04-26].

### 2.2 The RP1 SPI0 node itself [VERIFIED]

`arch/arm64/boot/dts/broadcom/rp1.dtsi`:

```
rp1_spi0: spi@50000 {
	reg = <0xc0 0x40050000  0x0 0x130>;
	compatible = "snps,dw-apb-ssi";
	interrupts = <RP1_INT_SPI0 IRQ_TYPE_LEVEL_HIGH>;
	clocks = <&rp1_clocks RP1_CLK_SYS>;
	clock-names = "ssi_clk";
	#address-cells = <1>;
	#size-cells = <0>;
	num-cs = <2>;
	dmas = <&rp1_dma RP1_DMA_SPI0_TX>,
	       <&rp1_dma RP1_DMA_SPI0_RX>;
	dma-names = "tx", "rx";
	status = "disabled";
};
```

`rp1_spi1` … `rp1_spi8` are structurally identical (same `compatible`, different base address / IRQ / DMA channels).

The DMA engine backing it:

```
rp1_dma: dma@188000 {
	reg = <0xc0 0x40188000  0x0 0x1000>;
	compatible = "snps,axi-dma-1.01a";
	interrupts = <RP1_INT_DMA IRQ_TYPE_LEVEL_HIGH>;
	clocks = <&rp1_clocks RP1_CLK_DMA &rp1_clocks RP1_CLK_SYS>;
	clock-names = "core-clk", "cfgr-clk";
	#dma-cells = <1>;
	dma-channels = <8>;
	snps,dma-masters = <1>;
	snps,dma-targets = <64>;
	...
};
```

### 2.3 Which driver binds [VERIFIED]

`drivers/spi/spi-dw-mmio.c`:

```
static const struct of_device_id dw_spi_mmio_of_match[] = {
	{ .compatible = "snps,dw-apb-ssi", .data = dw_spi_pssi_init},
```

So the binding chain is `snps,dw-apb-ssi` → `spi-dw-mmio.ko` → `spi-dw.ko` (core). There is **no** `raspberrypi,rp1-spi` compatible and no RP1-specific SPI driver.

### 2.4 Required Kconfig [VERIFIED]

From `drivers/spi/Kconfig`:

```
config SPI_DESIGNWARE
	tristate "DesignWare SPI controller core support"
	imply SPI_MEM

if SPI_DESIGNWARE

config SPI_DW_DMA
	bool "DMA support for DW SPI controller"

config SPI_DW_MMIO
	tristate "Memory-mapped io interface driver for DW SPI core"
	depends on HAS_IOMEM
```

Required for Pi 5 SPI:
- `CONFIG_SPI_DESIGNWARE=y`
- `CONFIG_SPI_DW_MMIO=y`
- `CONFIG_SPI_DW_DMA=y` (optional but wanted for MM6108 CMD53 block traffic)
- `CONFIG_DW_AXI_DMAC=y` (for `snps,axi-dma-1.01a`, needed by `SPI_DW_DMA` to actually get channels)
- `CONFIG_PINCTRL_RP1=y`, `CONFIG_MFD_RP1=y`, `CONFIG_COMMON_CLK_RP1=y` (already present, see §8)

**GAP FOUND IN THIS REPOSITORY [VERIFIED]:** `target/linux/bcm27xx/bcm2712/config-6.6` sets `CONFIG_MFD_RP1=y`, `CONFIG_PINCTRL_RP1=y`, `CONFIG_COMMON_CLK_RP1=y`, `CONFIG_PWM_RP1=y` — but contains **no** `CONFIG_SPI_DESIGNWARE`, `CONFIG_SPI_DW_MMIO`, `CONFIG_SPI_DW_DMA`, or `CONFIG_DW_AXI_DMAC`. `target/linux/generic/config-6.6` has them explicitly disabled:

```
target/linux/generic/config-6.6:1794:# CONFIG_DW_AXI_DMAC is not set
target/linux/generic/config-6.6:6225:# CONFIG_SPI_DESIGNWARE is not set
target/linux/generic/config-6.6:6228:# CONFIG_SPI_DW_DMA is not set
target/linux/generic/config-6.6:6229:# CONFIG_SPI_DW_MMIO is not set
```

They exist only as loadable kmods (`package/kernel/linux/modules/spi.mk`: `kmod-spi-dw`, `kmod-spi-dw-mmio`). For the Morse SPI driver to probe at boot the controller must be present early — build them **in** (`=y` in `target/linux/bcm27xx/bcm2712/config-6.6`), matching how `bcm2711/config-6.6` sets `CONFIG_SPI_BCM2835=y`.

---

## 3. Question 2 — does a Pi 4 `&spi0` overlay work unchanged on Pi 5?

### 3.1 Short answer: yes, for the node-targeting parts; and yes for the pinctrl parts too, because of a compatibility shim.

Evidence 1 — upstream ships **no** `spi0-1cs-pi5` / `spi0-2cs-pi5`. `arch/arm/boot/dts/overlays/overlay_map.dts` (the file the RPi firmware uses to substitute per-SoC overlay variants) has entries for spi2/spi3/spi5 but **nothing for spi0**:

```
	spi0-cs {
		renamed = "spi0-2cs";
	};

	spi0-hw-cs {
		deprecated = "no longer necessary";
	};

	spi2-1cs {
		bcm2835;
		bcm2711;
		bcm2712 = "spi2-1cs-pi5";
	};

	spi2-1cs-pi5 {
		bcm2712;
	};
	...
	spi3-1cs {
		bcm2711;
		bcm2712 = "spi3-1cs-pi5";
	};
	...
	spi5-1cs {
		bcm2711;
		bcm2712 = "spi5-1cs-pi5";
	};
```

The reason spi2/3/4/5 need `-pi5` variants is that those controllers land on **different header pins** on RP1 (e.g. README: *"spi2-1cs … Enables spi2 on GPIOs 40-42 … spi2-2cs-pi5 is substituted on a Pi 5"* vs *"spi2-1cs-pi5 … Enables spi2 on GPIOs 1-3"*). SPI0 is on GPIO 7–11 on both, so no variant is needed.

And `spi0-1cs-overlay.dts` — a Pi-4-era overlay declaring `compatible = "brcm,bcm2835"` — is shipped unchanged and used on Pi 5:

```
/dts-v1/;
/plugin/;


/ {
	compatible = "brcm,bcm2835";

	fragment@0 {
		target = <&spi0_cs_pins>;
		frag0: __overlay__ {
			brcm,pins = <8>;
		};
	};

	fragment@1 {
		target = <&spi0>;
		frag1: __overlay__ {
			cs-gpios = <&gpio 8 1>;
			status = "okay";
		};
	};

	fragment@2 {
		target = <&spidev1>;
		__overlay__ {
			status = "disabled";
		};
	};

	fragment@3 {
		target = <&spi0_pins>;
		__dormant__ {
			brcm,pins = <10 11>;
		};
	};

	__overrides__ {
		cs0_pin  = <&frag0>,"brcm,pins:0",
			   <&frag1>,"cs-gpios:4";
		no_miso = <0>,"=3";
	};
};
```

Evidence 2 — **`pinctrl-rp1.c` explicitly accepts the legacy BCM2835 pin bindings.** This is the single most important compatibility fact and it is not documented in the overlays README. From `drivers/pinctrl/pinctrl-rp1.c`:

```
static int rp1_pctl_dt_node_to_map(struct pinctrl_dev *pctldev,
				   struct device_node *np,
				   struct pinctrl_map **map,
				   unsigned int *num_maps)
{
	...
	/* Check for legacy pin declaration */
	pins = of_find_property(np, "brcm,pins", NULL);

	if (!pins) /* Assume generic bindings in this node */
		return pinconf_generic_dt_node_to_map_all(pctldev, np, map, num_maps);

	funcs = of_find_property(np, "brcm,function", NULL);
	if (!funcs)
		of_property_read_string(np, "function", &function);

	pulls = of_find_property(np, "brcm,pull", NULL);
	if (!pulls)
		pinconf_generic_parse_dt_config(np, pctldev, &configs, &num_configs);
	...
```

The `brcm,function` numbers are translated through a per-pin table whose slot order exactly reproduces the BCM2835 FSEL encoding (0=IN, 1=OUT, 2=ALT5, 3=ALT4, 4=ALT0, 5=ALT1, 6=ALT2, 7=ALT3):

```
#define LEGACY_MAP(n, f0, f1, f2, f3, f4, f5) \
	[n] = { \
		func_gpio, \
		func_gpio, \
		func_##f5, \
		func_##f4, \
		func_##f0, \
		func_##f1, \
		func_##f2, \
		func_##f3, \
	}
```

```
static const u8 legacy_fsel_map[][8] = {
	LEGACY_MAP(0, i2c0, _, dpi, spi2, uart1, _),
	LEGACY_MAP(1, i2c0, _, dpi, spi2, uart1, _),
	LEGACY_MAP(2, i2c1, _, dpi, spi2, uart1, _),
	LEGACY_MAP(3, i2c1, _, dpi, spi2, uart1, _),
	LEGACY_MAP(4, gpclk0, _, dpi, spi3, uart2, i2c2),
	LEGACY_MAP(5, gpclk1, _, dpi, spi3, uart2, i2c2),
	LEGACY_MAP(6, gpclk2, _, dpi, spi3, uart2, i2c3),
	LEGACY_MAP(7, spi0, _, dpi, spi3, uart2, i2c3),
	LEGACY_MAP(8, spi0, _, dpi, _, uart3, i2c0),
	LEGACY_MAP(9, spi0, _, dpi, _, uart3, i2c0),
	LEGACY_MAP(10, spi0, _, dpi, _, uart3, i2c1),
	LEGACY_MAP(11, spi0, _, dpi, _, uart3, i2c1),
	...
```

So `brcm,pins = <9 10 11>; brcm,function = <4>;` (ALT0) on Pi 5 maps GPIO 9/10/11 to `func_spi0` — the correct RP1 function. And `brcm,pins = <8>; brcm,function = <1>;` (OUT) maps to `func_gpio`. Both correct.

`brcm,pull` values also match BCM2835 semantics:

```
#define RP1_PUD_OFF			0
#define RP1_PUD_DOWN			1
#define RP1_PUD_UP			2
```

**Conclusion:** the *pinctrl* half of the existing OpenMANET Pi 4 overlay is portable to Pi 5 as-is. It is however **stylistically wrong** for Pi 5 — it re-creates nodes named `spi0_pins`/`spi0_cs_pins` under `&gpio` rather than reusing the base-DTB groups, and it does not clear RP1's default bias on GPIO 9/10/11 (see §6.2, a documented real-hardware problem).

### 3.2 What actually breaks

1. **Nothing at the label/`compatible` level.** The root `compatible` string of an overlay is informational for the RPi loader; `overlay_map.dts` is the mechanism that gates by SoC. Morse Micro staff confirm: asked whether `"brcm,bcm2712"` must be added to the compatible array, `ajudge` replied *"I would, but it should work without it."* [FIELD-REPORTED, 2025-12-23]. Adding `"brcm,bcm2712"` is still recommended for clarity.
2. **`__overrides__` that poke `brcm,pins` still work** (the legacy path reads them), but overrides that poke RP1 `pins = "gpioN"` strings do not exist on Pi 4 — so prefer `brcm,pins`-style overrides if you need dual-platform parameterisation, or avoid parameterising pins at all.
3. **`spi10` vs `spi0` confusion** — the only genuinely Pi-5-specific hazard (§2.1).
4. **Duplicate unit-address dtc warning** if you declare both `mm6108@0` and `spidev@0` inside the same `&spi0` fragment. This is what upstream avoids by targeting the pre-existing `&spidev0` / `&spidev1` labels instead. A forum user hit exactly this: *"I receive a warning (unique_unit_address) / duplicate unit-address"* [FIELD-REPORTED — WiHaLowThereFi, 2026-04-16].

### 3.3 Established dual-platform patterns (in order of preference)

| Pattern | When to use | Notes |
|---|---|---|
| **One overlay, `&spi0` + `&gpio` + `brcm,pins`** | Best for OpenMANET | Works on both because of the `pinctrl-rp1.c` legacy path. Zero build-system change. |
| **Two overlays + `overlay_map.dts` entry** | If pin *numbers* must differ | Upstream's own mechanism: `foo { bcm2711; bcm2712 = "foo-pi5"; }` then `foo-pi5 { bcm2712; }`. Firmware silently substitutes at `dtoverlay=foo`. Requires patching `overlay_map.dts`. |
| **Two overlays + `[pi4]`/`[pi5]` in config.txt** | If you also need other per-model settings | See §4. Most explicit, easiest to reason about in an OpenWrt image. |
| **`__overrides__` on one overlay** | Fine-grained tuning (speed, CS pin) | Already how upstream parameterises `spi0-1cs`. |

---

## 4. Question 3 — config.txt conditional filters, exact syntax

Source: `raspberrypi/documentation`, `documentation/asciidoc/computers/config_txt/conditional.adoc` (master) [VERIFIED].

### 4.1 Model filters

| Filter | Applicable models |
|---|---|
| `[pi1]` | 1A, 1B, 1A+, 1B+, Compute Module 1 |
| `[pi2]` | 2B (BCM2836- or BCM2837-based) |
| `[pi3]` | 3B, 3B+, 3A+, Compute Module 3, Compute Module 3+ |
| `[pi3+]` | 3A+, 3B+ (also sees `[pi3]` contents) |
| `[pi4]` | 4B, 400, Compute Module 4, Compute Module 4S |
| `[pi5]` | 5, 500, 500+, Compute Module 5 |
| `[pi400]` | 400 (also sees `[pi4]` contents) |
| `[pi500]` | 500/500+ (also sees `[pi5]` contents) |
| `[cm0]` | Compute Module 0 (also sees `[pi02]` contents) |
| `[cm1]` | Compute Module 1 (also sees `[pi1]` contents) |
| `[cm3]` | Compute Module 3 (also sees `[pi3]` contents) |
| `[cm3+]` | Compute Module 3+ (also sees `[pi3+]` contents) |
| `[cm4]` | Compute Module 4 (also sees `[pi4]` contents) |
| `[cm4s]` | Compute Module 4S (also sees `[pi4]` contents) |
| `[cm5]` | Compute Module 5 (also sees `[pi5]` contents) |
| `[pi0]` | Zero, Zero W, Zero 2 W |
| `[pi0w]` | Zero W (also sees `[pi0]` contents) |
| `[pi02]` | Zero 2 W (also sees `[pi0w]` and `[pi0]` contents) |
| `[board-type=Type]` | Filter by revision-code `Type` number, e.g. `[board-type=0x14]` matches CM4 |

Note quoted verbatim from the docs:

> Some models of Raspberry Pi, including Zero, Compute Module, and Keyboard models, read settings from multiple filters. To apply a setting to only one model:
> * apply the setting to the base model (for example, `[pi4]`), then revert the setting for all models that read the base model's filters (for example, `[pi400]`, `[cm4]`, `[cm4s]`)
> * use the `board-type` filter with a revision code to target a single model (for example, `[board-type=0x11]`)

**`[pi5]` therefore also matches CM5** — relevant if we ever ship a CM5 carrier; `[cm5]` can then revert.

### 4.2 Other filter families

- `[all]` — resets **all** previously set filters. *"It is usually a good idea to add an `[all]` filter at the end of groups of filtered settings to avoid unintentionally combining filters."*
- `[none]` — blocks everything following, until the next filter.
- `[tryboot]` — true when the tryboot reboot flag was set (intended for `autoboot.txt`).
- `[EDID=DEL-DELL_U2422H]` — monitor EDID name. **"NOTE: This setting is not available on Raspberry Pi 5."**
- `[0x12345678]` — serial-number filter (last 8 hex digits of `/proc/cpuinfo` Serial).
- `[gpio4=1]` / `[gpio2=0]` — GPIO state filter.
- Expression filters over boot variables `boot_arg1`, `cust_otpN`, `bootvar0`, `boot_count`, `boot_partition`, `partition`:
```
[ARG=VALUE]      # selected if (ARG == VALUE)
[ARG&MASK]       # selected if ((ARG & VALUE) != 0)
[ARG&MASK=VALUE] # selected if ((ARG & MASK) == VALUE)
[ARG<VALUE]      # selected if (ARG < VALUE)
[ARG>VALUE]      # selected if (ARG > VALUE)
```

### 4.3 Combination rules [VERIFIED]

> Filters of the same type replace each other, so `[pi2]` overrides `[pi1]`, because it is not possible for both to be true at once.
> Filters of different types can be combined by listing them one after the other […]
> Use the `[all]` filter to reset all previous filters and avoid unintentionally combining different filter types.

### 4.4 Applicability to OpenMANET

This repository currently ships per-board `distroconfig` fragments, e.g. `target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm610x-spi.txt`:

```
dtparam=spi=on
dtoverlay=mm610x-spi
```

Two viable strategies:

**(a) Single overlay, no conditionals** (recommended if §9's dual-platform overlay is adopted) — the fragment stays exactly as above and works on both.

**(b) Two overlays selected by filter** — if Pi 4 and Pi 5 ever need genuinely different fragments:

```
dtparam=spi=on
[pi4]
dtoverlay=mm610x-spi
[pi5]
dtoverlay=mm610x-spi-pi5
[all]
```

Note `[pi5]` also catches CM5; add `[cm5]` after it to revert if that matters. Also note the RPi firmware's own `overlay_map.dts` substitution (option (b'), see §3.3) is invisible in config.txt and arguably cleaner, but requires an extra kernel patch in `target/linux/bcm27xx/patches-6.6/`.

---

## 5. Question 4 — GPIO on Pi 5 for overlays

### 5.1 `&gpio` [VERIFIED]

`&gpio` is still the correct label for 40-pin header GPIOs. `bcm2712-rpi-5-b.dts` line 236:

```
gpio: &rp1_gpio {
	status = "okay";
};
```

The node itself (`rp1.dtsi`):

```
rp1_gpio: gpio@d0000 {
	reg = <0xc0 0x400d0000  0x0 0xc000>,
	      <0xc0 0x400e0000  0x0 0xc000>,
	      <0xc0 0x400f0000  0x0 0xc000>;
	compatible = "raspberrypi,rp1-gpio";
	interrupts = <RP1_INT_IO_BANK0 IRQ_TYPE_LEVEL_HIGH>,
		     <RP1_INT_IO_BANK1 IRQ_TYPE_LEVEL_HIGH>,
	             <RP1_INT_IO_BANK2 IRQ_TYPE_LEVEL_HIGH>;
	gpio-controller;
	#gpio-cells = <2>;
	interrupt-controller;
	#interrupt-cells = <2>;
	gpio-ranges = <&rp1_gpio 0 0 54>;
	...
```

Key consequences:
- `#gpio-cells = <2>` — **identical** to BCM2835. `<&gpio 17 GPIO_ACTIVE_HIGH>` is portable verbatim.
- `interrupt-controller` + `#interrupt-cells = <2>` — **`interrupt-parent = <&gpio>; interrupts = <5 IRQ_TYPE_LEVEL_LOW>;` works unchanged on Pi 5.**
- Header GPIO numbers are unchanged. `bcm2712-rpi-5-b.dts` names bank-0 lines `"ID_SDA","ID_SCL","GPIO2","GPIO3",…` at indices 0,1,2,3,… so `&gpio 17` is header GPIO17 on both platforms.
- Bank 0 = 0–27 (header). Banks 1 and 2 (28–53) are internal Pi 5 signals (e.g. `phy-reset-gpios = <&rp1_gpio 32 …>`, camera regulators at 34/46, PCIe at 44).

### 5.2 gpiochip numbering (userspace, not DT)

Per the aliases block, `gpiochip0 = &gpio` (RP1) and `gpiochip10 = &gio` on Pi 5. So on rpi-6.6.y Pi 5, `/dev/gpiochip0` is the RP1 header controller. On Pi 4 `/dev/gpiochip0` is the BCM2835 controller. Scripts that hard-code a gpiochip index are the thing that breaks, not the device tree. Also note the five `raspberrypi,gpiomem` chardevs on Pi 5 (`gpiomem0`..`gpiomem4`) versus one on Pi 4 — `gpiomem0` is the RP1 one.

### 5.3 Correct interrupt-driven-SPI fragment form for both platforms

Upstream's canonical example is `arch/arm/boot/dts/overlays/mcp251xfd-overlay.dts` — a Pi-4-era overlay with no `-pi5` variant and no `overlay_map.dts` entry, i.e. it is expected to work on Pi 5 through the legacy pinctrl path:

```
	fragment@8 {
		target = <&gpio>;
		__overlay__ {
			mcp251xfd_pins: mcp251xfd_pins {
				brcm,pins = <25>;
				brcm,function = <BCM2835_FSEL_GPIO_IN>;
			};
		};
	};
	...
	mcp251xfd_frag: fragment@10 {
		target = <&spi0>;
		__overlay__ {
			status = "okay";
			#address-cells = <1>;
			#size-cells = <0>;

			mcp251xfd: mcp251xfd@0 {
				compatible = "microchip,mcp251xfd";
				reg = <0>;
				pinctrl-names = "default";
				pinctrl-0 = <&mcp251xfd_pins>;
				spi-max-frequency = <20000000>;
				interrupt-parent = <&gpio>;
				interrupts = <25 IRQ_TYPE_LEVEL_LOW>;
				clocks = <&clk_mcp251xfd_osc>;
			};
		};
	};
```

**Note:** the Morse `morse_spi` driver does **not** use `interrupt-parent`/`interrupts`. It takes a GPIO descriptor via `spi-irq-gpios` and converts it to an IRQ itself (evidenced by every published MM6108 overlay, Morse Micro's own included). Both mechanisms are equally portable across Pi 4/Pi 5 because `rp1_gpio` is an interrupt-controller with the same cell count.

---

## 6. Question 5 — pinctrl for SPI0 on Pi 5

### 6.1 The RP1 pin groups [VERIFIED]

`rp1.dtsi`:

```
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

Aliased in `bcm2712-rpi.dtsi` as `spi0_pins` and `spi0_cs_pins`, so **`pinctrl-0 = <&spi0_pins &spi0_cs_pins>;` is valid on both Pi 4 and Pi 5.**

Generic-binding syntax on RP1 is `function = "<name>"; pins = "gpioN", …;` plus standard `pinconf` properties (`bias-disable`, `bias-pull-up`, `bias-pull-down`, `input`, `output-high`, `output-low`, `drive-strength`, `slew-rate`).

### 6.2 Real Pi 5 SPI overlay from the kernel tree [VERIFIED]

`arch/arm/boot/dts/overlays/spi2-1cs-pi5-overlay.dts` — the shape upstream uses for a Pi-5-only SPI overlay:

```
/dts-v1/;
/plugin/;


/ {
	compatible = "brcm,bcm2712";

	fragment@0 {
		target = <&spi2>;
		frag1: __overlay__ {
			/* needed to avoid dtc warning */
			#address-cells = <1>;
			#size-cells = <0>;

			cs-gpios = <&gpio 0 1>;
			status = "okay";

			spidev2_0: spidev@0 {
				compatible = "spidev";
				reg = <0>;      /* CE0 */
				#address-cells = <1>;
				#size-cells = <0>;
				spi-max-frequency = <125000000>;
				status = "okay";
			};
		};
	};

	__overrides__ {
		cs0_pin  = <&frag1>,"cs-gpios:4";
		cs0_spidev = <&spidev2_0>,"status";
	};
};
```

Observe: no explicit `pinctrl-0` — the base DTB's `&spi2` already carries `pinctrl-0 = <&spi2_pins …>`. The same is true of `&spi0`, so an MM6108 overlay only needs to restate `pinctrl-0` when it wants to **add** the Morse GPIO groups to the list.

### 6.3 Morse Micro's own Pi 5 pinctrl guidance [FIELD-REPORTED — ajudge (Morse Micro staff), Build Thread: HaLow for Raspberry Pi OS, 2025]

> On the RPi5 we noticed `rp1_spi0_gpio9`, a node which sets GPIO9, 10, 11 to the correct "alternate function" for SPI has pull downs enabled by default. This conflicts with the pull ups on most carrier boards. We disable this internal bias so high and low states can be correctly defined.

(Their wording says "pull downs"; the shipped `rp1_spi0_gpio9` node actually declares `bias-disable`. Their `fragment@3` re-asserting `bias-disable` is harmless either way, and may be defending against a different vintage of the DTS. **[UNVERIFIED discrepancy]**)

> The second fragment overrides the default SPI CS definition, `rp1_spi0_cs0_gpio7`, to point to GPIO 8 instead.

This matters: `rp1_spi0_cs_gpio7` by default sets **both** GPIO7 and GPIO8 to `function = "spi0"` (hardware CS). Because the base DTB uses `cs-gpios` (software CS), Morse override it to `function = "gpio"; pins = "gpio8";` so GPIO8 is a plain GPIO and GPIO7 is released.

---

## 7. Question 6 — SPI clock limits on RP1 vs BCM2835

### 7.1 Hard numbers [VERIFIED]

- RP1 SSI reference clock is `RP1_CLK_SYS`. `drivers/clk/clk-rp1.c` gives `[RP1_CLK_SYS] … .max_freq = 200 * MHz`.
- `drivers/spi/spi-dw-core.c` computes the divider as:
  ```
  clk_div = min(DIV_ROUND_UP(dws->max_freq, cfg->freq) + 1, 0xfffe) & 0xfffe;
  speed_hz = dws->max_freq / clk_div;
  ```
  i.e. **only even divisors ≥ 2**. With a 200 MHz reference:
  | requested | actual SCLK |
  |---|---|
  | ≥100 MHz | 100 MHz (div 2) |
  | 50 MHz | 50 MHz exactly (div 4) |
  | 33 MHz | 33.3 MHz (div 6) |
  | 25 MHz | 25 MHz exactly (div 8) |
  | 20 MHz | 20 MHz exactly (div 10) |
  | 8 MHz | 8 MHz exactly (div 25→26 ⇒ 7.69 MHz) — *not* exact |
- `host->max_speed_hz = dws->max_freq;` → the controller advertises 200 MHz; the base DTB's `spidev` nodes ask for `spi-max-frequency = <125000000>`, which is simply clamped by the divider math to 100 MHz.
- **Practical ceiling: 100 MHz. The MM6108's 25–50 MHz range is comfortably inside it and lands on exact divisors.**

For comparison, BCM2835/2711 `spi-bcm2835` derives from a 250 MHz core clock with even divisors, giving 125 MHz / 62.5 / 41.7 / 31.25 / 25 …, so **50 MHz is *not* exactly achievable on Pi 4** (you get 41.67 MHz) whereas it *is* on Pi 5. Worth knowing when comparing timing between the two boards. **[VERIFIED from divider math; not from an RPi erratum document]**

### 7.2 RP1 SSI IP identity

RP1 contains **nine DW_apb_ssi (v4.02a) SSI controllers, six of which reach GPIO bank 0** [FIELD-REPORTED via the RP1 Peripherals datasheet summary; the datasheet PDF itself could not be text-extracted in this session]. FIFO depth, and any silicon errata for the SSI blocks: **[UNVERIFIED]**.

### 7.3 Field reports on MM6108 SPI clock on RP1 [FIELD-REPORTED]

| Source | Finding |
|---|---|
| boltythedoge, 2026-04-26 | *"spi_clock_speed: 1MHz, 20MHz, 50MHz (50MHz causes harder crashes, 20MHz slightly better)"*; Pi 5 throughput ~800 kbps TCP vs Pi 4B+ working normally; `cmd53_write … (ret:-71)`, `morse_spi_find_token failed`, `HW restart failed` under sustained load. Also: *"Do NOT use `spi_clock_speed=1000000` — use the DTS 50MHz or 20MHz"*. |
| ajudge (Morse Micro), 2026-04-29 | *"A raspberry pi should be able to reach 50MHz spi clock."* Attributed boltythedoge's `-71` to a bus/power issue, not a throughput limit: *"As the WM6108 is a higher power module, you may be more susceptible to brownouts, as the Pi5 itself is quite power hungry."* |
| baudhound, 2026-07-14 | Ran a **three-node BATMAN_V mesh with two Pi 5 + WM6108** at ~31–32 Mbps BATMAN throughput estimate, 0% loss. This is the strongest evidence that Pi 5 + RP1 SPI + WM6108 is not inherently throughput-limited. |
| terem42, 2026-08-14 (Pi 4, HC01P) | *"large CMD53 block writes during firmware download are unreliable at the default SPI clock here; pinning `spi_clock_speed=8000000` makes them succeed ~80% of the time. It's a sharp resonance at 8 MHz, not a gradient."* |

**Recommended starting point for OpenMANET Pi 5: `spi-max-frequency = <25000000>` in DTS (exact divisor, conservative), raise to 50 MHz once the link is stable, and treat `-71` / `find_token failed` as a power/signal-integrity signal before treating it as a clock problem.**

---

## 8. Question 7 — known third-party MM6108-on-Pi-5 overlays

### 8.1 Morse Micro official build thread [FIELD-REPORTED, high credibility — vendor staff]

*Build Thread: HaLow for Raspberry Pi OS*, `ajudge` (Morse Micro), community.morsemicro.com/t/1124. Contains the vendor's own **`wm6108-spi.dts` for Raspberry Pi 5** — our exact hardware (WM6108 on WM1302 HAT). Reproduced verbatim:

```
/dts-v1/;
/plugin/;

/ {
        compatible = "brcm,bcm2835", "brcm,bcm2836", "brcm,bcm2708", "brcm,bcm2709", "brcm,bcm2711";

        fragment@0 {
                target = <&spi0>;
                frag0: __overlay__ {
                        pinctrl-0 = <&rp1_spi0_gpio9 &rp1_spi0_cs_gpio7 &morse_wake &morse_trst &morse_busy &morse_irq &morse_reset>;
                        cs-gpios = <&gpio 8 1>;
                        #address-cells = <1>;
                        #size-cells = <0>;
                        status = "okay";

                        mm6108: mm6108@0 {
                                compatible = "morse,mm610x-spi";
                                reg = <0>;
                                reset-gpios = <&gpio 17 0>;
                                power-gpios = <&gpio 23 0>,
                                              <&gpio 24 0>;
                                spi-irq-gpios = <&gpio 25 0>;
                                spi-max-frequency = <50000000>;
                                status = "okay";
                        };
                        spidev@0 {
                                reg = <0>;
                                status = "disabled";
                        };
                        spidev@1 {
                                reg = <1>;
                                status = "disabled";
                        };

                };
        };

        fragment@1 {
                target = <&rp1_spi0_cs_gpio7>;
                frag1: __overlay__ {
                        function = "gpio";
                        pins = "gpio8";
                        bias-pull-up;
                };
        };

        fragment@2 {
                target = <&gpio>;
                frag2: __overlay__ {
                        morse_wake: morse_wake {
                                function = "gpio";
                                pins = "gpio23";
                                output-high;
                                bias-disable;
                        };

                        morse_busy: morse_busy {
                                function = "gpio";
                                pins = "gpio24";
                                input;
                                bias-pull-down;
                        };

                        morse_irq: morse_irq {
                                function = "gpio";
                                pins = "gpio5";
                                bias-pull-up;
                                input;
                        };

                        morse_reset: morse_reset {
                                function = "gpio";
                                pins = "gpio17";
                                output-high;
                                bias-disable;
                        };
                };
        };

        fragment@3 {
                target = <&rp1_spi0_gpio9>;
                frag3: __overlay__ {
                        bias-disable;
                };
        };
};
```

**Two defects in the vendor's published file — do not copy blindly:**
1. `pinctrl-0` references `&morse_trst`, but `morse_trst` is **not defined anywhere in this file** (it exists only in their MMECH06 variant earlier in the same post). This will fail to compile / leave a dangling fixup.
2. `spi-irq-gpios = <&gpio 25 0>;` contradicts their own pin table for the WM1302/WM6108, which lists **SPI IRQ = GPIO5** (physical pin 29), and contradicts their own `morse_irq` pin group which configures `gpio5`. GPIO25 is a copy-paste leftover from the MMECH06 example. **Use `<&gpio 5 0>`** — which is what this repository's existing Pi 4 overlay already does.

Their WM1302 ↔ WM6108 ↔ RPi pin table (verbatim mapping):

| Signal | RPi header pin | RPi GPIO |
|---|---|---|
| SPI SCLK | 23 | GPIO11 |
| SPI MOSI | 19 | GPIO10 |
| SPI MISO | 21 | GPIO9 |
| SPI CS | 24 | GPIO8 |
| SPI IRQ | 29 | GPIO5 |
| RESETN | 11 | GPIO17 |
| WAKE | 16 | GPIO23 |
| BUSY | 18 | GPIO24 |

**This matches this repository's existing `mm610x-spi-overlay.dts` exactly.** Our Pi 4 GPIO map is already correct for Pi 5; only the pinctrl idiom and the kernel config differ.

### 8.2 Community Pi 5 overlay that reached a working link [FIELD-REPORTED — boltythedoge, 2026-04-26]

```
/dts-v1/;
/plugin/;

/ {
    compatible = "brcm,bcm2835", "brcm,bcm2836", "brcm,bcm2708",
                 "brcm,bcm2709", "brcm,bcm2711", "brcm,bcm2712";

    fragment@0 {
        target = <&spi0>;
        __overlay__ {
            pinctrl-0 = <&rp1_spi0_gpio9 &rp1_spi0_cs_gpio7
                         &morse_wake &morse_busy &morse_irq &morse_reset>;
            cs-gpios = <&gpio 8 1>;
            #address-cells = <1>;
            #size-cells = <0>;
            status = "okay";

            mm6108: mm6108@0 {
                compatible = "morse,mm610x-spi";
                reg = <0>;
                reset-gpios = <&gpio 17 0>;
                power-gpios = <&gpio 23 0>, <&gpio 24 0>;
                spi-irq-gpios = <&gpio 5 0>;
                spi-max-frequency = <50000000>;
                status = "okay";
            };
            spidev@0 { reg = <0>; status = "disabled"; };
            spidev@1 { reg = <1>; status = "disabled"; };
        };
    };

    fragment@1 {
        target = <&rp1_spi0_cs_gpio7>;
        __overlay__ {
            function = "gpio";
            pins = "gpio8";
            bias-pull-up;
        };
    };

    fragment@2 {
        target = <&gpio>;
        __overlay__ {
            morse_wake: morse_wake {
                function = "gpio";
                pins = "gpio23";
                output-high;
                bias-disable;
            };
            morse_busy: morse_busy {
                function = "gpio";
                pins = "gpio24";
                input;
                bias-pull-down;
            };
            morse_irq: morse_irq {
                function = "gpio";
                pins = "gpio5";
                bias-pull-up;
                input;
            };
            morse_reset: morse_reset {
                function = "gpio";
                pins = "gpio17";
                output-high;
                bias-disable;
            };
        };
    };
};
```

This is the vendor file with `morse_trst` removed and the IRQ GPIO corrected to 5 — i.e. it is the **fixed** version. It produced `wlan1` on boot, reliable AP/STA association, and 0% packet loss on ping. Its remaining problem was throughput, which the vendor attributed to power supply and which another user (baudhound) did not reproduce.

### 8.3 Other findings

- `buildwithparallel/openwrt-morse-rpi5`, branch `rpi5-mm-23.05` (GitHub). An independent OpenWrt 23.05 → Pi 5 backport of the Morse SDK. Their `AGENTS.md` states MM8108-USB + BATMAN mesh works, but **"the original goal — MM6108/SPI binding on Pi 5 — remains unresolved… the chip doesn't probe despite enumeration by the controller."** Given §8.2 and §9.3, that failure is most likely the CS-polarity/init-sequence issue, not a device-tree problem. Useful as a cross-check, not as a source of overlay text.
- Morse Micro thread 416 (*"Raspberry Pi 5 - Device tree overlay not loading (Kernel 6.1.y)"*) — overlays not loading at all; resolved as a bootloader/kernel-version mismatch, not a DT syntax issue.
- Morse Micro thread 1144 (*"SPI bringup on Raspberry Pi"*) — vendor confirms *"For SPI, the driver will only start probing if the `morse,mm610x` compatible is found."* and the required driver build flags: `make KERNEL_SRC=… CONFIG_WLAN_VENDOR_MORSE=m CONFIG_MORSE_SPI=y CONFIG_MORSE_USER_ACCESS=y CONFIG_MORSE_VENDOR_COMMAND=y`.
- Thread 1124 also reports **successful BATMAN_V meshing between a Pi 5 + WM6108 node and an OpenMANET node** — direct evidence our end goal is reachable.

---

## 9. The concrete recipe for OpenMANET

### 9.1 What we already have (Pi 4 path) [VERIFIED in this repo]

`target/linux/bcm27xx/patches-6.6/991-0003-dt-overlays-morse-add-spi-overlay-fragment.patch` creates `arch/arm/boot/dts/overlays/mm610x-spi-overlay.dts`:

```
/ {
	compatible = "brcm,bcm2835", "brcm,bcm2836", "brcm,bcm2837",
	             "brcm,bcm2708", "brcm,bcm2709", "brcm,bcm2710", "brcm,bcm2711";

	fragment@0 {
		target = <&spi0>;
		frag0: __overlay__ {
			pinctrl-0 = <&spi0_pins &spi0_cs_pins &morse_wake &morse_busy &morse_irq &morse_reset>;
			cs-gpios = <&gpio 8 1>;
			...
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
			spidev0: spidev@0 { reg = <0>; status = "disabled"; };
			spidev1: spidev@1 { reg = <1>; status = "disabled"; };
		};
	};

	fragment@1 {
		target = <&gpio>;
		__overlay__ {
			spi0_cs_pins: spi0_cs_pins { brcm,pins = <8>;      brcm,function = <1>; brcm,pull = <2>; };
			spi0_pins:    spi0_pins    { brcm,pins = <9 10 11>; brcm,function = <4>; brcm,pull = <2 2 2>; };
			morse_wake:   morse_wake   { brcm,pins = <23>; brcm,function = <0>; brcm,pull = <2>; };
			morse_busy:   morse_busy   { brcm,pins = <24>; brcm,function = <0>; brcm,pull = <1>; };
			morse_irq:    morse_irq    { brcm,pins = <5>;  brcm,function = <0>; brcm,pull = <2>; };
			morse_reset:  morse_reset  { brcm,pins = <17>; brcm,function = <0>; brcm,pull = <2>; };
		};
	};
};
```

`991-dt-overlays-build-morse-overlays.patch` adds `mm610x-spi.dtbo`, `mm810x-spi.dtbo`, `mm_wlan.dtbo`, `raven.dtbo` to `dtbo-$(CONFIG_ARCH_BCM2835)` in `arch/arm/boot/dts/overlays/Makefile`. Note the Kconfig gate: the bcm2712 kernel config must keep `CONFIG_ARCH_BCM2835=y` for these `.dtbo`s to be built at all. **[Verify during the build — if the bcm2712 subtarget uses a different ARCH symbol, the Morse overlays will silently not be produced.]**

### 9.2 Recommended dual-platform overlay

The safest minimal change is to **write a Pi-5-specific `mm610x-spi-pi5-overlay.dts` in the RP1-native idiom** and select it either via `overlay_map.dts` substitution or via `[pi5]` in distroconfig. Rationale: the legacy `brcm,pins` path *does* work on RP1, but the vendor-blessed Pi 5 form additionally (a) re-uses the base-DTB SPI groups rather than shadowing them, (b) explicitly releases GPIO7 from `spi0` function, and (c) clears the SPI-pin bias — all of which the legacy form does not do.

Proposed `mm610x-spi-pi5-overlay.dts` (derived from §8.2, which is the field-corrected vendor file; pin map matches our existing Pi 4 overlay exactly):

```
/dts-v1/;
/plugin/;

/ {
	compatible = "brcm,bcm2712";

	/* SPI0 = RP1 spi@50000. NOT spi10 (BCM2712 on-die boot SPI). */
	fragment@0 {
		target = <&spi0>;
		frag0: __overlay__ {
			pinctrl-names = "default";
			pinctrl-0 = <&spi0_pins &spi0_cs_pins
				     &morse_wake &morse_busy &morse_irq &morse_reset>;
			cs-gpios = <&gpio 8 1>;		/* GPIO_ACTIVE_LOW - must stay 1 */
			#address-cells = <1>;
			#size-cells = <0>;
			status = "okay";

			mm6108: mm6108@0 {
				compatible = "morse,mm610x-spi";
				reg = <0>;			/* CE0 */
				reset-gpios   = <&gpio 17 0>;	/* RESETN, hdr pin 11 */
				power-gpios   = <&gpio 23 0>,	/* WAKE,   hdr pin 16 */
				                <&gpio 24 0>;	/* BUSY,   hdr pin 18 */
				spi-irq-gpios = <&gpio 5 0>;	/* SPI IRQ, hdr pin 29 */
				spi-max-frequency = <25000000>;
				status = "okay";
			};
		};
	};

	/* Release GPIO7 from spi0 function; GPIO8 becomes a plain GPIO for software CS. */
	fragment@1 {
		target = <&spi0_cs_pins>;	/* == &rp1_spi0_cs_gpio7 */
		__overlay__ {
			function = "gpio";
			pins = "gpio8";
			bias-pull-up;
		};
	};

	/* Clear RP1's default bias on SCLK/MOSI/MISO - carrier board provides pulls. */
	fragment@2 {
		target = <&spi0_pins>;		/* == &rp1_spi0_gpio9 */
		__overlay__ {
			bias-disable;
		};
	};

	fragment@3 {
		target = <&gpio>;
		__overlay__ {
			morse_wake: morse_wake {
				function = "gpio";
				pins = "gpio23";
				output-high;
				bias-disable;
			};
			morse_busy: morse_busy {
				function = "gpio";
				pins = "gpio24";
				input;
				bias-pull-down;
			};
			morse_irq: morse_irq {
				function = "gpio";
				pins = "gpio5";
				input;
				bias-pull-up;
			};
			morse_reset: morse_reset {
				function = "gpio";
				pins = "gpio17";
				output-high;
				bias-disable;
			};
		};
	};

	/* Disable the base-DTB spidev nodes by label - avoids the
	 * duplicate-unit-address dtc warning from redeclaring spidev@0. */
	fragment@4 { target = <&spidev0>; __overlay__ { status = "disabled"; }; };
	fragment@5 { target = <&spidev1>; __overlay__ { status = "disabled"; }; };
};
```

Selection, option A — patch `arch/arm/boot/dts/overlays/overlay_map.dts` (invisible to config.txt, matches upstream convention):

```
	mm610x-spi {
		bcm2835;
		bcm2711;
		bcm2712 = "mm610x-spi-pi5";
	};

	mm610x-spi-pi5 {
		bcm2712;
	};
```

Selection, option B — per-image distroconfig (more explicit; a Pi 5 board dir gets its own file anyway):

```
dtparam=spi=on
[pi4]
dtoverlay=mm610x-spi
[pi5]
dtoverlay=mm610x-spi-pi5
[all]
```

Note `fragment@4`/`fragment@5` using `&spidev0`/`&spidev1` also works on Pi 4 — so if a single overlay is preferred later, the only genuinely Pi-5-only fragments are @1 and @2.

### 9.3 Three non-device-tree gaps that will bite on Pi 5

**(a) `SPI_CONTROLLER_ENABLE_CS_GPIOD` is a dead flag on the DesignWare path. [VERIFIED in this repo]**

`target/linux/bcm27xx/patches-6.6/991-0007-spi-support-control-cs-pin-on-init.patch` (Morse Micro, Sagar Bussa) adds:

```
+#define SPI_CONTROLLER_ENABLE_CS_GPIOD BIT(9)
```

and makes `spi_setup()` skip the forced `SPI_CS_HIGH` and `spi_set_cs()` invert polarity **only when a controller sets that flag**. Grepping the whole tree:

```
$ grep -rn "SPI_CONTROLLER_ENABLE_CS_GPIOD" --include=*.patch .
./target/linux/bcm27xx/patches-6.6/991-0007-...patch:27
./target/linux/bcm27xx/patches-6.6/991-0007-...patch:37
./target/linux/bcm27xx/patches-6.6/991-0007-...patch:53
```

**Nothing in this tree ever sets the flag.** If it is set by the out-of-tree `morse_spi` driver (in the Morse feed) on the controller it binds to, it will work on Pi 5 too since the patch is to generic `drivers/spi/spi.c`. **[UNVERIFIED — check the Morse driver package in `feeds/` once feeds are populated.]** If instead it is set by a `spi-bcm2835.c` patch we do not carry, Pi 5 will fail with the classic symptom:

```
morse_spi spi0.0: morse_spi_probe: failed to init SPI with CMD63 (ret:-61 or -71)
morse_spi spi0.0: probe with driver morse_spi failed with error -71
```

A driver-side alternative was published by `terem42` (2026-08-14) [FIELD-REPORTED]: in `morse_spi_initsequence()`, use `SPI_NO_CS` rather than toggling `SPI_CS_HIGH` for the ≥74-clock SD-spec warm-up, which is correct for **any** controller using a GPIO chip-select — including `spi-dw`. Root cause as they describe it:

> `morse_spi_initsequence()` clocks the SD-spec warm-up (≥74 clocks) with CS deasserted by toggling `SPI_CS_HIGH`. That works only when the driver owns CS polarity. On a mainline kernel with a GPIO chip-select, the SPI core sets `SPI_CS_HIGH` itself, so the driver's toggle is a no-op and the 18 training bytes go out with CS asserted. The chip counts them as a transaction and its bit pointer ends up permanently offset — so CMD63 comes back shifted.

This is the most likely explanation for `buildwithparallel`'s "chip doesn't probe despite enumeration" on Pi 5 (§8.3).

**(b) `cs-gpios` polarity flag must be `1`. [FIELD-REPORTED — baudhound, 2026-07-14]**

> decompile the deployed `.dtbo` and read the `cs-gpios` polarity flag:
> `dtc -I dtb -O dts /boot/firmware/overlays/wm6108-spi.dtbo 2>/dev/null | grep cs-gpios`
> must end in `0x01` (ACTIVE_LOW). If it's `0x00` the kernel drives CS high during transactions — the chip is never selected and returns garbage.

**(c) Cold power cycle required for first probe. [FIELD-REPORTED — ajudge, Morse Micro staff]**

> Have you physically power cycled the device (reconnected the power) or just soft booted? Unfortunately most of our deployments use a reset script to toggle the reset line on boot. If that's not run, on warmboots you will see these errors.

Relevant to hardware-validation methodology: a warm reboot is not a valid test of MM6108 bring-up. A Morse driver patch exists that moves the reset assertion into the driver.

### 9.4 Kernel-config delta for `target/linux/bcm27xx/bcm2712/config-6.6`

```
CONFIG_SPI_DESIGNWARE=y
CONFIG_SPI_DW_MMIO=y
CONFIG_SPI_DW_DMA=y
CONFIG_DW_AXI_DMAC=y
```

(Already present and correct: `CONFIG_MFD_RP1=y`, `CONFIG_PINCTRL_RP1=y`, `CONFIG_PINCTRL_BCM2712=y`, `CONFIG_COMMON_CLK_RP1=y`.)

Note `CONFIG_SPI_BCM2835` should **not** be added to bcm2712 — the BCM2712 on-die SPI (`spi10`) uses `brcm,bcm2835-spi` too, but nothing on the header needs it and enabling it only revives the boot-SPI/`spidev10` node.

---

## 10. Open items / could not verify

1. Whether the Morse `morse_spi` driver in this project's feed sets `SPI_CONTROLLER_ENABLE_CS_GPIOD`, or whether an unshipped `spi-bcm2835` patch does. **Blocks a confident answer on whether patch `991-0007` helps on Pi 5.** Check once feeds are populated.
2. Whether `dtbo-$(CONFIG_ARCH_BCM2835)` in the overlays Makefile is actually evaluated for the bcm2712 subtarget build (i.e. is `CONFIG_ARCH_BCM2835=y` in our bcm2712 config). If not, the Morse `.dtbo`s will not be produced for Pi 5 images.
3. RP1 DW_apb_ssi FIFO depth and any SSI errata — the RP1 Peripherals datasheet PDF could not be text-extracted in this session.
4. Morse Micro's claim that `rp1_spi0_gpio9` has "pull downs enabled by default" contradicts the shipped `bias-disable` in `rp1.dtsi` on `rpi-6.6.y`. Their extra `bias-disable` fragment is harmless; the discrepancy is unresolved.
5. Whether OpenMANET's bcm2712 image currently produces a working `config.txt`/`distroconfig.txt` pipeline for a Pi 5 board directory (only `boards/ekh01` exists under `target/linux/bcm27xx/image/boards/`, and `boards/` has no bcm2712 entry). A new board dir will be needed.

---

## 11. Sources

**Authoritative (raspberrypi/linux, branch `rpi-6.6.y`)**
- `arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts`
- `arch/arm64/boot/dts/broadcom/bcm2712-rpi.dtsi`
- `arch/arm64/boot/dts/broadcom/rp1.dtsi`
- `arch/arm/boot/dts/overlays/README`
- `arch/arm/boot/dts/overlays/overlay_map.dts`
- `arch/arm/boot/dts/overlays/spi0-1cs-overlay.dts`, `spi0-2cs-overlay.dts`, `spi2-1cs-pi5-overlay.dts`, `anyspi-overlay.dts`, `mcp251xfd-overlay.dts`
- `drivers/pinctrl/pinctrl-rp1.c`
- `drivers/spi/spi-dw-mmio.c`, `drivers/spi/spi-dw-core.c`, `drivers/spi/Kconfig`
- `drivers/clk/clk-rp1.c`

**Authoritative (raspberrypi/documentation, master)**
- `documentation/asciidoc/computers/config_txt/conditional.adoc`
- https://www.raspberrypi.com/documentation/computers/config_txt.html

**Vendor / community (field-reported)**
- https://community.morsemicro.com/t/build-thread-halow-for-raspberry-pi-os/1124
- https://community.morsemicro.com/t/mm6108-fgh100m-h-wm6108-wm1302-pi-hat-rpi5-over-spi/1104
- https://community.morsemicro.com/t/spi-bringup-on-raspberry-pi/1144
- https://community.morsemicro.com/t/raspberry-pi-5-device-tree-overlay-not-loading-kernel-6-1-y/416
- https://github.com/buildwithparallel/openwrt-morse-rpi5/blob/rpi5-mm-23.05/AGENTS.md
- https://pip.raspberrypi.com/documents/RP-008370-DS-1-rp1-peripherals.pdf (RP1 Peripherals datasheet — binary, not text-extracted)

**This repository**
- `target/linux/bcm27xx/patches-6.6/991-0003-dt-overlays-morse-add-spi-overlay-fragment.patch`
- `target/linux/bcm27xx/patches-6.6/991-0007-spi-support-control-cs-pin-on-init.patch`
- `target/linux/bcm27xx/patches-6.6/950-0821-spi-bcm2835-Support-spi0-0cs-and-SPI_NO_CS-mode.patch`
- `target/linux/bcm27xx/patches-6.6/991-dt-overlays-build-morse-overlays.patch`
- `target/linux/bcm27xx/bcm2712/config-6.6`, `target/linux/bcm27xx/bcm2711/config-6.6`, `target/linux/generic/config-6.6`
- `target/linux/bcm27xx/image/boards/ekh01/distroconfig-mm610x-spi.txt`
- `package/kernel/linux/modules/spi.mk`
