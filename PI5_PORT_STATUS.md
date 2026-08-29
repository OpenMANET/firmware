# OpenMANET Raspberry Pi 5 Port — Status

Authoritative current-state file. Read this after CLAUDE.md at the start of every session.

## Current Objective

**PHASE 1 COMPLETE — HARDWARE VERIFIED (2026-08-28).**

The Raspberry Pi 5 / BCM2712 OpenMANET product target (`bcm2712_mm6108-spi`) —
Seeed WM1302 HAT + Wio-WM6108 / Morse Micro MM6108 over SPI, US 900 MHz — is
delivered and demonstrated on physical hardware end to end, with the shipping
Raspberry Pi 4 (bcm2711) and Pi 3 (bcm2710) support preserved and regression-verified.

Current objective is now Phase 2 hardware validation: WM1302 GPS, then the external
USB Wi-Fi AC dongle. NVMe stays deferred. See Next Engineering Action.

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
| `ekh-bcm2712` (Pi 5) | `make -j20` exit 0, no errors. `openmanet-1.8.0-rpi5-mm6108-spi-squashfs-sysupgrade.img.gz`, 53,560,146 bytes, sha256 `6d97eb9a3502c30916a00775141e51b1c03e654e2eb4bb5f8243d469d3bc20bd` (rebuilt at `a7ed9bc`; all earlier images superseded). Log `~/logs/build-2712-v4.log`. |
| `ekh-bcm2711` (Pi 4 regression) | `make -j12` exit 0, no errors. All three shipping images produced: `rpi4-mm6108-spi`, `rpi4-mm6108-sdio`, `rpi4-mm8108-usb`. Last run at `a3b80a1`, log `~/logs/build-2711-v2.log`. |

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

# PHASE 1: HARDWARE VERIFIED — COMPLETE (2026-08-28)

The Raspberry Pi 5 OpenMANET port is **HARDWARE VERIFIED, not merely BUILD VERIFIED.**
The complete physical path has been demonstrated on real hardware:

```
Pi 5 -> RP1 -> SPI -> MM6108 -> 923 MHz Wi-Fi HaLow -> 802.11s -> BATMAN-adv -> Pi 4
```

### Platform bring-up

- Raspberry Pi 5 boots OpenMANET.
- The dedicated Pi 5 3-pin JST-SH UART provides bootloader, kernel AND interactive
  console at 115200 — the `boards/rpi5/cmdline.txt` / `ttyAMA10` work is confirmed
  correct on hardware, including the login shell via `/dev/console`.
- RP1 initialises.
- SPI/DW-SSI and DW AXI DMA initialise — the `CONFIG_DW_AXI_DMAC=y` review finding is
  vindicated. Without it the SPI controller would have failed to probe silently and
  the MM6108 would never have enumerated.

### Radio

- Wio-WM6108 / MM6108 probes successfully on `spi0.0`.
- GPIO reset works (`991-0006` `MM_RESET` line naming confirmed good).
- MM6108 firmware loads.
- US BCF loads: `bcf_fgh100mhaamd.bin`. Country = US.
- HaLow interface `wlh0` comes up.

### Mesh — the Phase 1 objective

OpenMANET provisioning creates the intended topology exactly as designed:

```
wlh0 -> batmesh0 -> bat0 -> br-ahwlan
```

- BATMAN algorithm = `BATMAN_V`.
- Pi 5 provisioned as **Mesh Point**; Pi 4 provisioned as **Mesh Gate**.
- Both: Mesh ID `openmanet`, width 2 MHz, channel 42 / 923 MHz.
- A real 802.11s HaLow peer connection was established between Pi 5 and Pi 4.

Pi 5 station dump:

| | |
|---|---|
| mesh plink | ESTAB |
| authorized / authenticated / associated | yes / yes / yes |
| signal | ~ -46 dBm |
| expected throughput | ~ 7.52 Mbps |

BATMAN neighbour on Pi 5: `a8:dd:9f:4d:c0:e3` via `wlh0`, throughput ~7.2.
The BATMAN originator table showed the Pi 4.

