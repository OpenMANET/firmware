# Independent review — staged `bcm2712_mm6108-spi` product profile

Branch `pi5-wm6108-port`, baseline `365b276`. Review of the staged (uncommitted) change set.
Read-only review; no repo file other than this report was touched.

Verdict: **1 BLOCKER (runtime, Pi 5 only), 2 HIGH, 4 MEDIUM.**
**No Pi 3 / Pi 4 regression found.** The highest-risk item flagged in the brief
(the shared `991-dt-overlays-build-morse-overlays.patch` hunk) is **clean — verified by
actually applying it**.

---

## Severity summary

| # | Sev | Item |
|---|-----|------|
| 1 | **BLOCKER** | `CONFIG_SPI_DW_DMA=y` without `CONFIG_DW_AXI_DMAC` → `rp1_spi0` probe-defers forever; MM6108 never enumerates |
| 2 | HIGH | `SPI_CONTROLLER_ENABLE_CS_GPIOD` still set by nobody in-tree; Pi 5 CS init sequencing unresolved |
| 3 | HIGH | `boards/common_extras/spi-rp1_diffconfig` is a **no-op** — all four kmods it selects are forced built-in by the same commit |
| 4 | MEDIUM | `CONFIG_SPI_MEM` left `n` (archs38, the only other `SPI_DESIGNWARE=y` target, sets it `y`) |
| 5 | MEDIUM | `CONFIG_PACKAGE_bsp-bcm271x=y` gating not verified for bcm2712 (same class of bug the author caught for `persistent-vars-storage-bcm2711`) |
| 6 | MEDIUM | DTS pinctrl uses nested-child form, unlike every other RP1 group in the tree (works — but see analysis) |
| 7 | MEDIUM | `/etc/modules.d/*` autoload stubs generated for now-built-in modules → boot-log errors |
| 8 | LOW ×6 | stale hunk `+231`, duplicate `SUPPORTED_DEVICES`, unused `frag0:` label, duplicated `patches/ekh-bcm2712/`, `board_name` not in `02_network`, 25 MHz comment |
| — | OK | Task A (Pi3/Pi4 regressions), Task B (patch well-formedness), most of Task C, Task D config symbols |

---

# 1. BLOCKER — `CONFIG_SPI_DW_DMA=y` with no DMA engine driver for RP1

`target/linux/bcm27xx/bcm2712/config-6.6:592`
```
CONFIG_SPI_DW_DMA=y
```

RP1's SPI0 declares DMA channels in the base device tree
(`target/linux/bcm27xx/patches-6.6/950-1180-arm64-dts-Move-bcm2712-and-rp1-here.patch:8631-8649`):

```
rp1_spi0: spi@50000 {
        compatible = "snps,dw-apb-ssi";
        num-cs = <2>;
        dmas = <&rp1_dma RP1_DMA_SPI0_TX>,
               <&rp1_dma RP1_DMA_SPI0_RX>;
        dma-names = "tx", "rx";
```

and `rp1_dma` (same patch, line 9515) is:

```
rp1_dma: dma@188000 {
        compatible = "snps,axi-dma-1.01a";
```

i.e. it needs `CONFIG_DW_AXI_DMAC` (`drivers/dma/dw-axi-dmac`). **That symbol is not enabled
anywhere for bcm2712:**

```
target/linux/generic/config-6.6:1794:# CONFIG_DW_AXI_DMAC is not set
```
— and `target/linux/bcm27xx/bcm2712/config-6.6` does not override it. There is also **no
OpenWrt kmod package** for it (`grep -rn DW_AXI_DMAC package/kernel/linux/modules/` → nothing).
The only target in the tree that sets it is `archs38`.

Consequence, kernel 6.6 `drivers/spi/spi-dw-mmio.c` / `spi-dw-core.c`:

* compatible `snps,dw-apb-ssi` → `dw_spi_dw_apb_init()` → `dw_spi_dma_setup_generic()` installs
  `dws->dma_ops` because `CONFIG_SPI_DW_DMA=y`;
* `dw_spi_add_host()` calls `dma_ops->dma_init()` → `dw_spi_dma_init_generic()` →
  `dma_request_chan(dev, "rx")`;
