# OpenMANET Raspberry Pi 5 Port — Status

Authoritative current-state file. Read this after CLAUDE.md at the start of every session.

## Current Objective

Add a Raspberry Pi 5 / BCM2712 OpenMANET product target (`bcm2712_mm6108-spi`)
— Seeed WM1302 HAT + Wio-WM6108 / Morse Micro MM6108 over SPI, US 900 MHz —
while preserving the shipping Raspberry Pi 4 (bcm2711) and Pi 3 (bcm2710) support.

## Repository State

| | |
|---|---|
| Branch | `pi5-wm6108-port` |
| Upstream baseline commit | `365b276` (== `origin/24.10` at session start) |
| Remote | `https://github.com/OpenMANET/firmware.git` |
| Reference PR | [#46](https://github.com/OpenMANET/firmware/pull/46) — OPEN, `mergeable: false`, and its own `Build ekh-bcm2712` CI job FAILS. Audited, selectively reused, NOT merged. |
| Read-only local ref | `pr46` → `19f0eea` (fetched via `git fetch origin pull/46/head:pr46`) |

## Hardware Target

Raspberry Pi 5 8GB + Seeed Studio WM1302 HAT + Wio-WM6108 (Morse Micro MM6108),
SPI0 on the 40-pin header, United States 900 MHz.

Pin map (identical to the shipping Pi 4 wiring):
reset GPIO17 · wake GPIO23 · busy GPIO24 · spi-irq GPIO5 · CS GPIO8 (CE0) · SPI0 GPIO9/10/11.

## Completed Milestones

### Investigation (4 parallel helpers, reports in `.ai-workflow/`)

- `pr46-audit.md` — full PR #46 audit and REUSE/MODIFY/DO-NOT-USE classification.
- `bcm2712-gap-analysis.md` — bcm2711-vs-bcm2712 gap analysis across the whole tree.
- `morse-mm6108-spi-analysis.md` — Morse feed / MM6108 SPI binding analysis.
- `rp1-spi-research.md` — BCM2712/RP1 SPI + pinctrl + overlay research.
- `pi5-change-review.md` — adversarial review of this session's changes.

### Key facts established

- The tree ALREADY has `target/linux/bcm27xx/bcm2712/` and a generic `Device/rpi-5`.
  PR #46 contributes ZERO generic BCM2712 enablement — its value is the Morse layer only.
- The pinned feeds ALREADY know this board: `bsp-common/files/uci-defaults/99_morse_radio_defaults`
  maps `bcm2712,mm6108-spi` to BCF `bcf_fgh100mhaamd.bin` with `country=US`, `channel=42`,
  and `bsp-bcm271x/files/board.d/03_openmanet_eth` lists `bcm2712,mm6108-spi`.
  This is why the device is named exactly `bcm2712_mm6108-spi` — `SYSINFO_BOARD_NAME`
  (`$(subst _,$(comma),$(1))`) then yields `bcm2712,mm6108-spi` and the US 900 MHz radio
  configuration comes for free.
- `kmod-mm6108` resolves to the OpenMANET feed package `om-pkgs/morse-micro/mm6108-driver`,
  whose Makefile hardcodes `CONFIG_MORSE_SPI=y` and `CONFIG_MORSE_COUNTRY=US`. The module is
  named `mm6108_sdio.ko` (feed patch `020-rename-module-to-mm6108_sdio.patch`) but contains
  BOTH SDIO and SPI support. An earlier concern that the SPI path was not built is resolved.
- The morse driver sets `SPI_CONTROLLER_ENABLE_CS_GPIOD` (`morse_driver/spi.c:1456`), pairing
  with in-tree kernel patch `991-0007`. That patch touches generic `drivers/spi/spi.c`, so it
  applies to the RP1 DesignWare controller too.
- On BCM2712 the labels `spi0` and `gpio` are re-pointed to `rp1_spi0` / `rp1_gpio`
  (see `950-1180`: `spi0: &rp1_spi0 { };` and `gpio: &rp1_gpio { ... }`). RP1 SPI is
  `snps,dw-apb-ssi`, driven by `spi-dw-mmio`.
- `Build/boot-common` copies only `*.dtbo` into the FAT partition, never `overlay_map.dtb`,
  so the Raspberry Pi firmware's automatic per-SoC overlay remapping is unavailable in OpenWrt
  images. Pi 5 overlays must therefore be named and selected explicitly.

### Implementation (committed; build not yet run)

1. `target/linux/bcm27xx/bcm2712/config-6.6` — the subtarget had NO SPI subsystem at all.
   Added `CONFIG_SPI`, `SPI_MASTER`, `SPI_DYNAMIC`, `SPI_BITBANG`, `SPI_GPIO`,
   `SPI_DESIGNWARE`, `SPI_DW_MMIO`, `SPI_DW_DMA`, `SPI_MEM` and `DW_AXI_DMAC`
   (RP1 SPI DMA hangs off a DesignWare AXI DMAC - see review finding 1), plus
   `PSTORE*`/`PSTORE_RAM`
   (the distroconfig uses a ramoops overlay) and `USB_SERIAL*` (cmdline.txt boots with
   `console=ttyUSB0`); cpufreq default governor ondemand → performance, matching bcm2711.
   32 insertions, 2 deletions, bcm2712-only.
2. New `patches-6.6/991-0008-dt-overlays-morse-add-rpi5-rp1-spi-overlay.patch` —
   `mm610x-spi-pi5-overlay.dts` targeting `&rp1_spi0` / `&rp1_gpio` with RP1 pinctrl syntax.
3. `991-dt-overlays-build-morse-overlays.patch` — registers `mm610x-spi-pi5.dtbo`
   (gated on `CONFIG_ARCH_BCM2835`, which bcm2712 does set).
4. `target/linux/bcm27xx/image/Makefile` — `Build/boot-rpi5-morse`, `Device/morse_rpi5_base`,
   `Device/bcm2712_mm6108-spi`, all inside `ifeq ($(SUBTARGET),bcm2712)`.
5. New `target/linux/bcm27xx/image/boards/rpi5/{distroconfig.txt,distroconfig-mm610x-spi.txt}`.
6. New `boards/ekh-bcm2712/` (target_diffconfig + 10 real mode-120000 symlinks) and
   `boards/common_extras/spi-rp1_diffconfig`.
7. New `patches/ekh-bcm2712/` — the four `ekh-bcm2711` feed patches (notably the
   golang/GCC-15 host fix, without which the openmanetd Go build fails).
8. New `.github/workflows/build-pr-bcm2712.yml`.

### Independent review outcome (`.ai-workflow/pi5-change-review.md`)

Pi 3 / Pi 4 regression hunt: **CLEAN**. Verified by execution, not inspection — both modified
kernel patches were reconstructed against a synthetic pre-image and applied with
`patch -p1 --dry-run` and `git apply --check`, both exit 0 with no offset. `Build/boot-rpi5-morse`
and `Device/morse_rpi5_base` are only reachable through `TARGET_DEVICES` inside
`ifeq ($(SUBTARGET),bcm2712)`; `DEVICE_VARS` already carries `SYSINFO_*` and `DISTROCONFIG_EXTRA`;
and `boards/common_extras/` is never globbed by `openmanet_setup.sh` (only name-indexed via `-x`),
so the new `spi-rp1_diffconfig` cannot leak into another board.

One real BLOCKER was found and fixed, plus five lesser findings:

| # | Was | Resolution |
|---|---|---|
| 1 | **BLOCKER** — `CONFIG_SPI_DW_DMA=y` with no DMA engine. `rp1_spi0` declares `dmas = <&rp1_dma …>` and `rp1_dma` is `snps,axi-dma-1.01a`, whose driver (`CONFIG_DW_AXI_DMAC`) was off. `spi-dw-mmio` would install `dma_ops`, `dma_request_chan()` would return `-EPROBE_DEFER`, and `dw_spi_add_host()` bails — **the SPI controller never probes and the MM6108 never enumerates, silently.** | FIXED: `CONFIG_DW_AXI_DMAC=y` added. All its prerequisites (`DMADEVICES`, `DMA_ENGINE`, `DMA_OF`, `DMA_VIRTUAL_CHANNELS`) were already `=y` for bcm2712, and the tree already carries eight RP1-specific `dw-axi-dmac` patches that were dead code until now. |
| 2 | HIGH — `SPI_CONTROLLER_ENABLE_CS_GPIOD` (defined by kernel patch `991-0007`) appeared to be set by nobody, which would leave Pi 5 CS init sequencing broken. | NOT A DEFECT. The reviewer only had the firmware repo. Verified in the pinned morse driver source: `morse_driver/spi.c:1456` does `spi->controller->flags \|= SPI_CONTROLLER_ENABLE_CS_GPIOD`, and the OpenMANET feed even ships `021-spi-demote-cs-gpiod-warning-to-runtime.patch` for the case where the kernel lacks it. |
| 3 | HIGH — `spi-rp1_diffconfig` was a no-op: all four `kmod-spi-*` it selected have their KCONFIG symbols forced `=y` by the same commit, and `scripts/kconfig.pl` `m+` mode lets `=y` win, so no `.ko` is produced. | FIXED: the file now selects only `CONFIG_MORSE_SPI=y` and documents that the SPI drivers are built in. |
| 4 | MEDIUM — `CONFIG_SPI_MEM` left off. `SPI_DESIGNWARE` only `imply`s it, and generic's explicit `n` wins. | FIXED: `CONFIG_SPI_MEM=y`, matching `archs38`, the only other `SPI_DESIGNWARE=y` target. |
| 5 | MEDIUM — `CONFIG_PACKAGE_bsp-bcm271x=y` might be silently dropped by `make defconfig` if the feed package is gated to bcm2711, the same trap as `persistent-vars-storage-bcm2711`. | NOT A DEFECT. Verified in the pinned feed: `bsp-bcm271x`'s `DEPENDS` carries no target gate, and `bsp-bcm271x/files/board.d/03_openmanet_eth` explicitly lists `bcm2712,mm6108-spi`. |
| 6 | MEDIUM — the DTS pinctrl groups used the nested `pin_* { }` child form (inherited from PR #46), the only place in the tree that does. | FIXED: flattened to match `rp1_spi0_gpio9` and every other in-tree RP1 group. Both forms in fact work — `rp1_pctl_dt_node_to_map()` delegates to `pinconf_generic_dt_node_to_map_all()` for nodes without `brcm,pins`, and that walks the node *and* its children — but there is no reason to be the odd one out. |
| 7 | MEDIUM — `/etc/modules.d/*` autoload stubs for now-built-in modules would make `kmodloader` log a failure per module, in exactly the boot log used to debug SPI. | FIXED as a consequence of #3. |
| 8a | LOW — hunk 2 of the overlays-build patch had an off-by-one new-start (`+231`, should be `+232`). | FIXED and re-verified: `git apply --check` is now clean with no offset. |

Deliberately left alone as consistent with the shipping Pi 4 product: the redundant
`SUPPORTED_DEVICES +=` line, the unused `IMAGE/factory.img.gz` recipe, and the fact that
`board_name` (`bcm2712,mm6108-spi`) is not matched by the in-tree `02_network` /
`05_set_preinit_iface_brcm2708` — `bcm2711,mm6108-spi` is equally unmatched today, because
networking comes from the openmanet feed's `03_openmanet_eth`.

## Build Environment

**READY. The WSL2 blocker is cleared.** The machine was rebooted (2026-08-27 20:05),
`.ai-workflow/setup-wsl-build-env.ps1` ran successfully, and the build environment is live.

| | |
|---|---|
| WSL distro | `openmanet-build` (Ubuntu 24.04, WSL2, imported to `C:\AI-Projects\OpenMANET-Pi5\wsl-openmanet`) |
| Resources | 24 processors / 47 GB RAM / 16 GB swap (`~/.wslconfig`), 953 GB free on ext4 |
| Build user | `builder` |
| Pi 5 build tree | `~/openmanet/firmware` — git mirror, remote `winrepo` -> `/mnt/c/AI-Projects/OpenMANET-Pi5/firmware`, at `ac924bb`, symlinks intact |
| Pi 4 regression tree | `~/openmanet/firmware-bcm2711` — separate `--shared` clone of the mirror, own `dl/`, so both boards can build concurrently without `.config` collisions |
| Logs | `~/logs/*.log` inside the distro |

Toolchain deps verified present: gcc, g++, make, git, python3, rsync, unzip, wget, quilt,
gawk, bison, flex, perl, swig, ccache. `subversion` is absent and not needed.

`~/rsync-from-windows.sh` was hardened: the Windows checkout has `core.symlinks=false`, so a
plain `rsync -a` would overwrite the mirror's real symlinks with the Windows text files and
`scripts/openmanet_setup.sh:267` would then abort. The script now restores every mode-120000
path from the git index after syncing. Prefer `~/sync-from-windows.sh` (git-based) anyway.

### Configuration verified after `openmanet_setup.sh -i -b ekh-bcm2712`

Exit 0. `.config` resolves to exactly the intended product:

```
CONFIG_TARGET_bcm27xx=y
CONFIG_TARGET_bcm27xx_bcm2712=y
CONFIG_TARGET_DEVICE_bcm27xx_bcm2712_DEVICE_bcm2712_mm6108-spi=y
CONFIG_PACKAGE_kmod-mm6108=y
CONFIG_PACKAGE_mm6108-firmware=y
```

The `alsa/openvlm` kconfig "recursive dependency detected" warning is pre-existing and
target-independent; `make defconfig` still completes and writes `.config`.

NOTE — `CONFIG_MORSE_SPI=y` from `boards/common_extras/spi-rp1_diffconfig` is dropped by
`make defconfig`. This is EXPECTED and harmless, and happens identically on `ekh-bcm2711`:
the symbol is declared in `feeds/openmanet/morse-micro/mm6108-driver/Config.in` as
`depends on PACKAGE_kmod-morse`, and this product selects `kmod-mm6108`, not `kmod-morse`.
SPI support is compiled in regardless — `mm6108-driver/Makefile:88` hardcodes
`CONFIG_MORSE_SPI=y` into `MORSE_MAKEDEFS` and comments that the OpenWrt `CONFIG_MORSE_*`
symbols are "unreliable here". No action needed.

## Most Recent Build

IN PROGRESS. `make -j24` for `ekh-bcm2712`, started 2026-08-27 ~20:30, log
`~/logs/build-bcm2712-01.log`. This is the FIRST compile of the Pi 5 target — from-scratch
toolchain, so several hours of wall clock. The `ekh-bcm2711` regression tree is being
prepared in parallel.

## Hardware Validation

NONE. Nothing below has been demonstrated on real hardware:
Pi 5 boot · RP1 SPI operation · MM6108 probe · HaLow interface creation · RF · mesh association.

## Blocker

None. (The WSL2 reboot blocker recorded in the previous session is resolved.)

## Next Engineering Action (exact)

1. Wait out `make -j24` in `~/openmanet/firmware`; on failure, classify, fix in the Windows
   authoritative tree, `~/sync-from-windows.sh`, rebuild the failing package only.
2. Once the kernel is unpacked into `build_dir/`, generate the deferred Pi 5
   `gpio-line-names` patch with `quilt` against the real post-patch
   `arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts`.
3. Confirm the produced artefacts under `bin/targets/bcm27xx/bcm2712/`: the sysupgrade image,
   `mm610x-spi-pi5.dtbo` inside the FAT partition, and `mm6108_sdio.ko` (or built-in) plus the
   `bcf_fgh100mhaamd.bin` BCF in the rootfs.
4. Run the `ekh-bcm2711` regression build in `~/openmanet/firmware-bcm2711` and diff its
   artefact list against the last known-good Pi 4 release.
5. Only then request the first hardware action (flash an SD card, COLD power cycle).

## Important Technical Decisions

- DO NOT MERGE PR #46. It is `mergeable: false` against a pre-1.8.0 merge base (`b2cc177`),
  its own bcm2712 CI job fails, and its `boards/ekh-bcm2712/target_diffconfig` uses dead
  package names (`morse-fw-6108`, `kmod-video-codec-bcm2835`). Its RP1 overlay was reused as
  a STARTING POINT only, rewritten with the fixes below.
- Separate `-pi5` overlay rather than extra fragments in `mm610x-spi`. The firmware overlay
  loader rejects an entire overlay if any fragment target label is unresolvable, so RP1
  fragments mixed into the shared overlay would break Pi 3 / Pi 4 / Seeed boards.
- `spidev@0` and `spidev@1` are explicitly disabled in the Pi 5 overlay. `bcm2712-rpi.dtsi`
  declares both under `&spi0` with no status property, so `spidev@0` would claim CE0 alongside
  the MM6108. PR #46 omits this; it is the prime first-boot failure suspect for that branch.
- Chip select uses a dedicated `rp1_morse_cs` group muxing GPIO8 to `function = "gpio"`,
  rather than reusing `rp1_spi0_cs_gpio7` (which muxes GPIO7+GPIO8 to the hardware `spi0` CS
  function). The driver drives CS as a GPIO descriptor. This mirrors what `991-0003` does on
  BCM283x, where `spi0_cs_pins` is overridden to `BCM2835_FSEL_GPIO_OUT` for the same reason.
- SPI clock 25 MHz for bring-up, not 50 MHz. On BCM2835 a requested 50 MHz is really
  41.67 MHz (250 MHz core clock, even divisors only), so 50 MHz has never actually been
  exercised on this hardware. The RP1 DW-SSI runs off clk_sys at 200 MHz, also
  even-divisors-only, so 50 MHz would be a true 50 MHz — 20% faster than the Pi 4 has ever
  run — and there are field reports of MM6108-on-RP1 instability at that rate. 200/8 = 25 MHz
  is exact. RAISE TO 33.3 OR 50 MHz once a two-node link is validated.
- Separate `boards/rpi5/` distroconfig directory instead of a `[pi5]` section in
  `boards/ekh01/distroconfig.txt`. The ekh01 file sets `dtoverlay=uart5` (no BCM2712
  equivalent) in its `[all]` block. A separate file gives the Pi 5 configuration zero Pi 4
  blast radius.
- `dtoverlay=ramoops-pi4` on Pi 5, because `overlay_map.dtb` is not shipped in OpenWrt images
  (see Key Facts) so the firmware cannot remap `ramoops` to `ramoops-pi4` for us.
- The Pi 5 profile builds the SPI variant ONLY. No SDIO, no MM8108/USB, no camera. That is the
  production path; the rest is scope this sprint does not need.
- `build-release.yml` is deliberately NOT wired up yet. Adding `build-ekh-bcm2712` to its
  `needs:` lists would make every release fail until the Pi 5 build is green. Wire it up
  after BUILD VERIFIED.

## Deferred / Known Follow-ups

- `gpio-line-names` for Pi 5. `991-0005` renames GPIO17/23/24 to `MM_RESET`/`MM_WAKE`/`MM_BUSY`
  in `bcm2711-rpi-4-b.dts`; Morse userspace (`chipreset.sh`, `gpioinfo --by-name`) looks the
  reset line up by that name. A matching patch is needed for
  `arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts`. Deliberately deferred to the build phase
  so it can be generated with `quilt` against the real post-patch tree rather than hand-written
  against patch context.
- `persistent-vars-storage-bcm2711` is hard-gated `@TARGET_bcm27xx_bcm2711` in the morse feed.
  Its script only calls `vcgencmd bootloader_config`, which does work on a Pi 5 — relaxing that
  dependency is a reasonable follow-up.
- Pi 5 camera (RP1 CFE / PiSP) has no kmod package in `target/linux/bcm27xx/modules/video.mk`.
- `base-files/etc/board.d/01_leds` HaLow ACT-LED case matches only `morse,ekh01*` — it does not
  cover `bcm2711,mm6108-spi` either, so this is a pre-existing gap, not a Pi 5 regression.
- A COLD POWER CYCLE (not a warm reboot) is required for the MM6108 first probe. Any hardware
  test plan must account for this.