End-to-end IP ping, Pi 5 -> Pi 4: **4/4 replies, 0% packet loss,
min/avg/max 3.620 / 3.892 / 4.105 ms**.

### CLAUDE.md "Phase 1 Definition of Done" — status

| Item | Status |
|---|---|
| Raspberry Pi 5 BCM2712 target | DONE |
| Successful OpenMANET firmware build | DONE |
| Bootable Pi 5 image | DONE |
| Pi 4 support preserved | DONE — regression-verified by content, not checksum |
| Pi 5 WM1302 / Wio-WM6108 SPI support | HARDWARE VERIFIED |
| Morse Micro MM6108 driver | HARDWARE VERIFIED |
| Required MM6108 firmware | HARDWARE VERIFIED |
| Correct BCF | HARDWARE VERIFIED (`bcf_fgh100mhaamd.bin`, US) |
| openmanetd | HARDWARE VERIFIED (provisioning applied) |
| batman-adv | HARDWARE VERIFIED (`BATMAN_V`) |
| Mesh functionality | HARDWARE VERIFIED (802.11s, plink ESTAB) |
| Pi 5 hardware boot | HARDWARE VERIFIED |
| HaLow interface initialisation | HARDWARE VERIFIED (`wlh0`) |
| Two-node mesh association | HARDWARE VERIFIED (Pi 5 point <-> Pi 4 gate) |
| BATMAN path | HARDWARE VERIFIED (neighbour + originator table) |
| IP traffic across mesh | HARDWARE VERIFIED (4/4 ping, 0% loss) |

**Phase 1 is complete.**

### Not yet hardware validated (Phase 2 scope)

- WM1302 HAT GPS/GNSS.
- External USB Wi-Fi AC dongle for local high-speed EUD/ATAK access.
- NVMe.

## BATMAN-adv provisioning — RESOLVED (root cause recorded 2026-08-28)

**Resolved by provisioning. The missing `bat0` before provisioning was expected
factory/unprovisioned behaviour, NOT a defect.** Once the mesh was provisioned the
intended topology came up exactly as designed and Phase 1 passed end to end (see
Hardware Validation above).

**Operational note that cost real time — record for the next unit:** on the Pi 4,
running **Quick Config alone was NOT sufficient** to rebuild the BATMAN topology.
Running the **full 802.11s mesh wizard** corrected it. Quick Config does not exercise
`wizard.js:1214 save()` -> `uci.js:444-518`, which is the only path that creates
`bat0` / `batmesh0` / `batmesh1` and appends `bat0` to `br-ahwlan`. If a node comes up
without `bat0` after a flash, run the full wizard, not Quick Config.

The original analysis follows, because it explains *why* no `bat0` exists on a freshly
flashed unit and should stop a future session re-investigating it.

Nothing in the image — on Pi 4 or Pi 5 — creates a batman-adv device at boot. Only
three things in the entire tree ever write `proto 'batadv'`:

1. `feeds/openmanet/luci/luci-app-morseconfig/htdocs/luci-static/resources/tools/morse/uci.js:444-518`
   (`setupBatmanDeviceOnNetwork` → `bat0`, `batmesh0`, `batmesh1`, then appends
   `bat0` to the `br-ahwlan` bridge), called only from `wizard.js:1214` `save()`.
2. openmanetd `ApplySetup` RPC phase 10 —
   `internal/openmanet/server/handlers/setup_phases.go:1150-1181` `runBatmanAdv()`.
   There is no first-boot auto-apply; `ManagementConfig.Start()` (`mgmt.go:95-112`)
   only sets MTU, multicast, forceflood and the MT7915-only `batmesh1` helper.
3. `/etc/uci-defaults/99-migrate-batadv_hardif` — dead code. Its whole body is gated
   on `[ -f /etc/config/batman-adv ]`, and no package ships that file.

No `board.d` script, no `uci-defaults` script and no package ships an
`/etc/config/network` containing batman. `/etc/config/network` is generated at first
boot by `/bin/config_generate` from `/etc/board.json`, and the only OpenMANET board.d
contribution is `03_openmanet_eth`, which sets `lan = eth0` and nothing else.

