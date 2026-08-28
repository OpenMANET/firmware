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
   `SPI_DESIGNWARE`, `SPI_DW_MMIO`, `SPI_DW_DMA`, plus `PSTORE*`/`PSTORE_RAM`
   (the distroconfig uses a ramoops overlay) and `USB_SERIAL*` (cmdline.txt boots with
   `console=ttyUSB0`); cpufreq default governor ondemand → performance, matching bcm2711.
   30 insertions, 2 deletions, bcm2712-only.
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

## Build Environment

BUILD NOT YET ATTEMPTED. OpenWrt cannot build on Windows.

WSL2 was NOT installed on this machine. It is now staged and ready:

- `VirtualMachinePlatform` and `Microsoft-Windows-Subsystem-Linux` optional components ENABLED
  (via DISM; both reported success, exit code 3010 = reboot required).
- WSL runtime 2.7.12 INSTALLED at `C:\Program Files\WSL\wsl.exe` (`wsl --version` works).
- Ubuntu 24.04 WSL rootfs downloaded to
  `C:\AI-Projects\OpenMANET-Pi5\wsl-stage\ubuntu-noble-rootfs.tar.gz` (340 MB).
- `wsl --status` reports "WSL2 is unable to start since virtualization is not enabled" —
  this is purely the pending reboot. The CPU is an AMD Ryzen 9 9950X3D with
  `VirtualizationFirmwareEnabled: True`, 16C/32T, 61.6 GB RAM, 613 GB free on C:.

Build tree design (per CLAUDE.md "Build Rules"): the Windows repo remains the single
authoritative source tree. The WSL distro gets a BUILD MIRROR clone whose `winrepo` remote
points back at `/mnt/c/AI-Projects/OpenMANET-Pi5/firmware`. Building in WSL ext4 is required
because the Windows checkout has `core.symlinks=false` (so `boards/*/spi_diffconfig` and
friends are plain text files there, and `scripts/openmanet_setup.sh:267` ABORTS if they are
not symlinks) and because OpenWrt needs a case-sensitive filesystem. Never commit from the
mirror.

## Most Recent Build

None. No build has been run — see Blocker.

## Hardware Validation

NONE. Nothing below has been demonstrated on real hardware:
Pi 5 boot · RP1 SPI operation · MM6108 probe · HaLow interface creation · RF · mesh association.

## Blocker

A single Windows reboot is required to activate the WSL2 optional components.
Everything else for the build environment is already installed and staged.

## Next Engineering Action (exact)

1. Owner reboots the machine.
2. From an elevated PowerShell in the repo root, run:
   `powershell -ExecutionPolicy Bypass -File .ai-workflow\setup-wsl-build-env.ps1`
   (idempotent; imports the `openmanet-build` distro, writes a `~/.wslconfig` sized for
   16C/32T + 61 GB RAM, provisions the OpenWrt build dependencies, creates the `builder`
   user and clones the build mirror).
3. `wsl -d openmanet-build -u builder`
4. `cd ~/openmanet/firmware && ./scripts/openmanet_setup.sh -i -b ekh-bcm2712`
5. `make -j$(nproc)` — then iterate on failures per CLAUDE.md "Build Rules".
6. Regression build: `./scripts/openmanet_setup.sh -i -b ekh-bcm2711 && make -j$(nproc)`.

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
