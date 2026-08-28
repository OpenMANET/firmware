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

### Implementation (committed, BUILD VERIFIED)

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
9. New `patches-6.6/991-0006-...-pi5.patch` — MM_RESET/MM_WAKE/MM_BUSY gpio-line-names
   on `&rp1_gpio` in the arm64 Pi 5 board DTS. Was a deferred follow-up; now done.
10. New `patches/ekh-bcm2712/0006` (chipreset fail-soft) and `0007` (gpsboard
   chip- and spi-path-agnostic) — see Important Technical Decisions.
11. New `patches/ekh-bcm27{11,12}/0008` (golang `go` symlink) and host-dependency +
   git-rewrite fixes in `.ai-workflow/provision-build-env.sh` — see Most Recent Build.

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

**BUILD VERIFIED — both targets green.**

| | |
|---|---|
| `ekh-bcm2712` (Pi 5) | `make -j20` exit 0, no errors. `openmanet-1.8.0-rpi5-mm6108-spi-squashfs-sysupgrade.img.gz`, 53,400,458 bytes, sha256 `3686d0b3c28a0e7ed7760bb40f1ca6c385030a3cde175d3ddb3bca382e064cea` (rebuilt at `e55ad37` for the debug-UART console). Log `~/logs/build-bcm2712-03.log`. |
| `ekh-bcm2711` (Pi 4 regression) | `make -j10` exit 0, no errors. All three shipping images produced: `rpi4-mm6108-spi`, `rpi4-mm6108-sdio`, `rpi4-mm8108-usb`. Log `~/logs/build-bcm2711-02.log`. |

Both built from commit `619022f` of `pi5-wm6108-port`.

### Three build blockers found and fixed — none of them Pi 5 regressions

The Pi 4 board was built in parallel from the start specifically so that "my change
or the tree?" could be answered by evidence. All three failures reproduced
identically on the untouched `ekh-bcm2711`.

1. **`runc` / `docker` / `containerd`: `go: not found`.** The `openmanet` feed is
   first in `feeds.conf.default`, so its golang shadows `feeds/packages/lang/golang`,
   and the two disagree about the host bin layout. Upstream's
   `GoCompiler/Default/Install/BinLinks` (`golang-compiler.mk:88`) links an
   unversioned `hostpkg/bin/go`; openmanet's (`golang-compiler.mk:100`) links only
   `go1.26` and compensates inside its own `golang-package.mk:182` with
   `GO_BIN_PATH`. Packages in the openmanet feed (openmanetd, tailscale, mavp2p)
   include that mk and are fine; runc and docker come from the packages feed and
   include the upstream mk, which expects a `go` that nothing creates.
   FIXED by `patches/ekh-bcm27{11,12}/0008`: the `golang` dummy package — which
   exists precisely to mean "the default Go version" — gets a `Host/Install` that
   links the unversioned names at `GO_DEFAULT_VERSION`, plus a `Host/Uninstall`.
   `$(LN)` is `ln -sf`, so it is idempotent and the versioned links are untouched.
2. **`openmanetd` hung rather than failed.** Its submodules use scp-style
   `git@github.com:OpenMANET/go-alfred.git` URLs; with no `url.insteadOf` rewrite the
   clone blocks on an SSH credential prompt indefinitely — the first diagnostic run
   sat on it for ten minutes with no error output. CI already handles this
   (`build-firmware.yml:82-85`); the WSL provisioning script did not.
   FIXED in `provision-build-env.sh`: the same three rewrite rules, plus
   `GIT_TERMINAL_PROMPT=0` and a `BatchMode` `GIT_SSH_COMMAND` so a missing
   credential fails fast instead of hanging.
3. **`openmanetd`: `/usr/bin/ld: cannot find -lnl-3 / -lnl-genl-3 / -lcap`.** Its
   `Build/Configure` runs `$(MAKE) -C internal/alfred/alfred`, which builds the
   alfred bindings with the HOST toolchain. CI installs those `-dev` packages
   (`build-firmware.yml:63-66`); the provisioning script carried only the
   OpenWrt-documented prerequisite set.
   FIXED in `provision-build-env.sh`: added libnl-3/libnl-genl-3/gps/cap/pkg-config,
   opus/opusfile/portaudio, pcre, net-tools, upx-ucl and golang-go.

### Pi 5 image contents verified by extraction, not by inference

The image was gunzipped, its partition table read, the FAT partition listed with
mtools and the squashfs unpacked with `unsquashfs`.

FAT boot partition:

- `kernel_2712.img` (14,260,232 bytes) and all six Pi 5 DTBs, including
  `bcm2712d0-rpi-5-b.dtb` for D0 silicon.