The observed wireless state — `mode='ap'`, `network='lan'`, `encryption='sae'`,
`ssid='BCM2712-3f76'` — is the correct factory default, byte-for-byte the output of
`netifd-morse/lib/wifi/morse.sh:90-97` plus `morse-wireless-defaults:153-157`. The
SSID is `$DEVICE_PRODUCT-$MAC4`, and `DEVICE_PRODUCT` is `CONFIG_VERSION_PRODUCT`
= `BCM2712`. A fresh Pi 4 produces the identical thing with a `BCM2711-` prefix.

**The `config interface 'bat0'` / `option multicast_mode '0'` stub is a red herring,
not a half-built mesh.** openmanetd runs `configureBatmanForceflood` on every start
(`mgmt.go:105`); with forceflood defaulting false (`config.go:27`) it writes
`multicast_mode='0'` to section `bat0` through `uci_network.go:238`, which calls
`AddSection()` unconditionally and never sets `proto`. netifd ignores a proto-less
section entirely. This is upstream openmanetd behaviour, identical on Pi 4, and was
deliberately NOT changed — this is a port, and changing it would alter Pi 4.

CAVEAT worth confirming: if production Pi 4 units genuinely arrive mesh-ready, that
provisioning happens outside this repository (factory step, a `files/` overlay in a
CI job, or a golden config). It is not in this tree.

### `persistent_vars_storage.sh` — NOT causal

`morse-wireless-defaults` has no `set -e`; lines 19 and 24 are plain command
substitutions, so a missing binary yields `""` and the script continues on its normal
path (line 20 is an explicit random-key fallback). Decisively: on Pi 4 the script
exists but runs under `set -eu` and greps `vcgencmd bootloader_config` for keys that
are absent on stock hardware, so it **exits 1 with empty stdout there too**. Both
boards get identical empty values; the delta is two stderr lines. The script contains
no network, mesh or batman logic at all.

Fixed anyway for parity (see 0009 below), because leaving a package that ten
installed scripts call missing is a real packaging gap.

## Blocker

None. Phase 1 is complete and hardware verified. The only prerequisite for the next
phase is flashing the current image (it carries the openmanetd BCM2712 board-capability
support that GPS validation depends on) - see Next Engineering Action.

## Next Engineering Action (exact)

Phase 1 is complete. The next hardware-validation areas, in order:

### 1. Flash the current image first — required before GPS validation

The unit that completed Phase 1 is running an image built BEFORE commit `a3b80a1`.
It therefore does NOT contain the openmanetd BCM2712 board-capability support, so
`GNSSsupoorted()` still returns false on it and the WM1302 GPS will look broken for a
reason that has nothing to do with the GPS.

**Flash this before starting GPS work:**

```
C:\AI-Projects\OpenMANET-Pi5\images\openmanet-1.8.0-rpi5-mm6108-spi-squashfs-sysupgrade.img.gz
sha256 6d97eb9a3502c30916a00775141e51b1c03e654e2eb4bb5f8243d469d3bc20bd
53,560,146 bytes
```

Contains `a3b80a1`: `patches/ekh-bcm2712/0010` (openmanetd recognises
`bcm2712,mm6108-spi`, so GNSS/BLOS/Comms report supported) and `0009`
(`persistent_vars_storage.sh` present, boot-log noise gone).

After flashing, re-provision the mesh (see the note below on Quick Config) and
re-confirm the Phase 1 path still comes up before moving on.

### 2. WM1302 HAT GPS / GNSS

`patches/ekh-bcm2712/0007` already made `gpsboard.init` chip- and SPI-path-agnostic
for BCM2712: it resolves GPS_RST/GPS_WAKE by gpio-line-name with `--strict` instead of
assuming `gpiochip0` (which on a Pi 5 is a SoC brcmstb controller, not RP1), and
suffix-matches `spi_master/spi0/spi0.0` instead of the literal BCM2711 SPI0 address.
Neither half of that has been exercised on hardware yet.

