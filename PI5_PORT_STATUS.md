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
| `ekh-bcm2712` (Pi 5) | `make -j20` exit 0, no errors. `openmanet-1.8.0-rpi5-mm6108-spi-squashfs-sysupgrade.img.gz`, 53,560,864 bytes, sha256 `2d0764b55c05cb899d51b0d037032bf3e89aefc9ced59c17a8bcff8b11567c1f` (rebuilt at `6ea1380`; PRODUCTION; all earlier images superseded). Log `~/logs/build-2712-v4.log`. |
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

**Active (2026-08-30, physical only):** GNSS validation is complete on the software
side but no satellite fix has been obtained — the receiver reports zero satellites
tracked. This requires an antenna placement / seating action, not a code change.
See "WM1302 GNSS validation" at the end of this file.

No software blockers. The §14 blocker (the 802.11s mesh SAE passphrase) was resolved
by the owner on 2026-08-30, and Phase 1 has been re-verified end to end on the
current image —
Pi4<->Pi5 HaLow mesh, BATMAN_V, 4/4 ping at 3.950 ms average, with the RTL8822BU
still at SuperSpeed simultaneously. See "§14 Phase 1 regression — COMPLETE,
HARDWARE VERIFIED" at the end of this file.

One open observation, not a blocker: a single unexplained reboot during verification
with no recorded cause. Details in that section.

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
sha256 2d0764b55c05cb899d51b0d037032bf3e89aefc9ced59c17a8bcff8b11567c1f
53,560,864 bytes
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

## USB Wi-Fi AC AP-mode failure — investigation and partial fix (commit `e89a5a7`)

With the driver installed (`a7ed9bc`) the adapter binds and loads firmware
("Firmware version 27.2.0, H2C version 13"), but AP mode fails with
`write RF mode table fail` / `WARNING ... rtw8822b.c:824`, then the netdev
unregisters and hostapd reports `No such device`.

### What the source establishes

- **`rtw8822b.c:824`** is a 100-iteration RF LUT readback poll in
  `rtw8822b_config_trx_mode()`: it writes LUT address `0x00001` and reads RF reg
  `0x33` back expecting `0x00001`. `rf_base_addr = {0x2800, 0x2c00}` with
  `.read_rf = rtw_phy_read_rf` (direct window), so on USB that readback is a
  vendor control read at MAC address `0x28CC`. On failure the function returns
  early, skipping LUT programming, `toggle_igi`, `set_channel_cca` and
  `set_channel_rfe`.
- **It is NOT AP-specific.** `config_trx_mode` <- `rtw8822b_phy_set_param()` <-
  `rtw_power_on()` (`main.c:1412`), i.e. device power-on, independent of
  interface mode. Channel / VHT80 / 5 GHz therefore cannot be the cause — the
  loop touches no channel state and runs before any channel is programmed.
- **RFE type is NOT the cause.** `config_trx_mode` has a separate guard at
  line 747 (`WARN(efuse->rfe_option >= ARRAY_SIZE(...))`) which did not fire.
- **No competing driver.** The image ships only `rtw88_{core,usb,8822b,8822bu}`;
  `rtl8812au-ct` is `=m` and absent (it is the 8812AU, `0bda:8812`, anyway).
- **AP is supported on USB by design.** `main.c:2221` sets
  `sta_mode_only = (hci.type == RTW_HCI_TYPE_SDIO)` — only SDIO is STA-only.
- **The netdev unregister is a re-enumeration.** `usb_reset_device()` occurs
  once, in `rtw_usb_disconnect()` (`usb.c:1233`), corroborated by the phy index
  advancing 3 -> 5. hostapd's `No such device` is a consequence, not a cause.
  THIS REMAINS UNEXPLAINED.

### The fix that was applied

`patches/rtl/052-wifi-rtw88-Fix-unaligned-32-bit-access-to-REG_TXPAUSE.patch`.

`REG_TXPAUSE` is `0x0522` and one byte wide, but `rtw_core_enable_beacon()`
used `rtw_write32_set/clr()` on it. Those are read-modify-write helpers, so a
32-bit access spans `0x0522..0x0525` and rewrites `REG_RD_CTRL` (`0x0524`) as
collateral on every beacon enable/disable. `rtw_core_enable_beacon()` is
AP-only (`if (!rtwdev->ap_active) return;`) and is called from the scan /
channel-switch C2H handler in `fw.c` — exactly the HT_SCAN phase where the
observed failure occurs.

Backported from OpenWrt backports 6.12.96 and verified, not assumed: the
6.12.96 tarball was downloaded (its sha256 matches the upstream openwrt-24.10
`PKG_HASH`) and `rtw_core_enable_beacon()` diffed; applying this patch yields a
function byte-identical to 6.12.96.

### The backports version bump was explicitly REJECTED

Research recommended bumping mac80211 6.12.61 -> 6.12.96 for a commit claimed to
"Avoid WARNING in rtw8822b_config_trx_mode()". Verified against the actual
6.12.96 source: **that WARN is still present, same line 824, same text.** The
bump would not fix it. It also rewrites **37 of 86 `net/mac80211`** and **19 of
43 `net/wireless`** source files — precisely the files this tree's ~30 Morse
S1G/HaLow patches modify — putting the hardware-verified Phase 1 MM6108 mesh at
risk for no gain. The mac80211 pin is deliberate (see `86bb3cc revert pkg
version`, `aad60e4 revert OpenWRT to 24.10.2`).

### Pi 4 regression for `e89a5a7` — clean

`patches/rtl/` is shared, so `ekh-bcm2711` was rebuilt and compared by content.
Only 19 files differ: 18 `usr/lib/opkg/info/*.control` differing solely in
`SourceDateEpoch:`, plus the known LuCI cache-busting token in `header.ut`.
**`cfg80211.ko`, `mac80211.ko`, `brcmfmac.ko`, `mm6108_sdio.ko` and
`batman-adv.ko` are all byte-identical.** Phase 1 is provably unaffected.

### Still open

The `052` fix is correct on its own merits but is NOT proven to cure the
reported failure. Two things remain unexplained: whether the `rtw8822b.c:824`
WARN is fatal or merely cosmetic, and why the device re-enumerates. The next
step is a STA-mode test on hardware — if the WARN fires in STA mode too it is a
power-on fault unrelated to AP, and `052` will not be sufficient.