- `overlays/mm610x-spi-pi5.dtbo` present (2,430 bytes).
- `distroconfig.txt` correctly assembled from `boards/rpi5/distroconfig.txt` +
  `distroconfig-mm610x-spi.txt` + the generated sysinfo line, ending in
  `dtparam=spi=on`, `dtoverlay=mm610x-spi-pi5` and
  `dtoverlay=sysinfo,board-name="bcm2712,mm6108-spi",model="RPI RPI5-MM6108 (SPI)"`.
  That board-name is what makes the feed's US 900 MHz radio defaults apply.

Root filesystem:

- `/lib/modules/6.6.138/mm6108_sdio.ko` and `/lib/modules/6.6.138/batman-adv.ko`.
- `/etc/modules.d/mm6108` = `mm6108_sdio country=US enable_ext_xtal_init=1`.
- `/lib/firmware/morse/mm6108.bin` and `/lib/firmware/morse/bcf_fgh100mhaamd.bin` —
  the correct BCF for this hardware.
- `/etc/board.d/03_openmanet_eth` matches `bcm2712,mm6108-spi`.
- Both feed patches landed: `/morse/scripts/chipreset.sh` has `return 1` at line 22,
  and `/etc/init.d/gpsboard.init` uses `--by-name` and the suffix `expected_path`.
- `/usr/bin/openmanetd`, `/sbin/morse_cli`, `hostapd`, `wpa_supplicant`, `alfred`,
  `gpioset`, `gpioinfo` all present.

### Device tree verified in binary form

- `991-0006` applied to the real tree: `MM_RESET` / `MM_WAKE` / `MM_BUSY` at lines
  700 / 706 / 707 of the built `bcm2712-rpi-5-b.dts`, and present in BOTH compiled
  DTBs (`bcm2712-rpi-5-b.dtb` and `bcm2712d0-rpi-5-b.dtb`).
- `mm610x-spi-pi5.dtbo` decompiled: its `__fixups__` require exactly three external
  labels — `rp1_spi0`, `rp1_spi0_gpio9`, `rp1_gpio` — and all three resolve in both
  Pi 5 base DTBs. The firmware rejects an overlay whose labels cannot be resolved,
  so this is the strongest pre-hardware evidence available that the overlay loads.
- Final kernel `.config` carries `SPI_DESIGNWARE`, `SPI_DW_MMIO`, `SPI_DW_DMA`,
  `SPI_MEM` and `DW_AXI_DMAC`.
- Pi 4 unaffected: `MM_RESET` still present in the built `bcm2711-rpi-4-b.dtb`, and
  the Pi 4 `distroconfig-mm610x-spi.txt` still selects `mm610x-spi`, not the Pi 5
  overlay. The extra 2,430-byte `mm610x-spi-pi5.dtbo` sits unreferenced in the Pi 4
  boot partition.

### Pi 4 vs Pi 5 manifest diff — 507 vs 457 packages, fully accounted for

Only `mm6108-firmware` is Pi-5-only. Everything Pi-4-only falls into a category this
port deliberately excluded, with no surprises: the camera/VideoCore stack and its
transitive deps (`kmod-video-*`, `kmod-camera-*`, `libcamera`, `mediamtx`,
`camera-onvif-server`, `luci-app-camera`, `libdrm`, `libpng`, `libfreetype`,
`libevent2*`, `rpcd-mod-onvif`); `kmod-mm8108` + `mm8108-firmware` (Pi 5 builds the
SPI variant only); `kmod-spi-bcm2835{,-aux}`, `kmod-spi-bitbang`, `kmod-spi-gpio`,
`kmod-i2c-bcm2835` (BCM283x controllers — on Pi 5 the RP1 DesignWare drivers are
built into the kernel, which is exactly what `spi-rp1_diffconfig` was written for);
`kmod-r8125`, `kmod-of-mdio`, `kmod-fixed-phy` (EKH01 carrier NIC and the lan78xx
workaround); and `persistent-vars-storage-bcm2711` (hard-gated to bcm2711 in the
feed).

## Hardware Validation

NONE. Nothing below has been demonstrated on real hardware:
Pi 5 boot / RP1 SPI operation / MM6108 probe / HaLow interface creation / RF / mesh
association. Everything above is BUILD VERIFIED only.

## Blocker

None in software. The port is now blocked on physical hardware access.

## Next Engineering Action (exact)

OWNER ACTION REQUIRED — one action: flash and boot a Pi 5.

Image (checksum verified after the copy):

```
C:\AI-Projects\OpenMANET-Pi5\images\openmanet-1.8.0-rpi5-mm6108-spi-squashfs-sysupgrade.img.gz
sha256 3686d0b3c28a0e7ed7760bb40f1ca6c385030a3cde175d3ddb3bca382e064cea
53,400,458 bytes
```