Expected checks: `gpioinfo --by-name GPIO25` / `GPIO12` resolve on RP1; `gpsboard.init`
does not `exit 0` early; `gpsd` gets a fix; openmanetd reports GNSS supported and
publishes position over alfred/CoT.

### 3. External USB Wi-Fi AC dongle

For local high-speed Wi-Fi / EUD / ATAK access, per the architecture intent. The
HaLow mesh stays the MANET transport; this is a separate access interface. Do NOT
redesign around Pi 5 onboard Wi-Fi.

### 4. NVMe — deferred

Explicitly deferred until the core radio / GPS / USB-Wi-Fi stack is validated.

### 5. Wire `build-ekh-bcm2712` into `build-release.yml`

Unblocked since the Pi 5 build went green; still not done because CI wiring cannot be
validated without pushing the branch.

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
- DONE (was deferred) `persistent-vars-storage-bcm2711` gating — relaxed to bcm2711||bcm2712 by
  `patches/ekh-bcm2712/0009` and selected in the board diffconfig. See Post-hardware-validation
  fixes below.
- Pi 5 camera (RP1 CFE / PiSP) has no kmod package in `target/linux/bcm27xx/modules/video.mk`.
- `base-files/etc/board.d/01_leds` HaLow ACT-LED case matches only `morse,ekh01*` — it does not
  cover `bcm2711,mm6108-spi` either, so this is a pre-existing gap, not a Pi 5 regression.
- A COLD POWER CYCLE (not a warm reboot) is required for the MM6108 first probe. Any hardware
  test plan must account for this.
- NVMe on the Pi 5 — DEFERRED until the core radio / GPS / USB-Wi-Fi stack is validated.
  Not started, not investigated. Revisit after Phase 2.
- USB Wi-Fi AC dongle for local EUD/ATAK access — Phase 2, deferred until after GPS.
  Architecture intent: the MM6108 HaLow interface carries the MANET/BATMAN mesh; the
  dongle is a separate local access interface. Do NOT redesign around Pi 5 onboard Wi-Fi.

## Post-hardware-validation fixes (commit `a3b80a1`)

Both found while tracing the missing `bat0`; neither is its cause. Both are
board-scoped to `ekh-bcm2712`, so the shipping Pi 4 product is untouched by
construction — no shared file was modified.

- `patches/ekh-bcm2712/0009` — relaxes `persistent-vars-storage-bcm2711`'s
  `@TARGET_bcm27xx_bcm2711` gate to `bcm2711||bcm2712`, and the board diffconfig now
  selects it. The gate was packaging, not hardware: the script's only dependency is
  `vcgencmd bootloader_config` from `bcm27xx-userland`, and `/usr/bin/vcgencmd` was
  already in the Pi 5 rootfs. Ten installed scripts call it. Parity/log-noise fix
  only — see the "NOT causal" note above; it changes no resulting configuration.
- `patches/ekh-bcm2712/0010` — adds a package patch inside the openmanetd feed
  package (same mechanism `0002` uses for collectd) adding `BCM2712_MM6108_SPI` to
  `internal/util/board/board_type.go` and listing it beside `BCM2711_MM6108_SPI` in
  `GNSSsupoorted()`, `BLOSsupported()` and `CommsSupported()`. All three switches end
  in `default: return false`, so the Pi 5 was silently reporting GNSS, BLOS and Comms
  unsupported on hardware that supports them — this is what would have made the
  WM1302 GPS look broken later for a non-obvious reason. `ExecutionProfileFor()` is
  deliberately left alone; the zero profile is right for a 4-core Cortex-A76.

Verified in the built rootfs, not inferred: `/sbin/persistent_vars_storage.sh` is
present, and `strings usr/bin/openmanetd` contains `bcm2712,mm6108-spi` exactly once,
the same count as `bcm2711,mm6108-spi`.

Deliberately NOT changed: openmanetd's `configureBatmanForceflood` creating a
proto-less `bat0` section (`uci_network.go:238`). It is misleading during diagnosis
but is upstream behaviour identical on Pi 4, and this is a port, not a redesign.
Worth raising upstream.

### Pi 4 regression evidence for `a3b80a1`