## USB Wi-Fi AC: SuperSpeed failure isolated (open; diagnostic build `c94fb65`)

Hardware result: RTL8822BU `0bda:b812` **scans fine at USB 2 High Speed (480)**
and **fails at USB 3 SuperSpeed (5000)** on BOTH Pi 5 USB3 ports, in STA mode
(so not AP-specific). Failure is `failed to do USB write, ret=-19` (-ENODEV) +
`failed to send h2c packet`, then an xHCI port reset ~1.7 s later and firmware
reload. No over-current / undervoltage logged. `-ENODEV` means the USB core
already considered the device gone, so the device leaves the bus FIRST and the
write failures and reset are consequences.

### The SuperSpeed delta is one register

Excluded from source: the probe-time USB2->USB3 mode switch (runs once, returns
early when already SuperSpeed); `rtw_usb_dynamic_rx_agg_v2()` (has the
SuperSpeed 0x6/0x1a branch but is selected only for 8821A/8812A — 8822B uses
`_v1`, which is NOT speed dependent); and patch `048` (only added 8812A, 8822B
was already covered).

What remains, and it is the ONLY speed-dependent setting for this chip:

```
rtw_usb_init_burst_pkt_len()   usb.c:799
  USB_SPEED_SUPER -> BIT_DMA_BURST_SIZE_1024   (REG_RXDMA_MODE 0x0290, bits 5:4 = 0)
  USB_SPEED_HIGH  -> BIT_DMA_BURST_SIZE_512    (bits 5:4 = 1)
```

### Why no root-cause evidence appears in dmesg

`rtw_usb_read_port_complete()` swallows every RX urb error — `-EPIPE`,
`-EPROTO`, `-EOVERFLOW` (xHCI babble) and others all hit a bare `break` with NO
log line — and `rtw_usb_rx_resubmit()` is called only on the success path and
from `rtw_usb_setup_rx()`. So `RTW_USB_RXCB_NUM` (4) transient RX errors
permanently retire RX with nothing in dmesg. Verified unchanged in backports
6.12.96.

### Diagnostic build `c94fb65` — `patches/rtl/053`, REVERT WHEN DONE

1. `rtw88_usb.rx_burst_size` (int, 0644, default -1 = existing behaviour).
   Confirmed present in the shipped module (`parmtype=rx_burst_size:int`).
2. Logs the otherwise-silent RX urb errors with status and `actual_length`.
   Logging only — resubmit behaviour deliberately NOT changed.

The controlled experiment (HS-vs-SS varies link speed AND burst size together;
this varies the burst size alone, at SuperSpeed):

```sh
echo 512 > /sys/module/rtw88_usb/parameters/rx_burst_size   # then replug
iw phy<N> interface add sta0 type managed && ip link set sta0 up
iw dev sta0 scan | head
dmesg | grep -iE "rtw|rx urb error|usb|reset"
```

Stable at 512/SuperSpeed => the 1024-byte RX DMA burst is implicated and link
speed is exonerated; the real fix is then a targeted quirk plus an upstream
report. Still failing => burst size exonerated, and the new `rx urb error`
lines should expose the first fault rather than its aftermath.

USB 2.0 High Speed is a WORKAROUND ONLY, not the intended final state — this is
a USB3-capable adapter and is meant to run at USB 3.

### Pi 4 regression for `c94fb65` — clean

`cfg80211.ko`, `mac80211.ko`, `mm6108_sdio.ko`, `batman-adv.ko` and
`brcmfmac.ko` all byte-identical to the previous build; the only differences
are opkg `SourceDateEpoch` metadata and the LuCI cache-busting token.

## USB3 SuperSpeed: candidate fix backported (commit `14caf12`)

`patches/rtl/054-wifi-rtw88-Add-USB-PHY-configuration.patch` — upstream
`5b1b9545262b5126a3c2776e7e64ff29765cbe6e`, first released in v6.14, not in the
6.12 stable series and therefore absent from the `backports-6.12.61` pin.

Its upstream commit message describes our exact symptom: an RTL8822BU
(TP-Link Archer T3U — same chip as `0bda:b812`) "in USB 3 mode was randomly
disconnecting from USB", with repeated SuperSpeed disconnect / re-enumerate
cycles.

Verified before backporting, not assumed:

- fetched from git.kernel.org and applies to this tree with offsets only;
- every prerequisite already exists in 6.12.61 — `struct rtw_intf_phy_para`,
  `chip->intf_table`, the `usb3_para` member, and `usb3_param_8822b[]` in
  `rtw8822b.c` — so it is a pure addition to `usb.c` and `reg.h`;
- the whole `patches/rtl/` series (052, 053, 054 included) applies cleanly to a
  pristine `backports-6.12.61` extraction with zero failures.

### CUT-GATED — candidate, not a confirmed cure

`usb3_param_8822b[]` holds exactly one real entry,
`{0x0001, 0xA841, RTW_IP_SEL_PHY, RTW_INTF_PHY_CUT_D}`, and
`rtw_usb_phy_cfg()` skips entries whose `cut_mask` does not match
`BIT(rtwdev->hal.cut_version)`. `RTW_INTF_PHY_CUT_D` is `BIT(3)`, so this only
acts on a cut-D part (`cut_version == 3`). On any other cut it is a no-op and
will NOT fix the disconnects.

`patches/rtl/053` was extended to log this at probe:

```
DIAG: usb speed=%d cut_version=%u rxdma=0x%02x
```

First check after flashing is therefore `dmesg | grep "DIAG: usb speed"`:

- `cut_version=3` → the PHY tuning is active; retry the SuperSpeed scan. If
  stable, that is the fix and `053` can be reverted.
- anything else → `054` is inert for this part; fall back to the
  `rx_burst_size=512` controlled experiment in `053`.

### Ruled out along the way

`xhci-hcd.quirks=` cannot disable USB3 LPM — it is applied as `quirks |= …`
(OR-only), so a bit can be added but never cleared.

### Pi 4 regression for `14caf12` — clean