1. Flash it to an SD card (full disk image).
2. Fit the card in the Pi 5 with the WM1302 HAT + Wio-WM6108.
3. Plug the Waveshare Pi 5 3-pin UART lead into the dedicated JST-SH **debug UART
   connector** between the HDMI ports. No jumper wires, no GPIO14/15 needed.
4. Open the port at **115200 8N1**.
5. **Cold power cycle** — pull power. A warm reboot is not sufficient for the MM6108
   first probe.
6. Capture the serial log.

The debug connector now carries the bootloader/firmware output *and* the full Linux
kernel log *and* a login shell (`/dev/console` is ttyAMA10). GPIO14/15 remains a
115200 fallback if the plug misbehaves.

What to look for, in order:

1. RP1 enumerates over PCIe and `pinctrl-rp1` probes.
2. `spi-dw-mmio` binds and `spi0` appears — if `DW_AXI_DMAC` were wrong this fails
   silently with `-EPROBE_DEFER` and nothing else is reported.
3. The morse driver probes on `spi0.0` and reads the chip ID.
4. `bcf_fgh100mhaamd.bin` and `mm6108.bin` load.
5. A HaLow `wlan` interface is created.
6. `morsechipreset` at S09 does NOT log "unable to reset as MM_RESET is not in
   gpio-line-names" — if it does, the overlay did not load.

Two units are needed for the Phase 1 mesh objective; one is enough to prove boot, SPI
and MM6108 probe.

## Important Technical Decisions

- SERIAL CONSOLE: the Pi 5 hardware-validation console is the dedicated 3-pin JST-SH debug
  connector (SoC uart10, alias `serial10`, `ttyAMA10`), NOT GPIO14/15. Verified against the
  built kernel: `pl011_probe_dt_alias()` calls `of_alias_get_id(np, "serial")` so the alias
  number becomes the tty index, and `UART_NR` is 14 so index 10 is in range and is not folded
  back to 0 by the guard in `pl011_console_setup()`.
  `bcm2712-rpi-5-b.dtb` already carries `stdout-path = "serial10:115200n8"`, but that alone is
  not enough: any `console=` on the kernel command line sets `console_set_on_cmdline`, and
  `of_console_check()` then declines to register the stdout-path console. So `ttyAMA10` has to
  be named explicitly, and it is listed LAST so it also becomes `/dev/console` — which is what
  inittab's `::askconsole` attaches to, giving a login shell and not just a one-way log. HDMI
  keeps its shell through the separate `tty1::askfirst` entry.
  Implemented Pi-5-only via the mechanism the image architecture already provides:
  `Build/boot-rpi5-morse` overwrites `distroconfig.txt` after `Build/boot-common` has run, so
  it now overwrites `cmdline.txt` the same way from `boards/rpi5/cmdline.txt`. The shared
  `cmdline.txt` is untouched — verified by extraction: the Pi 4 image's `cmdline.txt` is
  byte-identical to the shared source, and all three Pi 4 images are byte-size identical across
  independent builds. `Build/boot-rpi5-morse` is referenced only by `Device/morse_rpi5_base`.
  All bauds are explicit. `console=serial0` carried no options, which makes
  `pl011_console_setup()` fall through to `pl011_console_get_options()`; that only derives the
  rate when `UARTEN` is already set in hardware and otherwise leaves its local default of
  38400. GPIO14/15 is kept, now pinned to `115200n8`, purely as a first-boot fallback.
  `uart_2ndstage=1` was deliberately NOT added — the Pi 5 bootloader already talks to this
  connector natively. Add it only if verbose second-stage firmware logging is wanted.
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
  STATUS: the Pi 5 build is now green, so this is unblocked and is the next non-hardware
  task. Not done in this session because CI wiring cannot be validated without pushing.

## Deferred / Known Follow-ups

- DONE (was deferred) `gpio-line-names` for Pi 5 — delivered as `991-0006`, verified present
  in both compiled Pi 5 DTBs. See Most Recent Build.
- `persistent-vars-storage-bcm2711` is hard-gated `@TARGET_bcm27xx_bcm2711` in the morse feed.
  Its script only calls `vcgencmd bootloader_config`, which does work on a Pi 5 — relaxing that
  dependency is a reasonable follow-up.
- Pi 5 camera (RP1 CFE / PiSP) has no kmod package in `target/linux/bcm27xx/modules/video.mk`.
- `base-files/etc/board.d/01_leds` HaLow ACT-LED case matches only `morse,ekh01*` — it does not
  cover `bcm2711,mm6108-spi` either, so this is a pre-existing gap, not a Pi 5 regression.
- A COLD POWER CYCLE (not a warm reboot) is required for the MM6108 first probe. Any hardware
  test plan must account for this.