No shared file was modified — the whole change set lives in `patches/ekh-bcm2712/`
and `boards/ekh-bcm2712/` — so Pi 4 is unaffected by construction. Verified anyway by
rebuilding `ekh-bcm2711` at `a3b80a1` and comparing against the images built at
`a6da409`:

- `make -j12` exit 0, all three shipping images produced.
- Boot partition: `cmdline.txt` and `distroconfig.txt` byte-identical.
- Root filesystem: unsquashed both and ran `diff -rq --no-dereference`. **Exactly one
  file differs** — `usr/share/ucode/luci/template/header.ut`, and only in LuCI's
  cache-busting query string (`?v=9aqZQSU2PzNSg` vs `?v=Hu1kSpomZM1EO`), a token
  regenerated on every build. Everything else is identical.

The `.img.gz` sha256 values therefore differ between builds, but that is build
non-determinism in one LuCI template, not a functional change. Recorded here so a
future session does not mistake a checksum delta for a regression.

## USB Wi-Fi AC adapter — driver baked in (commit `a7ed9bc`)

USB ID `0bda:b812` enumerated on the Pi 5 but produced no wireless interface: the
image contained no matching driver.

**Chipset mapping (verified in source, not from the marketing name).** The adapter is
sold as "RTL8812BU USB3.0 802.11ac 1200M", but `0xb812` is the FIRST entry of
`rtw_8822bu_id_table[]` in `backports-6.12.61/drivers/net/wireless/realtek/rtw88/
rtw8822bu.c:12`, bound to `rtw8822b_hw_spec`. It is rtw88's 8822b family. It is NOT
`rtl8812au-ct`, which is the 8812AU (`0bda:8812`), a different part that this tree
does also build. No out-of-tree 88x2bu driver is needed — OpenWrt 24.10 builds
mac80211 from backports-6.12.61, which has rtw88 USB support in-tree.

**Not missing, mis-selected.** `boards/common/kmods_diffconfig:245` already set
`kmod-rtw88-8822bu=m`, so the .ipk was built for every board and installed into none.
The Pi 4 product has the identical gap — no board in the tree selects any rtw88 `=y`.
Not a Pi 5 regression.

**Fix:** two lines in `boards/ekh-bcm2712/target_diffconfig` (Pi-5-only; no shared
file touched, so Pi 3 / Pi 4 images are unchanged by construction):

```
CONFIG_PACKAGE_kmod-rtw88-8822bu=y
CONFIG_PACKAGE_rtl8822be-firmware=y
```

`openmanet_setup.sh:279-288` concatenates `boards/common/*` then `boards/<board>/*`
into `.config` and kconfig takes the last occurrence, so the board `=y` overrides the
shared `=m`. `kmod-rtw88`, `kmod-rtw88-usb`, `kmod-rtw88-8822b` are `HIDDEN:=1` and
resolve through DEPENDS; `rtl8822be-firmware` is named explicitly because it is
selectable and carries the blob. Confirmed with `make defconfig` that the whole chain
lands `=y` with nothing left at `=m`.

**Verified inside the built image:** `rtw88_core.ko`, `rtw88_usb.ko`, `rtw88_8822b.ko`,
`rtw88_8822bu.ko`, `/lib/firmware/rtw88/rtw8822b_fw.bin` (150,984 B), and the four
`/etc/modules.d/rtw88*` autoload entries. The driver requests exactly
`"rtw88/rtw8822b_fw.bin"` (`rtw8822b.c:2495`) — filename matches the installed path.

NOTE on how it loads: `CONFIG_MODULE_STRIPPED=y` is set tree-wide, so shipped modules
carry no `alias=usb:v0BDApB812` entries and there is no udev alias-based demand load.
That is normal here — the proven-working `mm6108_sdio.ko` has zero aliases too. The
load path is `/etc/modules.d/rtw88-8822bu` -> kmodloader at boot -> the driver
registers with USB core -> USB core binds by the in-driver id_table whenever the
adapter is present, plugged before or after boot. Functionally this is still
flash -> boot -> plug -> interface appears.