`cfg80211.ko`, `mac80211.ko`, `mm6108_sdio.ko`, `batman-adv.ko`,
`brcmfmac.ko` all byte-identical; no non-metadata differences at all.

## USB3: SuperSpeed + forced 512 result — analysis (no rebuild)

Hardware: `DIAG: usb speed=5 cut_version=3 rxdma=0x1e`, twice, during the scan.
Device stayed on the bus, scan completed and returned a real BSS, but RX was
badly corrupted (`unused phy status page`, `Rate marked as a VHT rate but data
is invalid`, `invalid wl info c2h length`, repeated `mac80211/rx.c:808` and
`rx.c:5445` WARNINGs, `rtw_rx_query_rx_desc` traces from the rtw88_usb RX wq).

### 1. What `rxdma=0x1e` confirms

`REG_RXDMA_MODE` base is `BIT_DMA_BURST_CNT | BIT_DMA_MODE` = 0x0E, with burst
size in bits 5:4. Decoded: 1024 -> 0x0e, **512 -> 0x1e**, 64 -> 0x2e. So the
override took effect and the part really ran at SuperSpeed with a 512-byte RX
DMA burst. `cut_version=3` is `RTW_INTF_PHY_CUT_D` (`BIT(3)`), so **patch 054's
USB PHY tuning does apply to this adapter** — it is not a no-op here.

### 2. Why SuperSpeed + 512 survives but corrupts RX

512 at SuperSpeed is wrong by construction, and the corruption is the expected
consequence rather than a new bug:

- SuperSpeed bulk endpoints have a fixed max packet size of 1024 bytes.
- `BIT_DMA_BURST_SIZE` controls how the chip pushes RX data into the USB FIFO.
  Forcing 512 makes it emit 512-byte chunks on a 1024-MPS endpoint.
- A bulk IN transfer terminates on any short packet, and the driver sets no
  `URB_SHORT_NOT_OK` on RX URBs (only TX uses `URB_ZERO_PACKET`).
- So every 512-byte burst ends the transfer early. The driver receives
  truncated fragments and parses a partial aggregated block as if complete —
  producing exactly the observed garbage descriptors and rate/PHY-status
  warnings.

Smaller per-transfer sizes also plainly avoid whatever overruns the link at
1024, which is why the device no longer disappears.

### 3. Buffer sizing / aggregation vs link stability

Not a buffer-size bug. `RTW_USB_MAX_RECVBUF_SZ` is 32768 and is identical at
both speeds; RX aggregation for 8822B is `_v1`, which is NOT speed dependent;
and the driver never reads the endpoint max packet size at all — it infers the
burst purely from link speed. Mainline `rtw_usb_init_burst_pkt_len()` is
byte-identical to ours, so upstream still regards 1024 as correct at
SuperSpeed. The evidence points at the DMA-burst / USB-packet-size interaction
at 1024, not at RX buffer sizing.

### 4. Later upstream RX fixes (verified against git.kernel.org)

- `aa7d92e83811a0b557b75f7a0ce85315f4358bf2` "Add more validation for the RX
  descriptor" — discards frames whose PHY status size is not 0 or 4, whose size
  is <= 4 or > 11454, or whose rate exceeds 4SS MCS9. This would SUPPRESS the
  warnings seen at 512. **Deliberately NOT applied**: it masks the diagnostic
  signal we are currently relying on. Revisit as hardening once the cause is
  settled.
- `6b964941bbfe6e0f18b1a5e008486dbb62df440a` "usb: fix memory leaks on USB
  write failures" — relevant, since the failing path leaks on every `-ENODEV`
  write and we hit that repeatedly. Candidate for later.
- Mainline burst-size selection is unchanged, so there is no upstream fix that
  alters the 1024 choice.

### 5. Next step — no rebuild required

The 512 run changed TWO variables at once: patch 054 became active AND the
burst was forced. **SuperSpeed at the correct 1024 burst with 054 active has
never been tested** — the earlier `-ENODEV` failures were all on the pre-054
image. Forcing 512 may simply have masked the fix.

```sh
echo -1 > /sys/module/rtw88_usb/parameters/rx_burst_size   # restore default
# replug the adapter (read at probe), then rescan
dmesg | grep -E "DIAG: usb speed|rx urb error|reset SuperSpeed"
```

Expect `rxdma=0x0e`. If the scan is then clean, 054 is the fix and both the
burst override and 053 as a whole can be reverted. If it disconnects again,
054 alone is insufficient and the DMA-burst/MPS interaction at 1024 is the
real fault.

## USB 3 SuperSpeed: VALIDATED — production build `80c8396`

**Patch `054` is the fix.** Validated on the physical Pi 5 + RTL8822BU
(`0bda:b812`), blue USB 3 port, SuperSpeed, `cut_version=3` (cut D), default
burst (`rxdma=0x0e`):

- STA: active scan completed normally, no RX corruption, no reset, no
  disconnect, no `-ENODEV`, no failed writes or H2C.
- AP: `phy7-ap0` created, joined `br-lan`, forwarding, SSID up.
- Real client: associated/authenticated/authorized, 66,905 B RX / 46,979 B TX,
  **0 TX retries, 0 TX failed**, 351 Mbit/s VHT-MCS 4 80 MHz NSS 2.

### Production patch set (all upstream, no local invention)

| Patch | Upstream | Purpose |
|---|---|---|
| `052` | 6.12.96 | `REG_TXPAUSE` unaligned 32-bit RMW clobbering `REG_RD_CTRL` |
| `054` | `5b1b9545262b` (v6.14) | **USB PHY configuration — the USB 3 fix** |
| `055` | `44d1f624bbdd` | `rtw8822b_config_trx_mode()` WARNING |

`053` was **removed in full**. It was diagnostic-only, and all of it had served
its purpose: the `rx_burst_size` override (forcing 512 at SuperSpeed is wrong by
construction and caused the RX corruption), the `DIAG` probe log (answered:
cut D), and the RX urb error logging (would spam on every normal unplug/ifdown,
since it logged `-ENODEV`/`-ESHUTDOWN`/`-ENOENT` too).

Verified in the shipped module: `rx_burst_size` is **gone** (only
`switch_usb_mode` remains).