* `of_dma_request_slave_channel()` finds the `dmas` phandle but **no registered controller**
  for `rp1_dma`, so it returns `-EPROBE_DEFER`;
* `dw_spi_add_host()` explicitly `goto err_free_irq` on `-EPROBE_DEFER`.

Net effect: **`rp1_spi0` never finishes probing, `spi0.0` never appears, the MM6108 never
enumerates** — and the failure is a silent deferred probe, not an error, so it is easy to
misdiagnose as a wiring/overlay problem on the bench.

This is a *self-inflicted* regression relative to the baseline: before this change the bcm2712
target had no `CONFIG_SPI_*` lines at all, so `kmod-spi-dw` / `kmod-spi-dw-mmio` (both in
`Device/rpi-5`'s `DEVICE_PACKAGES`, `target/linux/bcm27xx/image/Makefile:262-263`) built as
modules with `CONFIG_SPI_DW_DMA` inheriting generic's `is not set` → PIO mode, which works.

The project's own research already called this out and it was dropped in implementation —
`.ai-workflow/rp1-spi-research.md` §9.4 prescribes:

```
CONFIG_SPI_DESIGNWARE=y
CONFIG_SPI_DW_MMIO=y
CONFIG_SPI_DW_DMA=y
CONFIG_DW_AXI_DMAC=y     <-- missing from the staged config
```

**Fix (either is sufficient, first is preferred):**
* add `CONFIG_DW_AXI_DMAC=y` to `bcm2712/config-6.6` (the tree already carries RPi's RP1
  fixes for that driver: `950-1144-dmaengine-dw-axi-dmac-Fixes-for-RP1.patch`,
  `950-1145-fixup-...`, `950-0967-...`, `950-1047-...` — they are currently dead code); **or**
* drop `CONFIG_SPI_DW_DMA` for bring-up (PIO), matching `archs38`
  (`target/linux/archs38/config-6.6:253: # CONFIG_SPI_DW_DMA is not set`).

Given four RP1-specific dw-axi-dmac patches are already applied and the MM6108 moves ~1500-byte
frames, enabling the DMAC is the right answer.

---

# 2. HIGH — `SPI_CONTROLLER_ENABLE_CS_GPIOD` is still set by nothing in this tree

`target/linux/bcm27xx/patches-6.6/991-0007-spi-support-control-cs-pin-on-init.patch:37`
makes `spi_setup()` skip the forced `SPI_CS_HIGH` **only if the controller sets
`SPI_CONTROLLER_ENABLE_CS_GPIOD`**. A whole-tree grep finds the flag only in its own patch:

```
$ grep -rn SPI_CONTROLLER_ENABLE_CS_GPIOD . | grep -v '^./.ai-workflow\|PI5_PORT_STATUS'
target/linux/bcm27xx/patches-6.6/991-0007-...patch:27,37,53
```

If the flag is set by the out-of-tree `morse_spi` driver on whatever controller it binds to
(as `PI5_PORT_STATUS.md:53` asserts, `morse_driver/spi.c:1456`) this is fine on RP1 too, since
991-0007 patches generic `drivers/spi/spi.c`. If instead it depends on a `spi-bcm2835` change
we don't carry, Pi 5 will fail at `morse_spi_initsequence()` with the classic shifted-CMD63
symptom. This change set does nothing to resolve the ambiguity, and it is the single most
likely first-boot failure after the DMA blocker.

**Action:** once feeds are installed, `grep -rn SPI_CONTROLLER_ENABLE_CS_GPIOD feeds/morse/`
before burning a card. Not a code change here, but it should be on the bring-up checklist.

---

# 3. HIGH — `boards/common_extras/spi-rp1_diffconfig` is a no-op

```
boards/common_extras/spi-rp1_diffconfig:8-12
CONFIG_MORSE_SPI=y
CONFIG_PACKAGE_kmod-spi-dw=y
CONFIG_PACKAGE_kmod-spi-dw-mmio=y
CONFIG_PACKAGE_kmod-spi-bitbang=y
CONFIG_PACKAGE_kmod-spi-gpio=y
```

All four kmods are made **built-in** by the very same commit:

| package | `KCONFIG` symbol | now forced in `bcm2712/config-6.6` |
|---|---|---|
| `kmod-spi-dw` | `CONFIG_SPI_DESIGNWARE` (`package/kernel/linux/modules/spi.mk:83`) | `:591 =y` |
| `kmod-spi-dw-mmio` | `CONFIG_SPI_DW_MMIO` (`spi.mk:103`) | `:593 =y` |
| `kmod-spi-bitbang` | `CONFIG_SPI_BITBANG` (`spi.mk:33`) | `:587 =y` |
| `kmod-spi-gpio` | `CONFIG_SPI_GPIO` (`spi.mk:50`) | `:592-ish =y` |

The merge is `scripts/kconfig.pl 'm+' '+' .config.target /dev/null .config.override`
(`include/kernel-defaults.mk:122`). In `m+` mode `config_add()` does `next if $config{$config}
eq "y"` (`scripts/kconfig.pl:73`), so the target config's `=y` **wins over** the package
metadata's `=m`. The `.ko`s are never produced.

**This is not a build failure** — I checked the guard. `include/kernel.mk:246-249` greps
`modules.builtin` first and prints `NOTICE: module '…' is built-in.` before the
`ERROR: module '…' is missing.` branch. So the four packages install as empty stubs and the
build succeeds. Same for `kmod-ramoops` (`boards/common/kmods_diffconfig`, now
`CONFIG_PSTORE_RAM=y`) and the `kmod-usb-serial*` set — the latter already behaves this way on
bcm2711, so it is consistent.

But the diffconfig **reads as if it does something and does not**. Two concrete costs:

* It hides the blocker in #1: the file's own comment reasons about `spi-dw` being the right
  driver, yet selecting `kmod-spi-dw-mmio` cannot rescue a `SPI_DW_DMA` misconfiguration.
* `spi_diffconfig` on bcm2711 → `common_extras/spi_diffconfig` genuinely selects modules
  (`CONFIG_SPI_BCM2835` is not `=y` in `bcm2711/config-6.6`). The symmetry is only apparent.

**Recommendation:** either drop the four `CONFIG_PACKAGE_kmod-spi-*` lines and keep only
`CONFIG_MORSE_SPI=y` (with a comment saying the drivers are built in), or move
`SPI_DESIGNWARE`/`SPI_DW_MMIO` out of `config-6.6` and let the kmods build them as modules.
Do not leave both.

**No cross-board leakage:** `scripts/openmanet_setup.sh:265-283` globs
`./boards/common/*_diffconfig` then `./boards/<BOARD>/*_diffconfig`, and `common_extras`
entries are only pulled in by an explicit `-x <name>` (`:289-292`). `boards/common_extras/` is
**never globbed** — only indexed by name. `usage()` (`:57-58`) does `ls -1 boards/common_extras`,
so `spi-rp1` will now appear in the `-x` listing; that is cosmetic and arguably correct.
`boards/ekh-bcm2712/spi_diffconfig → ../common_extras/spi-rp1_diffconfig` is a symlink, so the
`"is not a symlink; aborting"` check at `:266-273` passes. **No effect on any other board.**

---

# Task A — Pi 4 / Pi 3 regression hunt: **CLEAN**

### `target/linux/bcm27xx/image/Makefile` — no leakage

* `Build/boot-rpi5-morse` (`:84-95`) is defined unconditionally but GNU make `define`s are
  recursively expanded, so the body is only evaluated where referenced. It is referenced only
  from `Device/morse_rpi5_base` (`:402-403`). bcm2710/bcm2711 `IMAGE/*` recipes are unchanged.
  Indentation verified with `cat -A`: every body line starts with a hard tab, matching
  `Build/boot-ekh01` (`:72-82`). **OK.**
* `Device/morse_rpi5_base` (`:388-404`) and `Device/bcm2712_mm6108-spi` (`:406-415`) are only
  expanded via `TARGET_DEVICES += bcm2712_mm6108-spi` inside `ifeq ($(SUBTARGET),bcm2712)`
  (`:416-418`). The guard is correct and complete — it is the same construct used for all nine
  pre-existing devices. `$(Device/rpi-5)` is likewise only expanded there. **OK.**
* **No shadowing of `Device/morse_ekh01_base`** (`:272`) — distinct name; `grep -c
  'define Device/morse_rpi5_base'` = 1, `Device/morse_ekh01_base` untouched by the diff. **OK.**
* `DEVICE_VARS` **already contains all three** required vars —
  `Makefile:9: DEVICE_VARS += SYSINFO_MODEL SYSINFO_BOARD_NAME DISTROCONFIG_EXTRA`.
  Confirmed as requested; no addition needed. **OK.**
* New `boards/rpi5/` directory is a sibling of `boards/ekh01/`; `boards/ekh01/*` untouched.
  Both new files end with `\n` (verified via `od -c`), so the `cat a b -` concatenation in
  `boot-rpi5-morse` will not glue `camera_auto_detect=0` onto `dtparam=spi=on`. **OK.**

### `991-dt-overlays-build-morse-overlays.patch` — **the counts are correct**

This was the flagged highest-risk item. Explicit count:

**Hunk 1 `@@ -184,7 +184,11 @@`**
pre-image: 7 context lines, 0 deletions → `-184,7` ✓
```
miniuart-bt.dtbo  mipi-dbi-spi.dtbo  mlx90640.dtbo  mmc.dtbo  mz61581.dtbo  ov2311.dtbo  ov5647.dtbo
```
post-image: 7 context + 4 additions (`mm610x-spi-pi5`, `mm610x-spi`, `mm810x-spi`, `mm_wlan`)
= 11 → `+184,11` ✓

**Hunk 2 `@@ -228,6 +231,7 @@`**
pre-image: 6 context → `-228,6` ✓; post-image: 6 + 1 (`raven.dtbo`) = 7 → `+…,7` ✓

The *only* defect is the **new-file start line**: it should now be `232` (228 + 4 delta), not
`231` — it was not refreshed after the extra line was added to hunk 1.

**Tested for real.** I reconstructed a synthetic `arch/arm/boot/dts/overlays/Makefile` with the
pre-image context at lines 184-190 and 228-233 and ran both applicators:

```
$ patch -p1 --dry-run --verbose < 991-dt-overlays-build-morse-overlays.patch
checking file arch/arm/boot/dts/overlays/Makefile
Using Plan A...
Hunk #1 succeeded at 184.
Hunk #2 succeeded at 232.
done                                       # exit 0

$ git apply --check -v 991-dt-overlays-build-morse-overlays.patch
Checking patch arch/arm/boot/dts/overlays/Makefile...
Hunk #2 succeeded at 232 (offset 1 line).  # exit 0, "GIT APPLY OK"
```

Both accept it; `patch`/quilt locate hunks by the **old** line number and treat the new start as
informational, so this is cosmetic (a `quilt refresh` would fix it). **No Pi 3 / Pi 4 breakage.**
Severity **LOW**, listed as finding #8a.

### `bcm2712/config-6.6` — subtarget-scoped, no shared file touched

Every change is inside `target/linux/bcm27xx/bcm2712/config-6.6`. `bcm2710/config-6.6` and
`bcm2711/config-6.6` are not in the diff. The cpufreq governor flip
(`:143-144`, ondemand → performance) actually brings bcm2712 **into line with bcm2711**
(`bcm2711/config-6.6:115-116` is already `PERFORMANCE`); bcm2710 stays on ondemand. Not scope
creep — parity. **OK.**

The `PSTORE*`, `SERIAL_RPI_FW`, and `USB_SERIAL*` blocks are byte-identical to the ones already
in `bcm2711/config-6.6:449, 512-517, 519-531`. **OK.**

### Other files — inert for Pi 3 / Pi 4

* `991-0008-…patch` creates a new file only; touches nothing existing.
* `boards/ekh-bcm2712/**`, `patches/ekh-bcm2712/**` — new directories, selected only by
  `-b ekh-bcm2712`. `patch_feeds_packages()` (`scripts/openmanet_setup.sh:120-155`) keys on
  `patches/${BOARD}`. The four patches are byte-identical to `patches/ekh-bcm2711/*`
  (verified with `diff -q`). **OK.**
* `.github/workflows/build-pr-bcm2712.yml` — structurally identical to
  `build-pr-bcm2711.yml`, same reusable-workflow inputs. `paths:` overlaps on
  `target/linux/bcm27xx/**` etc., which is intended (a shared-patch change should fire both
  jobs). **OK.**

---

# Task B — patch well-formedness: **both valid, both verified by execution**

`991-0008-dt-overlays-morse-add-rpi5-rp1-spi-overlay.patch`

* header `@@ -0,0 +1,86 @@` at line 52; `awk` count of `+` lines after it = **86** ✓
* zero non-`+` lines after the hunk header ✓ (no stray context that would break a create hunk)
* file ends with `\n` (`od -c` tail: `… + } ; \n`), no `\ No newline at end of file` needed
  (contrast: `991-0003` *does* have that marker and applies fine anyway)
* `--- /dev/null` + `-p1` create-file form is handled correctly:

```
$ patch -p1 --dry-run < 991-0008-...patch
checking file arch/arm/boot/dts/overlays/mm610x-spi-pi5-overlay.dts   # exit 0
$ patch -p1 < 991-0008-...patch
patching file arch/arm/boot/dts/overlays/mm610x-spi-pi5-overlay.dts
-rw-r--r-- 1561 bytes
$ git apply --check 991-0008-...patch                                 # GIT APPLY OK
```

The RFC-822-style `From:/Date:/Subject:` preamble before the diff is standard for this tree and
`patch` skips it ("Hmm... Looks like a unified diff to me").

The overlays Makefile rule builds `%.dtbo` from `%-overlay.dts`, so the filename
`mm610x-spi-pi5-overlay.dts` correctly produces the registered `mm610x-spi-pi5.dtbo`. ✓
`CONFIG_ARCH_BCM2835=y` is set for bcm2712 (`bcm2712/config-6.6:5`), so the
`dtbo-$(CONFIG_ARCH_BCM2835)` list *is* evaluated for the Pi 5 build — this resolves open
item #2 in `rp1-spi-research.md`. ✓

---

# Task C — device-tree review

### Labels: all resolve. **OK.**

| label | where defined |
|---|---|
| `rp1_spi0` | `950-1180…patch:8631` (`spi@50000`, `snps,dw-apb-ssi`) |
| `rp1_gpio` | `950-1180…patch:8918` (`gpio@d0000`); also aliased `gpio: &rp1_gpio` at `:1291` |
| `rp1_spi0_gpio9` | `950-1180…patch:9360` (child of `rp1_gpio`) |

Forward-referencing `rp1_morse_cs` / `_wake` / `_busy` / `_irq` / `_reset` from fragment@0 when
they are defined in fragment@1 is **valid** and is exactly what `991-0003` does with
`morse_wake`/`morse_busy`/`morse_irq`/`morse_reset`. dtc emits `__local_fixups__` for
overlay-internal phandle references and the RPi loader resolves them at apply time. ✓

### `function = "gpio"` — **valid**

`950-0530-pinctrl-Add-rp1-driver.patch:465` — `FUNC(gpio)` is in `rp1_func_names[]`
(`enum funcs` has `func_gpio`, `:255`). And every pin the overlay muxes has `gpio` available at
FSEL 5 (`RP1_FSEL_GPIO 0x05`, `:147`):

```
:531  PIN(5,  gpclk1, dpi, uart2, i2c2, dtr0, gpio, proc_rio, pio, spi3)
:534  PIN(8,  spi0,   dpi, uart3, i2c0, _,    gpio, proc_rio, pio, spi4)
:543  PIN(17, spi1,   dpi, dsi1_te_ext, _, uart0, gpio, proc_rio, pio, _)
:549  PIN(23, sd0,    dpi, i2s0,  i2c3, i2s1, gpio, proc_rio, pio, _)
:550  PIN(24, sd0,    dpi, i2s0,  _,    i2s1, gpio, proc_rio, pio, spi2)
```
✓ All five (5, 8, 17, 23, 24).

### Nested-child pinctrl form — **works, but is the odd one out** (MEDIUM, finding #6)

The overlay writes
```
rp1_morse_wake: rp1_morse_wake {
        pin_wake { function = "gpio"; pins = "gpio23"; bias-pull-up; };
};
```
whereas **every** RP1 group in the base tree puts the properties directly on the group node
(`950-1180…patch:9360-9372`):
```
rp1_spi0_gpio9: rp1_spi0_gpio9 {
        function = "spi0";
        pins = "gpio9", "gpio10", "gpio11";
        bias-disable;
        drive-strength = <12>;
        slew-rate = <1>;
};
```

**The driver accepts both.** `rp1_pctl_dt_node_to_map()`
(`950-0530-pinctrl-Add-rp1-driver.patch:1082-1102`) checks for the legacy `brcm,pins` property
and, when absent, delegates:

```c
	pins = of_find_property(np, "brcm,pins", NULL);
	if (!pins) /* Assume generic bindings in this node */
		return pinconf_generic_dt_node_to_map_all(pctldev, np, map, num_maps);
```

`pinconf_generic_dt_node_to_map()` (kernel `drivers/pinctrl/pinconf-generic.c`) first calls
`pinconf_generic_dt_subnode_to_map()` on the node itself — which returns 0 early with the
comment *"skip this node; may contain config child nodes"* when it has neither `pins` nor
`groups` — and then iterates `for_each_available_child_of_node()`, mapping each child. So the
parent `rp1_morse_cs` is skipped and `pin_cs` is mapped. `pinctrl-0 = <&rp1_morse_cs>` points at
the parent, which is the node the generic mapper walks. **Functionally correct.**

Recommendation is style-only but worth taking: flatten to the base-tree form. It removes an
extra indirection, matches `rp1_spi0_gpio9` two lines above it in the same `pinctrl-0` list, and
removes any dependency on the "skip this node" branch of a generic helper. Nothing in this
change set requires the nesting.

Related nit: the group *names* are carried over from the BCM283x overlay without re-checking —
`rp1_morse_wake` is GPIO23 and `rp1_morse_busy` is GPIO24, but both are consumed as
`power-gpios = <&rp1_gpio 23 0>, <&rp1_gpio 24 0>`, i.e. as **outputs**. `bias-pull-down` on an
output enable line (`rp1_morse_busy`) is inherited from `991-0003`'s `brcm,pull = <1>` and is
equally odd there. Not a defect introduced here; leaving it identical to Pi 4 is the right call
for a port.

### `spidev@0` / `spidev@1` disabling — **correct**

`950-1180…patch:7110-7130` shows both nodes declared under `&spi0` (== `&rp1_spi0`) in
`bcm2712-rpi.dtsi` with **no `status` property**, so they go live the moment the controller does,
and `spidev0` would claim CE0. The overlay's fragment@0 adds child nodes with matching names
(`spidev@0`, `spidev@1`) and `status = "disabled"`; libfdt merges overlay subnodes by name, so
the existing nodes are updated rather than duplicated. This is byte-for-byte the mechanism
`991-0003` already uses successfully on Pi 4. ✓

Ordering with `dtparam=spi=on` in `distroconfig-mm610x-spi.txt` is also right: the `dtparam`
line precedes the `dtoverlay=` line, so it applies to the base DTB first and the overlay's
`disabled` wins. ✓

### `cs-gpios = <&rp1_gpio 8 1>` vs `num-cs = <2>` — **not a problem**

Base declares `cs-gpios = <&gpio 8 1>, <&gpio 7 1>;` (`950-1180…patch:7113`) and `num-cs = <2>`
(`:8639`). An overlay property *replaces* the base property, so `cs-gpios` becomes a 1-entry
list while `num-cs` stays 2. In `spi_get_gpio_descs()` (kernel 6.6 `drivers/spi/spi.c`):

```c
nb = gpiod_count(dev, "cs");                                   /* = 1 */
ctlr->num_chipselect = max_t(int, nb, ctlr->num_chipselect);   /* = max(1,2) = 2 */
cs = devm_kcalloc(dev, ctlr->num_chipselect, sizeof(*cs), ...); /* 2 slots */
for (i = 0; i < nb; i++) { ... }                                /* fills [0] only */
```

`cs_gpiods[1]` stays NULL, which is only reached if a device is registered on CS1 — and
`spidev@1` is disabled. `max_native_cs` is not set by `spi-dw`, so the
`num_cs_gpios > max_native_cs` warning path is not taken. Polarity flag `1` = `GPIO_ACTIVE_LOW`
matches the base and matches the field guidance in `rp1-spi-research.md` §9.3(b). ✓

Dropping `spi0_cs_pins` from `pinctrl-0` (so GPIO7/CE1 is left unmuxed and GPIO8 goes to
`func_gpio` instead of the `spi0` hardware CS) is deliberate and correct for a GPIO chip select —
mirrors `991-0003`'s `BCM2835_FSEL_GPIO_OUT` override. ✓

### Minor DTS notes

* `frag0:` label on `__overlay__` (fragment@0) is **unused** — copied from `991-0003` where it
  is equally unused. Harmless. (LOW)
* Root `compatible = "brcm,bcm2712"` matches `bcm2712-rpi-5-b.dts`. ✓
* No `overlay_map` entry is needed for `mm610x-spi-pi5` since `distroconfig` names the
  `-pi5` overlay directly.
* `dtoverlay=ramoops-pi4` in `boards/rpi5/distroconfig.txt:43` is correct and the comment's
  reasoning checks out: `950-1288-dts-overlay_map-ramoops-pi4-works-on-Pi-5.patch:20` adds
  `bcm2712 = "ramoops-pi4";`, but `Build/boot-common` (`image/Makefile:36-38`) copies only
  `overlays/*.dtbo` and `overlays/README` — never `overlay_map.dtb` — so the firmware cannot do
  the remap. Naming it directly is the right workaround. ✓
* `dtparam=act_led_trigger=none` is valid on BCM2712 (`950-1180…patch:1890` defines the
  `act_led_trigger` override in the 2712 base). ✓
* `sysinfo.dtbo` is SoC-agnostic (targets `/`) and is already in the `CONFIG_ARCH_BCM2835`
  list via `992-0001`, so `boot-rpi5-morse`'s `dtoverlay=sysinfo,...` line will work. ✓

---

# Task D — build-breakers and config-symbol validity

### Config symbols: all real in this tree's 6.6

| symbol | evidence |
|---|---|
| `CONFIG_SPI_DESIGNWARE` | `target/linux/generic/config-6.6:6225`, `archs38/config-6.6:252` |
| `CONFIG_SPI_DW_DMA` | `generic/config-6.6:6228`, `archs38/config-6.6:253` |
| `CONFIG_SPI_DW_MMIO` | `generic/config-6.6:6229`, `archs38/config-6.6:254` |
| `CONFIG_SPI_DYNAMIC` | `bcm2711/config-6.6:537` |
| `CONFIG_SERIAL_RPI_FW` | `bcm2711/config-6.6:449` |
| `CONFIG_PSTORE*` block | `bcm2711/config-6.6:519-531` (identical) |

`SPI_DW_DMA`'s dependency is satisfiable at **build** time: in 6.6 it is a plain
`bool` inside `if SPI_DESIGNWARE` with no `DW_DMAC_PCI` dependency, and `CONFIG_DMADEVICES=y` /
`CONFIG_DMA_ENGINE=y` are already present (`bcm2712/config-6.6:213, 218`), so `spi-dw-dma.c`
compiles. The problem is purely at **runtime** — see BLOCKER #1. `CONFIG_SPI_MASTER` and
`CONFIG_SPI_DYNAMIC` are auto-computed (`def_bool`) and setting them explicitly is inert.

### #4 MEDIUM — `CONFIG_SPI_MEM` left off

`SPI_DESIGNWARE` carries `imply SPI_MEM`, but `generic/config-6.6:6240` has
`# CONFIG_SPI_MEM is not set` and bcm2712 does not override it — an explicit `n` beats an
`imply`, so `SPI_MEM` stays off. The only other `SPI_DESIGNWARE=y` target sets it on
(`archs38/config-6.6:256: CONFIG_SPI_MEM=y`). It builds either way (the `mem_ops` field of
`struct spi_controller` is unconditional) and the Morse driver uses plain `spi_sync()`, so this
is not a blocker — but it means a `make kernel_oldconfig` / `target/linux/refresh` will
re-add `# CONFIG_SPI_MEM is not set` noise and the config diverges from the reference target.
Decide it deliberately and write it down.

### #5 MEDIUM — `bsp-bcm271x` gating unverified

`boards/ekh-bcm2712/target_diffconfig:29: CONFIG_PACKAGE_bsp-bcm271x=y`

The author correctly reasoned about `persistent-vars-storage-bcm2711` being hard-gated to
`@TARGET_bcm27xx_bcm2711` (`:36-40`) and dropped it. `bsp-bcm271x` — a feed package, not present
in this checkout — was carried over without the same check. If it is likewise gated (or pulls
BCM283x-only helpers), `make defconfig` will **silently drop the line** with no error and the
image ships without it. Same applies to `CONFIG_MORSE_SPI=y` in `spi-rp1_diffconfig`. Verify
after `./scripts/openmanet_setup.sh -i`:
`grep -rn 'DEPENDS.*bcm27' feeds/openmanet/*/bsp-bcm271x/Makefile`.

### #7 MEDIUM — autoload stubs for built-in modules

`ModuleAutoLoad` (`include/kernel.mk:183-191`) writes `/etc/modules.d/<pkg>` unconditionally —
it has **no `modules.builtin` check**, unlike the install loop at `:247`. So the image will ship
`/etc/modules.d/spi-dw-mmio` (`AUTOLOAD:=$(call AutoProbe,spi-dw-mmio)`, `spi.mk:106`),
`spi-gpio`, `ramoops`, etc., naming modules that do not exist as `.ko`. `kmodloader` logs a
failure for each at boot. Cosmetic, but it adds noise to exactly the boot log that will be used
to debug the SPI bring-up. Resolving #3 resolves this too.

### #8 LOW — remaining nits

a. `991-dt-overlays-build-morse-overlays.patch` hunk 2 header says `+231`, should be `+232`.
   Both `patch` and `git apply` accept it (`git apply` prints `offset 1 line`). Run
   `quilt refresh` next time the patch is touched.
b. `Device/bcm2712_mm6108-spi:413` — `SUPPORTED_DEVICES += bcm2712,mm6108-spi` duplicates the
   value `morse_rpi5_base:391` already set from `SYSINFO_BOARD_NAME`
   (`$(subst _,$(comma),bcm2712_mm6108-spi)` = `bcm2712,mm6108-spi`). Harmless duplicate in
   sysupgrade metadata; **identical wart exists on `bcm2711_mm6108-spi:307`**, so leaving it is
   the consistent choice.
c. `Device/morse_rpi5_base:403` defines `IMAGE/factory.img.gz` while `IMAGES := sysupgrade.img.gz`
   (`:395`) means it is never produced — again identical to `morse_ekh01_base:282`. Consistent.
d. `patches/ekh-bcm2712/` duplicates four files from `patches/ekh-bcm2711/` byte-for-byte rather
   than sharing. `patch_feeds_packages()` keys strictly on `patches/${BOARD}` so a shared
   directory is not supported today; the duplication is the only option, but it now needs
   updating in two places.
e. `board_name` on this image will be `bcm2712,mm6108-spi` (via the sysinfo overlay,
   `base-files/lib/preinit/01_sysinfo`), which is **not** matched by
   `base-files/etc/board.d/02_network:12-33` or
   `base-files/lib/preinit/05_set_preinit_iface_brcm2708:7-27`. Note that `bcm2711,mm6108-spi`
   is *equally* unmatched on the shipping Pi 4 product, so networking must already come from the
   openmanet feed. Consistent with shipping behaviour — flagging only so it is not mistaken for
   a Pi-5-specific bug during bring-up.
f. The 25 MHz justification in the `991-0008` commit message is sound (200 MHz `clk_sys`,
   even divisors, 200/8 = 25.0 MHz exact vs Pi 4's effective 41.67 MHz), and it is a
   conservative choice. Worth re-raising to 33.3 MHz (200/6) once a link is up, as the message
   itself says.

---

## Bring-up checklist derived from this review

1. **Add `CONFIG_DW_AXI_DMAC=y` to `bcm2712/config-6.6`** (or drop `CONFIG_SPI_DW_DMA`) — without
   this the Pi 5 SPI bus does not come up, and the failure mode is a silent deferred probe.
2. Reconcile `spi-rp1_diffconfig` with the built-in symbols (#3).
3. `grep -rn SPI_CONTROLLER_ENABLE_CS_GPIOD feeds/morse/` once feeds are installed (#2).
4. `grep DEPENDS` on `bsp-bcm271x` for a `bcm2711`-only gate (#5).
5. Optional before commit: flatten the DTS pinctrl groups (#6), `quilt refresh` the overlays
   Makefile patch (#8a).