### `rtw8822b.c:824` "write RF mode table fail" — fixed by `055`

`rtw8822b_set_antenna()` can be called from userspace while the chip is powered
off; reading RF registers then returns an unexpected value and the readback
poll exhausts. `/lib/netifd/wireless/mac80211.sh:1249` runs
`iw phy $phy set antenna` during bring-up, which is exactly that trigger.
`055` guards the call with `RTW_FLAG_POWERON`. Pure guard — it touches no USB,
RX or PHY path, so it cannot affect the validated SuperSpeed behaviour. The
warning was already non-fatal (AP and client traffic worked through it).

### Radio-path bookkeeping — NO source change needed

Traced the full chain:

- At High Speed the driver **does not register a phy** — `rtw_usb_probe()`
  skips `rtw_register_hw()` when the USB2->USB3 mode switch fires
  ("Not a fail, but we do need to skip rtw_register_hw"). So no HS-path radio
  can ever be created.
- `/etc/hotplug.d/ieee80211/10-wifi-detect` runs `/sbin/wifi config` on phy add;
  that runs `wifi-detect.uc`, which rewrites `/etc/board.json`'s `wlan` section
  (pruning stale entries), then `mac80211.uc`, which creates a radio for any
  phy not already matched.
- `mac80211.uc radio_exists()` matches on `macaddr` FIRST, then `phy`, then a
  `path` suffix. netifd's `find_phy()` supports `phy`, `path` and `macaddr`.

So on a clean flash exactly ONE phy appears — at the SuperSpeed path — and
exactly one radio is created with the correct path. **The stale `radio2` and the
accumulated disabled radios were artifacts of this session's testing** (two
different blue ports = two different USB paths, plus the pre-054 image's
repeated re-enumeration), not a boot-time defect.

Residual exposure, which is upstream OpenWrt behaviour and identical on Pi 4:
nothing ever deletes stale `wifi-device` sections, so moving the dongle to a
different physical USB port creates a new radio and leaves the old one behind.

Narrowest hardening IF that is ever wanted — one UCI option, no source change,
no script:

```sh
uci set wireless.<radio>.macaddr="$(cat /sys/class/ieee80211/<phy>/macaddress)"
uci -q delete wireless.<radio>.path
uci commit wireless
```

`radio_exists()` checks `macaddr` before `path`, and `find_phy()` falls back to
it, so the radio then survives any re-enumeration or port change. A cleanup
script was deliberately NOT added — that would be redesigning networking.

### Pi 4 regression for `80c8396` — clean

`cfg80211.ko`, `mac80211.ko`, `mm6108_sdio.ko`, `batman-adv.ko`,
`brcmfmac.ko` all byte-identical; no non-metadata differences at all.

## USB Wi-Fi boot-order race — FIXED (commit `6ea1380`)

Symptom, reproduced after `rm /etc/config/wireless; wifi config` and a FULL
reboot (so not stale UCI/netifd state): `radio1` (RTL8822BU) never comes up on
boot —

```
netifd: radio1: Phy not found / Could not find PHY for device 'radio1'
netifd: Wireless device 'radio1' set retry=0 ... setup failed, retry=0
morse-wifi-re-enable: Ignoring Wi-Fi phy3 hotplug add as network.wireless
                      status does not have a path for /devices/.../usb4/4-1/...
```

### Mechanism (source-proven)

1. The RTL8822BU probes on USB 2. `rtw_usb_probe()` **skips
   `rtw_register_hw()`** when the USB2->USB3 switch fires, so no phy exists yet.
2. It re-enumerates at SuperSpeed (`usb4/4-1`) and becomes `phy3`.
3. netifd has already tried `radio1` and failed. `/lib/netifd/wireless/
   mac80211.sh:1206` does `find_phy || { ...; wireless_set_retry 0; }`.
4. That sets `retry_setup_failed`, and netifd's `wireless_device_set_up()`
   returns early **forever** while it is set (`wireless.c:539`). Only
   `wireless_device_set_down()` clears it (`wireless.c:718`) — i.e. the *down*
   half of `wifi up`.
5. The `ieee80211` hotplug add for `phy3` then arrives, but the only installed
   re-enable handler skipped every non-s1g radio, so `radio1` was never retried.

### Why the fix is in hotplug, not netifd

`retry=0` is deliberate upstream behaviour — retrying a *missing* phy on a timer
achieves nothing, so mac80211.sh tells netifd not to spend retries and leaves
recovery to hotplug. Raising netifd's retry count would fight that design and
amount to a blind timer. Stock OpenWrt has **no** generic late-phy handler:
`/etc/hotplug.d/ieee80211/10-wifi-detect` only runs `wifi config`, which writes
UCI and never brings a radio up.

### The fix

`patches/ekh-bcm2712/0011` lifts the s1g-only gate in
`15-morse-wifi-re-enable`. That restriction was never technical — its own
comment read *"This code should work in the generic case, but currently it's in
netifd-morse so let's only try to deal with Morse wifi chips."*

Safeguards verified intact (in source AND in the shipped image):

- the radio is acted on only when its configured path matches the event's
  `DEVPATH`, so one hotplug event still affects at most one radio;
- `pending` still prevents bouncing a radio mid-reconfiguration;
- `autostart` still protects a radio brought down with `wifi down` — netifd
  clears `autostart` **only** in `wireless_device_set_down()`, never on a failed
  setup, so it survives the failure as 1 but a manual `wifi down` sets it to 0;
- netifd-not-up early exit, migration path and single-match `exit 0` unchanged.

s1g/HaLow behaviour is unchanged — the gate only ever *excluded* non-s1g. No
loop risk: the handler fires on phy add/remove, and `wifi up` creates netdevs,
not phys.

### Pi 4 regression for `6ea1380` — clean, with board-scoping proven

The Pi 4 image still contains the original gate at line 86
(`if [ "$band" != "s1g" ]; then`), confirming the patch is genuinely
board-scoped. `cfg80211.ko`, `mac80211.ko`, `mm6108_sdio.ko`, `batman-adv.ko`
and `brcmfmac.ko` are byte-identical, with no non-metadata differences at all.

## UART console automation (2026-08-29)

The Pi 5 is now operated directly over its USB-TTL UART console. Helper:

```
C:\AI-Projects\OpenMANET-Pi5\.ai-workflow\pi5-uart.ps1
```

Port **COM4**, identified by FTDI VID `0403`/PID `6001` (the other two COM ports
are an LG display and a Sennheiser headset interface). 115200 8N1,
`Handshake=None`, DTR and RTS explicitly de-asserted so the adapter cannot hold
the Pi in reset. Uses .NET `System.IO.Ports` via PowerShell — real Python is not
installed on this workstation (Store stub only), and this needs no install and
no network. Transcripts append to `.ai-workflow\pi5-uart.log`, `-Label` adds a
dated rotated copy. Secrets (PSK/key/passphrase/token/PEM) are redacted from
durable logs and reports.

Actions: `Probe`, `Sync`, `Run`, `Batch`, `Capture`, `WaitForShell`, `Reboot`.

**Command completion is not prompt-based.** Each command is wrapped in unique
BEGIN/END markers carrying `$?`. First attempt failed and the failure was
instructive: the console line-wraps the *echo* of the command at 80 columns,
which split `__OM_END_` from `1495851E__RC=` and broke marker counting. The
markers are now assembled by the shell from two variables
(`_A=__OM; _B=<id>; echo "${_A}_BEG_${_B}"`), so the literal marker text never
appears in the command line and therefore never in its echo — each marker
appears exactly once, in real output, at the start of its own short line.

## Reserved-page/beacon failure — live hardware evidence (2026-08-29)

Captured over UART, uptime ~3780 s, RTL8822BU AP on phy5, channel 36 VHT80:

- **7 × `error beacon valid`** at 231, 1703, 2004, 2251, 2322, 2912, 3159 s.
  Intervals 1472 / 301 / 247 / 71 / 590 / 247 s — **irregular and NOT
  accelerating**.
- 6 × `failed to download beacon` vs 7 × `error beacon valid`: the event at
  2251 s produced only `error beacon valid` + `failed to download drv rsvd
  page`, so different reserved-page entries fail on different occasions.
- **The client rode through it.** Connected 2166 s continuously (associated at
  boottime 1671 s), i.e. across 6 of the 7 events: authorized/authenticated/
  associated yes, rx 396,916 B / 5,695 pkt, tx 249,761 B / 2,393 pkt,
  tx retries 0, tx failed 2, rx drop misc 0, rx 702 Mbit/s VHT-MCS8 80 MHz
  NSS2, DTIM 2.
- No correlation with anything in `logread` at those timestamps.

### Trigger identified in source

`mac80211.c:429-432` — `BSS_CHANGED_BEACON` -> `rtw_fw_download_rsvd_page()`.
In AP mode mac80211 raises that whenever beacon content changes (TIM, ERP/
protection, HT/VHT operation elements as clients come and go), which is
event-driven, not periodic — matching the irregular intervals exactly. It does
not require deep LPS (`disable_lps_deep=N` is set, but the `LPS_DEEP_MODE_PG`
rsvd-page path in `ps.c` is a separate, non-periodic trigger).

### Which candidate cause this is — and is not

This is **not** the TX page-pool exhaustion path (Mehmet Fide's acked-but-
unapplied bmc/DTIM series). That signature is a monotonic drain to zero free
pages ending in a terminal state where "nothing can join until the device is
rebooted". Ours is sporadic over 52 minutes, self-recovering, with a client
holding a 2166 s session straight through it. Live evidence, not inference.

It IS consistent with the async-URB race that lwfinger PR #455 describes.

### Decision: do NOT apply PR #455 (unchanged, now with hardware backing)

- Never submitted upstream despite the maintainer asking twice; still open.
- Its own author flagged that blocking 5 s under `rtwdev->mutex` stalls the
  whole driver, suggested 500 ms, and the committed patch still uses 5000 ms.
- One reporter still lost the AP with it applied, plus a new `-110`/-ETIMEDOUT
  failure mode from the new wait.
- It needs hand-porting: it calls `rtw_tx_fill_tx_desc(..., struct rtw_tx_desc *)`
  but our 6.12.61 takes `struct sk_buff *`, and this kernel builds
  `-Werror=incompatible-pointer-types`, so it is a hard build failure as-is.
- **And the symptom is demonstrably non-fatal on our hardware.**

REVISIT IF: beaconing actually stops, clients cannot associate, or the event
rate starts accelerating rather than staying sporadic. Also revisit if the fix
is accepted upstream, in which case take the upstream version.

NOTE: `85bf3041a0ea` ("Set `pkt_info.ls` for the reserved page", v6.13) is
already in our tree via OpenWrt `patches/rtl/034` — verified, no action needed.

### Unrelated observation

`logread` is currently full of `alfred: can't get interface: No such device`
and `openmanetd: batctl mj/gwj: exit status 1`, because `bat0` does not exist —
the HaLow mesh is un-provisioned after the earlier `rm /etc/config/wireless`.
Expected; it is restored as part of the final Phase 1 regression.

---

## §14 Phase 1 regression over UART (2026-08-29/30) — PARTIAL, blocked on credential

Performed entirely over the 3-pin JST-SH UART console (`.ai-workflow/pi5-uart.ps1`,
COM4). Device: `BCM2712-3f76`, OpenMANET 24.10 1.8.0, kernel 6.6.138.

### MM6108 / HaLow radio path — REGRESSION-CLEAN

Restored via the image's own shipped one-shot default script, NOT by hand-written
config: `sh /rom/etc/uci-defaults/99_morse_radio_defaults` (the copy in `/etc` had
already been consumed and deleted on first boot, which is why `radio2` had lost
country/channel/BCF after the earlier `/etc/config/wireless` regeneration).

Restored values: `channel=42`, `country=US`, `bcf=bcf_fgh100mhaamd.bin`,
`enable_ext_xtal_init=1`, `enable_ps=0`, `enable_twt=0`.

Bring-up verified end to end:

- `morse_spi spi0.0` probes; `morse_of_probe` reads GPIO config from DT; GPIO reset OK
- firmware `morse/mm6108.bin`, 468304 B, crc32 `0xbe7b5c8f`
- **US BCF** `morse/bcf_fgh100mhaamd.bin`, 1251 B, crc32 `0x941b2a82`
- driver modparams confirm `country: US`, `enable_ext_xtal_init: Y`
- `hostapd_s1g`: `morse_set_interface: s1g_chan_center=42, ht_center_chan=159`
- `wlh0` created, `AP-ENABLED`, forwarding on `br-lan`

So RP1 -> SPI -> DW AXI DMA -> MM6108 -> firmware -> BCF -> `wlh0` is intact on the
current image. Driver version `0-rel_mm6108_2_0_1_2026_Jun_11`.

Regdb corroborates the validated tuple — `/usr/share/morse-regdb/channels.csv`:
`US,,True,2,42,2,69,923.0,100.0,100.0,USA,36.0,False,0.0,0.0,0.0,159`.
The `map_5g_chan=159` column is why `iw` displays `wlh0` as "channel 157 (5785 MHz)":
that is the 5 GHz shadow mapping, not a misconfiguration.

### RTL8822BU / USB3 — REGRESSION-CLEAN

- `/sys/bus/usb/devices/4-1/speed` = **5000** — patch 054 holds across reboots
- AP `phy5-ap0` up, ch36 VHT80; client connected 3350 s at 292.5 Mbit/s
  VHT-MCS7 NSS1, **0 tx retries**, 2 tx failed, -27 dBm
- only the known benign `error beacon valid` / `failed to download drv rsvd page`
  pair since the dmesg clear — matches the non-fatal pattern recorded in `8bd27bb`;
  client session unaffected
- boot-order recovery (patch 0011) confirmed present on-device: the hotplug handler
  carries the comment "The s1g-only restriction that used to be here has been lifted
  for this board."
- batman-adv `2025.4-openwrt-2` loaded; `batctl`, `alfred`, and `batadv.sh` /
  `batadv_hardif.sh` / `batadv_vlan.sh` all present

### Provisioning path — investigated, and the naive plan is WRONG

`openmanet.setup.v1.SetupService/ApplySetup` (openmanetd, ports 8081/8087) is NOT
usable for a restore, on two independent grounds:

1. it is the **first-boot** wizard — `admin_password` is a required field
   (`min_len 8`) and it flips `auth.enable`, i.e. it changes credentials;
2. `/etc/openmanetd/config.yml` has no `setup:` key, so `setup.enabled` defaults
   false and the call returns `CodeUnavailable`.

There is no server-side backend for the LuCI EKH wizard either — `/usr/libexec/rpcd/`
holds only `switch_wifi_driver`; the wizard is pure client-side JS writing UCI through
LuCI's generic rpc.

**Critical finding: running the LuCI EKH wizard on this box would damage working
configuration and weaken the firewall.** `resetUci()` / `resetUciNetworkTopology()`
(`tools/morse/wizard.js:412-542`) run unconditionally on wizard *entry*, before any
user choice, and:

- delete **every** `config rule` in `firewall` (wizard.js:494-496) and replace them
  with the wizard's own 13
- set the **wan** zone `input/output/forward=ACCEPT` (wizard.js:364-366) — the stock
  default is REJECT — and strip `masq`/`mtu_fix` from all zones
- set `enabled=0` on every existing forwarding, including stock `lan -> wan`
- set `ignore=1` on every `dhcp` pool (wizard.js:512)
- delete every bridge device section including `br-lan`, and unset `.device` on every
  interface, leaving `lan` deviceless (wizard.js:517-521, 540)
- strip `wireless.radio1` to a 14-option whitelist and `default_radio1` to
  `network device key encryption mode ssid mesh_id`, dropping everything else
- set `disabled=1` on **every** wifi-iface (wizard.js:463)
- silently convert an `encryption='none'` AP to `psk2` (the encryption widget offers
  only psk2/sae-mixed/sae, and `ui.Select` ignores an out-of-list cfgvalue), then
  refuse to advance without a passphrase
- delete outright any wifi-iface not named `default_<device>`
  (`removeExtraWifiIfaces`, wizard.js:390-398)

Ground truth for all of the above: `openmanetd-1.3.10/testfixtures/setup-wizard/`
contains a captured real before/after UCI dump of this exact wizard run on a
Pi 4 + MM6108-over-SPI.

**The transformation IS fully reproducible as a plain `uci` shell sequence** — nothing
on the Mesh Point path depends on a live scan, iwinfo probe, or DOM state. Only three
values are random, and they are free choices, not derived:

| value | source | space |
|---|---|---|
| `network.ahwlan.ipaddr` | `uci.js:549` | `10.41.254.0`-`10.41.254.253` (3rd octet hard-coded 254) |
| `dhcp.ahwlan.start` | `uci.js:136` | `255 + 16k`, k in [0,14] |
| `br-ahwlan` `macaddr` | `uci.js:22-25` | `F2:` + 5 random octets |

Two source defects noted: `uci.js:526` writes `mesh11sd.mesh_params.nolearn`, but the
shipped config and `morse.sh` use `mesh_nolearn` — the wizard's option is dead. And
`device_mode_meshpoint` is forced to `bridge` in the OpenMANET fork
(`meshwizard.js:485-486`, `readonly = true`), so "Mesh Point" always yields the bridge
topology regardless of the none/extender selection.

### Blocker

**The 802.11s mesh SAE passphrase is not recoverable and must match the Pi 4.**
`/etc/config/wireless` was regenerated during USB testing, so the passphrase used in
the validated Phase 1 run is gone. Guessing or inventing it is forbidden by the
operator rules, and a mismatch means the mesh simply will not associate.

Secondary: the intended topology merges `lan` and `ahwlan` into a single
`10.41.0.0/16` network (`br-ahwlan` carries `eth0` + `bat0`, `lan` goes deviceless).
The current box has `lan` at `10.41.254.1/16` AND would get `ahwlan` at
`10.41.254.x/16` — a subnet collision — so a mesh-only partial replay is not clean
either. Restoring the validated topology necessarily moves the RTL8822BU AP onto
`ahwlan`, which disconnects the client currently associated at `10.41.0.225`.

### Exact next action

Owner supplies the mesh SAE passphrase (or authorises a specific one to be set on
BOTH nodes), and confirms the Pi 4 is powered on and provisioned as Mesh Gate with
`mesh_id=openmanet`, channel 42, US. Then apply the wizard's Mesh Point transformation
as a scripted `uci` sequence over UART with the three random values pinned, reload,
and complete the regression: `iw dev wlh0 station dump`, `batctl if/n/o`, `bat0` state,
`openmanetd` status, and an end-to-end ping to the Pi 4 across `bat0`.

Full config backup already on the device in `/root/cfgbak/` (`network`, `wireless`,
`firewall`, `dhcp`, `mesh11sd`, plus `.pre-wizard` copies). The UART console is
independent of networking, so no network change can lock us out.

---

## §14 Phase 1 regression — COMPLETE, HARDWARE VERIFIED (2026-08-30)

The blocker above is resolved. The owner supplied the existing lab mesh SAE
passphrase (not recorded here) and confirmed the Pi 4 was powered on and still
carrying its verified Mesh Gate configuration.

### What was applied

The LuCI EKH wizard's **Mesh Point / bridge** transformation, applied as a scripted
`uci` sequence over UART from the source analysis above — the destructive global
resets (`resetUci` / `resetUciNetworkTopology`) were deliberately NOT replayed, so
the firewall rule set, the wan zone's REJECT posture, and the stock forwardings were
all left intact.

Applied: `default_radio2` -> `mode=mesh`, `mesh_id=openmanet`, `encryption=sae`,
`beacon_int=1000`, `wds=1`, `network=batmesh0`; `bat0` (`proto=batadv`,
`routing_algo=BATMAN_V`, `gw_mode=client`, bridge_loop_avoidance/bonding/
aggregated_ogms/fragmentation/DAT/multicast_mode/network_coding, `orig_interval=1000`,
`hop_penalty=30`); `batmesh0`/`batmesh1` (`proto=batadv_hardif`, `master=bat0`);
`br-lan` replaced by `br-ahwlan` (bridge, ports `eth0` + `bat0`); `ahwlan`
(`proto=static`, `/16`, `ip6assign=64`, `ip6ifaceid=eui64`, `ip6class=local`);
`lan` left **deviceless** so there is no `10.41.0.0/16` collision; firewall zone
`ahwlan` (ACCEPT/ACCEPT/ACCEPT, `mtu_fix=1`) plus one `ahwlan -> lan` forwarding;
`dhcp.ahwlan` server pool with `dhcp.lan.ignore=1`; `mesh11sd.mesh_params`
`mesh_fwding=0`, `mesh_nolearn=1`, `mesh_gate_announcements=0` (Mesh Point);
`default_radio1` (RTL8822BU AP) moved onto `ahwlan`.

**Note — `mesh_nolearn` not `nolearn`.** The wizard writes the dead `nolearn` option
(uci.js:526); the shipped mesh11sd config and `morse.sh` use `mesh_nolearn`. The
working name was used deliberately.

### Result — matches the 2026-08-28 Phase 1 result

| Check | Phase 1 (2026-08-28) | §14 re-verification |
|---|---|---|
| `wlh0` type | mesh point | **mesh point** |
| Peer | `a8:dd:9f:4d:c0:e3` | **`a8:dd:9f:4d:c0:e3`** (same unit) |
| mesh plink | ESTAB | **ESTAB** |
| authorized / authenticated / associated | yes | **yes / yes / yes** |
| signal | ~ -46 dBm | **-35 to -38 dBm** |
| expected throughput | ~7.52 Mbps | **7.52 Mbps** |
| `batctl if` | wlh0 active | **wlh0: active** |
| routing algo | BATMAN_V | **BATMAN_V** (`batctl ra` confirms) |
| BATMAN neighbour / originator | via `wlh0`, ~7.2 | **via `wlh0`, 7.2 / 7.1** |
| end-to-end ping | 4/4, 0%, 3.620/3.892/4.105 ms | **4/4, 0%, 3.854/3.950/4.075 ms** |

Additional evidence beyond the original run:

- `batctl gwl` lists the Pi 4 as an actual **gateway** (10.0/2.0 MBit), and the
  station dump reports `mesh connected to gate: yes` — the Mesh Gate role is live,
  not merely configured.
- After a reboot the mesh re-formed **automatically** at boottime 24.567 s with no
  operator action, and BATMAN resolved the peer by name as `RAPTOR-01_wlh0` (alfred
  name resolution working). Post-reboot steady-state ping: **10/10, 0% loss,
  3.886/4.828/10.316 ms**. This is a stronger result than the original Phase 1 run,
  which was provisioned live rather than cold-booted.
- The chronic `alfred: can't get interface: No such device` log spam is **gone**
  (count 0) now that `bat0` exists. `batctl gwj: exit status 254` appears only twice
  at boot, before the mesh forms.

### Both subsystems healthy simultaneously

- **MM6108:** `wlh0` mesh point, US / channel 42 / `bcf_fgh100mhaamd.bin`,
  peer ESTAB, BATMAN_V, `bat0` UP/LOWER_UP under `br-ahwlan`, openmanetd running.
- **RTL8822BU:** still **SuperSpeed 5000** after the reboot, AP up and `forwarding`
  in `br-ahwlan`. Only the known benign `error beacon valid` / `failed to download
  drv rsvd page` set, consistent with `8bd27bb`. The single
  `write register 0xc4 failed with -71` at t=13 s is on the **High Speed** instance
  (`3-1:1.0`) before SuperSpeed re-enumeration as `4-1:1.0` — the documented
  boot-order behaviour that patch 0011 handles.
- `br-ahwlan` ports: `eth0` (NO-CARRIER, no cable), `bat0` forwarding,
  `phy3-ap0` forwarding.

### Two behaviours worth recording

**openmanetd rewrites the `ahwlan` address.** The pinned `10.41.254.15` was replaced
with `10.41.183.117` and written back into UCI by openmanetd's
`AddressReservationWorker`. This is the product's own designed mesh-wide address
reservation and supersedes the wizard's random seed IP — it is not a defect, and it
means the wizard's `getRandomIpaddr` value is only a starting point.

**One unexplained reboot.** The unit rebooted once during verification. There is no
recorded cause: `/sys/fs/pstore` is empty, and there is no under-voltage, OOM, panic,
hung-task or RCU stall in the log; 7.9 GB of 8 GB RAM was free. It occurred while a
254-process concurrent ping sweep (run to discover the Pi 4's address) overlapped a
netifd reconfiguration, and the kernel cmdline carries `reboot=w` with procd's
watchdog active, so the most plausible explanation is a watchdog reset from a
transient stall induced by that diagnostic sweep. **This is unproven.** It did not
recur, and the box came back with the full mesh working unattended. Watch for it;
do not treat it as explained.

### Blocker

None. Phase 1 is re-verified end to end on the current image.

---

## WM1302 GNSS validation (2026-08-30) — SOFTWARE PATH VERIFIED, fix pending antenna

Performed over UART on the current production image with the restored mesh topology
live. Patches `0007` and `0010` are both now exercised on Pi 5 hardware.

### Software chain — VERIFIED end to end

```
/dev/ttyAMA0 -> u-blox receiver -> gpsd -> openmanetd
```

- `/dev/ttyAMA0` present (204,64) and distinct from the `ttyAMA10` debug console
  (204,74) — no contention between the GPS UART and our console.
- `gpsd` running (pid 3216), `uci` device `/dev/ttyAMA0`, port 2947.
- GPSD `DEVICES` reports: `"driver":"u-blox"`, `"bps":9600`, `"parity":"N"`,
  `"stopbits":1`, `"native":1`, activated. Matches the previously established
  9600 8N1 u-blox result. `native:1` means gpsd successfully switched the receiver
  into binary mode, which requires the receiver to accept commands — so this is
  two-way communication, not passive listening.
- Live data flows at ~1 Hz: a 400-message capture over ~200 s contained 199 TPV and
  198 SKY reports with no dropouts.
- `openmanetd`: `INF gps Connected to GPSD address=localhost:2947`.

### Patch 0007 (chip/SPI-path-agnostic `gpsboard.init`) — VALIDATED

Boot log (`init-gps-device`):

```
GPS device: /dev/ttyAMA0
configuring GPS GPIOs (RST=25, WAKE=12)
pulsing GPS reset on GPIO25
GPIO25 (RST)     = ?
GPIO12 (WAKEUP) = ?
```

The proof is that `configuring GPS GPIOs` was reached at all. `check_morse_device`
suffix-matches `spi_master/spi0/spi0.0` and calls `exit 0` when it does not match;
the live path is
`platform/axi/1000120000.pcie/1f00050000.spi/spi_master/spi0/spi0.0`, which the old
BCM2711-literal comparison would have rejected, aborting the script before any GPIO
work. It did not abort.

`gpioinfo` confirms both lines are held as outputs with `consumer="gps-wm1302"` by
two live daemonised `gpioset` processes (pids 2017, 2020). The `?` readback is fully
explained by that ownership. **No source change made or warranted.**

**Accuracy note on the patch rationale.** The in-script comment argues that
`-c gpiochip0` is unsafe because "on BCM2712 the header pins live on RP1, which
probes from PCIe with .base = -1 and is not gpiochip0". On this kernel that specific
prediction does not hold — `gpiodetect` shows `gpiochip0 [pinctrl-rp1] (54 lines)`
with the brcmstb controllers at `gpiochip10..13`, so RP1 *is* gpiochip0 here and the
old assumption would have coincidentally worked. The `--by-name` approach remains the
correct fix regardless, because name resolution does not depend on probe/enumeration
order, but the comment's stated failure mode was not observed and should not be cited
as demonstrated.

### Patch 0010 (openmanetd GNSS capability) — VALIDATED

- `/tmp/sysinfo/board_name` = `bcm2712,mm6108-spi`; model `RPI RPI5-MM6108 (SPI)`.
- That exact string is present in the shipped `/usr/bin/openmanetd` binary
  (`board_type.go:10`, `BCM2712_MM6108_SPI`).
- `supported_features.go:39` lists `BCM2712_MM6108_SPI` in the `GNSSsupoorted()`
  true-case (upstream's spelling). Without patch 0010 the board would fall through
  to `default: return false`.
- **Functional proof:** `openmanet.go:86` gates GPS module creation on
  `cfg.GetEnableGNSS() && board.GNSSsupoorted()`, and the `gps` logger is created
  only inside that branch. The live `INF gps Connected to GPSD` line therefore
  cannot be emitted unless `GNSSsupoorted()` returned true on this board.
- openmanetd starts normally; zero "unsupported / unknown board" messages in the log.

### Satellite fix — NOT obtained; environmental, not software

199 of 199 TPV reports are `"mode":1` (no fix). More significantly, **none of the 198
SKY reports contained a `satellites` array at all**, and all DOP values are 0.00 —
the receiver is tracking zero satellites, not merely failing to resolve a fix.

This is category **A** (receiver and software functioning, no satellite signal), not
category B. The UART link, protocol negotiation, framing, and the full
gpsd -> openmanetd path are all demonstrably healthy; there is simply no GNSS signal
reaching the receiver.

Zero satellites *in view* over 200 s is a stronger symptom than a marginal indoor
fix attempt, where a few low-C/N0 satellites would normally still be listed. The
likely physical causes are the antenna not being seated in the WM1302's GNSS
connector (the HAT has separate LoRa and GNSS connectors), or the antenna having no
sky visibility at all. This cannot be distinguished from software:
`ubxtool` is not in the image, so UBX-MON-HW antenna status (OK/OPEN/SHORT) is not
readable, and `gpsmon` is a curses UI unsuitable for the serial console.

### Status summary

| Item | State |
|---|---|
| Software path (`ttyAMA0` -> u-blox -> gpsd -> openmanetd) | **VERIFIED** |
| Hardware receiver communication (two-way, 9600 8N1, binary mode) | **VERIFIED** |
| Patch 0007 chip/SPI-path independence | **VERIFIED on Pi 5** |
| Patch 0010 GNSS capability | **VERIFIED on Pi 5** |
| Satellite fix | **PENDING** — antenna placement / connection |

### Blocker

Physical only: the GNSS antenna needs clear sky visibility, and its seating in the
WM1302 GNSS connector should be confirmed while doing so. No software action remains.
