# PR #46 Audit — "Rpi 5 BCM2712 & Heltec HC01P Support"

Audited against local tree `C:\AI-Projects\OpenMANET-Pi5\firmware`, branch `pi5-wm6108-port`, HEAD `365b276`.
PR head fetched locally as ref `pr46` (`git fetch origin pull/46/head:pr46`). **Nothing was merged or checked out.**

Raw diff saved to scratchpad: `pr46.diff` / `pr46.patch`
(`https://patch-diff.githubusercontent.com/raw/OpenMANET/firmware/pull/46.diff`).

---

## 1. PR status

| Field | Value |
|---|---|
| Number / Title | #46 — "Rpi 5 BCM2712 & Heltec HC01P Support" |
| Author | `andrewsuggs465` |
| State | **OPEN** (not merged, not draft) |
| Base branch | `OpenMANET:24.10` |
| Head branch | `andrewsuggs465:rpi5-support` |
| Head commit | `19f0eea2aa4bf780300b4f5a6be8008e97ab6067` ("Merge branch '24.10' into rpi5-support") |
| Created | 2026-04-01 |
| Last updated | 2026-08-09 |
| Commits | 10 (9 real + 1 merge) |
| Diffstat | 32 files changed, +606 / -28 |
| `mergeable` | **false** — `mergeable_state: "dirty"` (real conflicts against 24.10 tip) |
| Description body | **empty** (no PR description provided) |
| Labels | `core packages`, `GitHub/CI`, `target/bcm27xx`, `toolchain` |
| Reviews | None submitted. `coreywagehoft` requested as reviewer, **awaiting review**. 1 approval required. |

### Merge base
`git merge-base 365b276 pr46` = **`b2cc177`** ("bcm27xx: enable Raspberry Pi camera stack (#55)").
The PR's merge commit pulled in 24.10 only up to `b2cc177`. It therefore **predates**
`b5e1251` ("1.8.0 Release (#66)"), `9241a8d` and `365b276` — i.e. it predates the entire
1.8.0 board/config/kernel-patch rework that our tree is built on. This is the root cause
of most of the staleness below.

### Review comments (2, verbatim substance)
- **andrewsuggs465** (2026-04-02): "I forked the repo and the build worked. The previous build ... .patch file ..." + noted Heltec HC01P support added.
- **coreywagehoft** (2026-04-08): "@andrewsuggs465 do you also have a Seeed Studio board and Pi hat? An unknown here is if your changes to the linux patches would break the existing support for the Seeed Studio board and the Pi4"

**This concern was never answered.** It was partially addressed by the author in commit
`e2bf741` (split RP1 fragments into separate `-pi5` overlays instead of mutating the shared
Pi1-4 overlays) — that commit's message explicitly states the shared-overlay approach
"would break overlay application on Pi 3/4 and Seeed boards". The residual risk is now low
for the overlays, but no reviewer confirmation and no hardware validation exists.

### CI state (checks on head `19f0eea`, run 2026-08-09)

| Check | Conclusion |
|---|---|
| `Build ekh-bcm2710 / Build ekh-bcm2710` | **success** |
| `Build ekh-bcm2711 / Build ekh-bcm2711` | **success** |
| **`Build ekh-bcm2712 / Build ekh-bcm2712`** | **FAILURE** (annotation: "Process completed with exit code 2") |
| `Test Formalities / Test Formalities` | **FAILURE** (exit code 1) |
| `Build all affected Kernels / Check Kernel patches (bcm27xx, bcm2708) / Check Kernel patches` | **FAILURE** (exit code 1) |
| `Build all affected Kernels / Build Kernel with external toolchain (bcm27xx, bcm2708) / Build bcm27xx/bcm2708` | success |
| `Build all affected Kernels / .../ Check packages for bcm27xx/bcm2708` | failure |
| `Build all core packages ... (x86/64, malta/be)` build + check | failure |
| `Pull Request Labeler` | success |

**Bottom line: the PR's own Pi 5 (`ekh-bcm2712`) firmware build does not pass CI, and
the kernel-patch formality check fails.** GitHub does not expose the job logs anonymously,
so the exact failure reason could not be retrieved. Do not treat any part of this PR as
build-verified.

---

## 2. File-by-file change list (32 files)

### CI / workflows (4)
| File | Change |
|---|---|
| `.github/workflows/build-pr-bcm2712.yml` | **new** — PR-triggered build job calling `build-firmware.yml` with `board: ekh-bcm2712 / target: bcm27xx / subtarget: bcm2712 / description: "Raspberry Pi 5"`; path filter mirrors `build-pr-bcm2711.yml`. |
| `.github/workflows/build-release.yml` | Adds a `build-ekh-bcm2712` release job (`releasepackages: true`, `cpu_arch: aarch64_cortex-a76`) and inserts it into the `needs:` list of `publish-packages` and `release`. |
| `.github/workflows/formal.yml` | Adds `pull-requests: write` to the workflow `permissions:` block. |
| `.github/workflows/github-release.yml` | **deleted** (legacy `softprops/action-gh-release` draft-release workflow). |

### Board configs (14)
| File | Change |
|---|---|
| `boards/ekh-bcm2710/target_diffconfig` | +1 line: `CONFIG_TARGET_DEVICE_bcm27xx_bcm2710_DEVICE_bcm2710_ht-hc01p-spi=y` |
| `boards/ekh-bcm2711/target_diffconfig` | +1 line: `CONFIG_TARGET_DEVICE_bcm27xx_bcm2711_DEVICE_bcm2711_ht-hc01p-spi=y` |
| `boards/ekh-bcm2712/{camera,cameraapp,dppqrcode,languages,morseguide,prplmesh,rangetest,spi,usb,utils,video,wireshark}_diffconfig` | **12 new symlinks** (mode 120000) to `../common_extras/<name>_diffconfig` — identical pattern to `boards/ekh-bcm2711/`. |
| `boards/ekh-bcm2712/target_diffconfig` | **new**, 36 lines — the Pi 5 board profile (see §3 for detail). |

### New package (2)
| File | Change |
|---|---|
| `package/utils/persistent-vars-storage-bcm2712/Makefile` | **new** — in-tree OpenWrt package, `PROVIDES:=persistent-vars-storage`, `DEPENDS:= +bcm27xx-userland @TARGET_bcm27xx_bcm2712`, installs one shell script. |
| `package/utils/persistent-vars-storage-bcm2712/files/sbin/persistent_vars_storage.sh` | **new**, 59 lines — `READ`/`READALL` via `vcgencmd bootloader_config`; `WRITE`/`ERASE` return "isn't implemented on bcm2712, yet" + exit 1. |

### Target base-files (2)
| File | Change |
|---|---|
| `target/linux/bcm27xx/base-files/etc/board.d/01_leds` | Adds `bcm2710,ht-hc01p-spi`, `bcm2711,ht-hc01p-spi`, `bcm2712,ht-hc01p-spi` to the HaLow-activity-LED case. |
| `target/linux/bcm27xx/base-files/lib/preinit/05_set_preinit_iface_brcm2708` | Adds the same three Heltec board names to the eth0 preinit case. |

### Image generation (6)
| File | Change |
|---|---|
| `target/linux/bcm27xx/image/Makefile` | +115 lines: new `Build/boot-rpi5-morse` recipe; new `Device/morse_rpi5_base`; new devices `bcm2712_mm6108-spi`, `bcm2712_mm8108-spi`, `bcm2712_mm6108-sdio`, `bcm2712_mm8108-sdio`, `bcm2712_ht-hc01p-spi`, `bcm2711_ht-hc01p-spi`, `bcm2710_ht-hc01p-spi`. |
| `target/linux/bcm27xx/image/boards/rpi5/distroconfig.txt` | **new**, 28 lines — Pi 5 base `distroconfig.txt` (`[pi5] dtoverlay=dwc2,dr_mode=host`, `disable_overscan`, `gpu_mem_*=128`, `uart_enable=1`, `dtparam=act_led_trigger=none`, `dtoverlay=ramoops`, `camera_auto_detect=1`). |
| `.../rpi5/distroconfig-mm610x-spi.txt` | **new** — `dtparam=spi=on` + `dtoverlay=mm610x-spi-pi5` |
| `.../rpi5/distroconfig-mm810x-spi.txt` | **new** — `dtparam=spi=on` + `dtoverlay=mm810x-spi-pi5` |
| `.../rpi5/distroconfig-mm610x-sdio.txt` | **new** — `dtoverlay=sdio,poll_once=on`, `dtparam=sdio_overclock=42`, `dtoverlay=mm_wlan-pi5` |
| `.../rpi5/distroconfig-mm810x-sdio.txt` | **new** — byte-identical to the mm610x-sdio file |

### Kernel patches (3)
| File | Change |
|---|---|
| `target/linux/bcm27xx/patches-6.6/990-0001-arm64-dts-add-morse-gpio-line-names.patch` | **new** — renames `&rp1_gpio` `gpio-line-names` in `arch/arm64/boot/dts/broadcom/bcm2712-rpi-5-b.dts`: GPIO5→`MM_IRQ`, GPIO17→`MM_RESET`, GPIO23→`MM_WAKE`, GPIO24→`MM_BUSY`. |
| `target/linux/bcm27xx/patches-6.6/991-0008-dt-overlays-morse-add-rpi5-overlay-variants.patch` | **new**, 212 lines — creates three new overlay sources: `mm610x-spi-pi5-overlay.dts`, `mm810x-spi-pi5-overlay.dts`, `mm_wlan-pi5-overlay.dts`, targeting `&rp1_spi0` / `&rp1_mmc0` / `&rp1_gpio`, `compatible = "brcm,bcm2712"`. |
| `target/linux/bcm27xx/patches-6.6/991-dt-overlays-build-morse-overlays.patch` | Registers `mm610x-spi-pi5.dtbo`, `mm810x-spi-pi5.dtbo`, `mm_wlan-pi5.dtbo` in `arch/arm/boot/dts/overlays/Makefile`. |

### Net-zero commits (present in history, not in the final diff)
- `1e6e7e8` "fix 991-0007 spi patch hunk offset (revert 521 to 568)" — reverted by later work.
- `d566640` "drop start4/fixup4 firmware from Pi 5 boot partition" — removes a `Build/boot-2712` recipe that an earlier PR commit had added. Net effect on the tree is nil, but the **reasoning is valuable and correct**: BCM2712 does not use the VPU `start*.elf` / `fixup*.dat` boot model; the EEPROM bootloader loads the kernel directly.
- `e2bf741` "split RPi5 overlay fragments into separate -pi5 overlays" — restores `991-0001` and `991-0003` to their Pi1-4-only form (undoing the change coreywagehoft flagged as risky) and moves the RP1 work into the new `991-0008`.

---

## 3. Classification

### REUSE (take substantially as-is)

| Item | Reason |
|---|---|
| `.github/workflows/build-pr-bcm2712.yml` | Matches our current `build-firmware.yml` `workflow_call` input contract (`board`/`target`/`subtarget`/`description`) exactly; path filter identical in shape to `build-pr-bcm2711.yml`. Drop-in. |
| `boards/ekh-bcm2712/*_diffconfig` (12 symlinks) | Pure symlinks into `boards/common_extras/`; identical to `boards/ekh-bcm2711/`. No risk. |
| `target/linux/bcm27xx/image/boards/rpi5/distroconfig-mm610x-spi.txt` | 2 lines, exactly the pattern used by `boards/ekh01/`. Our production SPI path. |
| `Build/boot-rpi5-morse` in `image/Makefile` | Line-for-line the `Build/boot-ekh01` idiom retargeted at `boards/rpi5/`. The `sysinfo` overlay it relies on (`992-0001`) uses `target-path = "/"`, so it has no label dependency and works on BCM2712. |
| The `Build/boot-2712` **removal** rationale (commit `d566640`) | Technically correct for BCM2712. Our tree never had `Build/boot-2712`, so this is a "do not add it" instruction rather than a patch. |
| `991-dt-overlays-build-morse-overlays.patch` **content** (the three `*-pi5.dtbo` lines) | Correct registration. Confirmed `CONFIG_ARCH_BCM2835=y` in `target/linux/bcm27xx/bcm2712/config-6.6:5`, so the `dtbo-$(CONFIG_ARCH_BCM2835)` list does get built for bcm2712. **But the hunk header must be re-based — see MODIFY.** |
| `991-0008` `mm610x-spi-pi5-overlay.dts` / `mm810x-spi-pi5-overlay.dts` GPIO map | Verified against our `991-0003-dt-overlays-morse-add-spi-overlay-fragment.patch`: reset=GPIO17, power=GPIO23+GPIO24, spi-irq=GPIO5, `cs-gpios = <… 8 1>`, `spi-max-frequency = <50000000>`, `compatible = "morse,mm610x-spi"`. **Identical wiring** — a faithful RP1 translation of the Seeed WM1302 / Wio-WM6108 pinout we already ship on Pi 4. This is the single most valuable artifact in the PR. |
| Separate-`-pi5`-overlay **architecture decision** | Correct and important: the RPi firmware overlay loader rejects an entire overlay if any fragment's target label is unresolvable, so `&rp1_spi0`/`&rp1_gpio` fragments must not be merged into the shared `mm610x-spi` overlay. This is exactly what keeps Pi 3/4 + Seeed working. |

### MODIFY (idea is right, code is stale or conflicts)

| Item | Reason |
|---|---|
| `boards/ekh-bcm2712/target_diffconfig` | Written against pre-1.8.0 package naming. Concretely wrong symbols: `CONFIG_PACKAGE_morse-fw-6108`, `morse-fw-6108-tlm`, `morse-fw-8108-tlm`, `morse-fw-8108-flm` (our tree uses `mm6108-firmware` / `mm8108-firmware`); `CONFIG_PACKAGE_kmod-video-codec-bcm2835` (our tree's package is **`kmod-codec-bcm2835`** — see `target/linux/bcm27xx/modules/video.mk:44`); `morse-board-config-hotplug-model`, `luci-app-ekhwizards`, `morsectrl` are unreferenced by any current board. Also **missing** everything our `boards/ekh-bcm2711/target_diffconfig` now depends on: `CONFIG_TARGET_PER_DEVICE_ROOTFS=y`, `CONFIG_PACKAGE_kmod-mm6108=y` / `kmod-mm8108=y` / `mm6108-firmware=y` / `mm8108-firmware=y`, and the per-device `CONFIG_TARGET_DEVICE_PACKAGES_…="-kmod-mm8108 -mm8108-firmware -wpad-basic-mbedtls"` exclusion lists. Rewrite from `boards/ekh-bcm2711/target_diffconfig`, not from this file. |
| `.github/workflows/build-release.yml` | Correct intent (`cpu_arch: aarch64_cortex-a76` matches `target/linux/bcm27xx/bcm2712/target.mk` `CPU_TYPE:=cortex-a76`), but **conflicts**: our `needs:` lists are now `[build-ekh-bcm2711, build-ekh-bcm2710, build-halowlink2, build-hd01-v2, build-venice]`. Re-apply by hand. |
| `991-dt-overlays-build-morse-overlays.patch` | **Hard conflict.** PR version's hunk header is `@@ -170,7 +170,13 @@`; our tree's is `@@ -184,7 +184,10 @@` and additionally carries a second hunk adding `raven.dtbo`. Do not take the PR's file — add only the three `*-pi5.dtbo` lines into our existing patch. |
| `Device/morse_rpi5_base` in `image/Makefile` | Structure is right, package list is stale/wrong: `DEVICE_PACKAGES += kmod-morse netifd-morse morse-fw-6108 morse-fw-8108 kmod-spi-dw kmod-spi-dw-mmio kmod-i2c-designware-platform`. Our Pi 4 devices use `kmod-mm6108 netifd-morse mm6108-firmware`, and Morse state the mm6108/mm8108 drivers conflict when loaded together — shipping both firmwares in one image contradicts our current per-device-rootfs exclusion scheme. Also inherits `$(Device/rpi-5)` whose `DEVICE_PACKAGES :=` includes **`wpad-basic-mbedtls`**, which `boards/ekh-bcm2711/target_diffconfig` explicitly strips because it clashes with `wpad-openssl` (both ship `/usr/sbin/hostapd`). `morse_rpi5_base` has no equivalent removal → **image assembly conflict is likely**. |
| `target/linux/bcm27xx/image/boards/rpi5/distroconfig.txt` | Take, but review three lines: `[pi5] dtoverlay=dwc2,dr_mode=host` (dwc2 is the Pi4/CM4 OTG controller; Pi 5 USB is XHCI behind RP1 — this is at best a no-op), `gpu_mem_256/512/1024` (ignored on BCM2712, harmless noise), `dtoverlay=ramoops` (our tree also ships `ramoops-pi4.dtbo`; the correct variant for BCM2712 memory layout is unverified). |
| `01_leds` and `05_set_preinit_iface_brcm2708` | The PR only adds `bcm2710,ht-hc01p-spi` / `bcm2711,ht-hc01p-spi` / `bcm2712,ht-hc01p-spi`. It **never adds `bcm2712,mm6108-spi`** (or `mm8108`/`sdio`), which is what `SYSINFO_BOARD_NAME` produces for our production device. So the Morse-on-Pi5 images get no HaLow LED trigger and no preinit interface. Take the *shape*, substitute our board names. (Note: our tree also lacks `bcm2711,mm6108-spi` in these files — a pre-existing inconsistency, out of scope.) |
| `990-0001-arm64-dts-add-morse-gpio-line-names.patch` | Content verified as plausible: our `950-0870-ARM-dts-Standardise-downstream-Pi-GPIO-pin-names.patch` rewrites the `&rp1_gpio` `gpio-line-names` block in `bcm2712-rpi-5-b.dts` at `@@ -678,34 +678,34 @@` producing exactly the `"GPIO2", // GPIO2` context this patch expects, and `990-` sorts after `950-`, so ordering is right. Two things to fix: (a) the patch carries a **fabricated author/hash** (`Developer <dev@example.com>`, `d4a7c7f5…`) — replace with a real header before committing; (b) rename to fit our series (our Pi 4 equivalent is `991-0005-dt-overlays-morse-add-HAT-gpios-to-gpio-line-names.patch`). |
| `package/utils/persistent-vars-storage-bcm2712/*` | Useful — `boards/ekh-bcm2711/target_diffconfig` already sets `CONFIG_PACKAGE_persistent-vars-storage-bcm2711=y` (that package comes from the `morse` feed, pinned at `fc332b01`), so a bcm2712 equivalent is genuinely needed. But the Makefile has broken indentation (mixed 8-space/2-space in `define Package/…`), no `PKG_VERSION`, an empty `Build/Compile`, and `WRITE`/`ERASE` unimplemented — so first-boot key provisioning will fail. Check whether the morse feed already ships a bcm2712 variant before adding an in-tree duplicate that `PROVIDES:=persistent-vars-storage`. |

### NEEDS TESTING (take, but unverifiable without hardware / a build)

| Item | Reason |
|---|---|
| `mm610x-spi-pi5-overlay.dts` pinctrl label references | Uses `&rp1_spi0_gpio9` and `&rp1_spi0_cs_gpio7`. These labels must exist in the RPi 6.6 `rp1.dtsi`/`bcm2712-rpi.dtsi` or the overlay silently fails to load at boot. Not verifiable from this tree (kernel source is not unpacked). Verify after the first `make target/linux/prepare`. |
| Missing `spidev@0` / `spidev@1` disable nodes in the `-pi5` SPI overlays | The Pi 1-4 `mm610x-spi-overlay.dts` explicitly sets `spidev0`/`spidev1` to `status = "disabled"` so they do not fight the Morse node for CE0. The `-pi5` variants omit this. If the BCM2712 base DT enables `spidev@0` under `&rp1_spi0`, CE0 will be double-claimed and probe will fail. **Likely first-boot failure mode — check this first.** |
| `mm_wlan-pi5-overlay.dts` | Mixes `&rp1_gpio` (fragment@2) with plain `&gpio` (reset/power-gpios in fragment@0), and targets `&rp1_sdio_clk0`, whose existence is unverified. SDIO is **not** our production path (we are SPI), so this is low priority — but if it fails to build, the whole `991-0008` patch fails. |
| `990-0001` patch application | The `Check Kernel patches (bcm27xx, bcm2708)` CI job **fails** on the PR head. The two new kernel patches are the prime suspects. Must be re-refreshed (`make target/linux/refresh`) after rebasing onto our tree. |
| `persistent_vars_storage.sh` on Pi 5 | Depends on `vcgencmd bootloader_config` working on BCM2712 via `bcm27xx-userland`. Unverified. |
| Whole `ekh-bcm2712` build | The PR's own CI build of this board **failed**. Assume nothing builds until we build it ourselves. |

### DO NOT USE

| Item | Reason |
|---|---|
| `boards/ekh-bcm2710/target_diffconfig` change | Adds a Heltec HC01P image to the Pi 3 board. Out of scope, extra build time, unrelated hardware. |
| `boards/ekh-bcm2711/target_diffconfig` change | Same, on Pi 4 — and it conflicts with our substantially rewritten 1.8.0 version of that file. Taking it risks disturbing known-good Pi 4 support. |
| `Device/bcm2710_ht-hc01p-spi`, `Device/bcm2711_ht-hc01p-spi`, `Device/bcm2712_ht-hc01p-spi` in `image/Makefile` | Heltec HC01P is explicitly not our production target (CLAUDE.md). Each adds a full image build. |
| `bcm2710,ht-hc01p-spi` / `bcm2711,ht-hc01p-spi` / `bcm2712,ht-hc01p-spi` entries in `01_leds` and `05_set_preinit_iface_brcm2708` | Heltec-only board names. |
| `.github/workflows/formal.yml` (`pull-requests: write`) | Unrelated CI permission widening with no stated justification. Not part of the port. |
| Deletion of `.github/workflows/github-release.yml` | Unrelated CI housekeeping; deleting a release workflow is a consequential change with no bearing on the Pi 5 port. |
| `Device/bcm2712_mm8108-sdio` / `bcm2712_mm6108-sdio` (initially) | Not our production path; the `mm_wlan-pi5` overlay is the least-verified part of the PR. Defer until SPI works. Note `distroconfig-mm810x-sdio.txt` and `distroconfig-mm610x-sdio.txt` are byte-identical (both say `mm_wlan-pi5`), which is almost certainly a copy-paste bug for the MM8108 case. |
| `boards/ekh-bcm2712/target_diffconfig` **as a file** | See MODIFY — rewrite from `ekh-bcm2711`, do not cherry-pick this file. |

---

## 4. GENERIC BCM2712 / RP1 / Pi 5 vs HELTEC HC01P-specific

### What is already in our tree at `365b276` (so PR #46 adds nothing here)
- `target/linux/bcm27xx/bcm2712/config-6.6` (16 KB) and `target/linux/bcm27xx/bcm2712/target.mk`
  (`ARCH:=aarch64`, `SUBTARGET:=bcm2712`, `CPU_TYPE:=cortex-a76`, `FEATURES+=pci pcie`).
- Generic `define Device/rpi-5` + `ifeq ($(SUBTARGET),bcm2712) TARGET_DEVICES += rpi-5` in
  `target/linux/bcm27xx/image/Makefile:231-257`, with `KERNEL_IMG := kernel_2712.img` and
  the full `bcm2712-rpi-5-b` / `cm5` DTS list.
- All RP1 kernel plumbing enabled: `CONFIG_MFD_RP1=y`, `CONFIG_PINCTRL_RP1=y`,
  `CONFIG_PINCTRL_BCM2712=y`, `CONFIG_COMMON_CLK_RP1=y`, `CONFIG_COMMON_CLK_RP1_SDIO=y`,
  `CONFIG_PWM_RP1=y`, `CONFIG_ARCH_BCM2835=y` (all in `bcm27xx/bcm2712/config-6.6`).
- All the RPi downstream BCM2712/RP1 kernel patches (`950-0526-mfd-Add-rp1-driver.patch`,
  `950-0530-pinctrl-Add-rp1-driver.patch`, `950-0521-PCI-brcmstb-Add-BCM2712-support.patch`,
  `950-0870-ARM-dts-Standardise-downstream-Pi-GPIO-pin-names.patch`, etc.).

**So PR #46 contributes zero generic BCM2712 enablement.** Its entire generic value is the
*OpenMANET/Morse layer on top of* the already-present BCM2712 target.

### GENERIC Pi 5 / RP1 work in PR #46 (relevant to us)
1. `991-0008` — the three RP1 overlay sources (`mm610x-spi-pi5`, `mm810x-spi-pi5`, `mm_wlan-pi5`). **The core deliverable.**
2. `991-dt-overlays-build-morse-overlays.patch` — registering those `.dtbo`s.
3. `990-0001` — `MM_IRQ`/`MM_RESET`/`MM_WAKE`/`MM_BUSY` gpio-line-names on `bcm2712-rpi-5-b.dts` (needed by Morse userspace `chipreset.sh` / `morse_cli.sh`).
4. `Build/boot-rpi5-morse` + `boards/rpi5/distroconfig*.txt` — the sysinfo/overlay boot plumbing.
5. `Device/morse_rpi5_base` + `Device/bcm2712_mm6108-spi` / `bcm2712_mm8108-spi`.
6. `boards/ekh-bcm2712/` board directory (12 symlinks + target_diffconfig).
7. `package/utils/persistent-vars-storage-bcm2712/`.
8. `.github/workflows/build-pr-bcm2712.yml` + the `build-release.yml` job.
9. The `Build/boot-2712` removal rationale (no start4/fixup4 on BCM2712).
10. The "separate `-pi5` overlays, never shared fragments" design constraint.

### HELTEC HC01P-specific work (discard)
1. `Device/bcm2710_ht-hc01p-spi`, `Device/bcm2711_ht-hc01p-spi`, `Device/bcm2712_ht-hc01p-spi`.
2. `boards/ekh-bcm2710/target_diffconfig` and `boards/ekh-bcm2711/target_diffconfig` one-liners.
3. `bcm27{10,11,12},ht-hc01p-spi` entries in `01_leds` and `05_set_preinit_iface_brcm2708`.
4. `CONFIG_TARGET_DEVICE_bcm27xx_bcm2712_DEVICE_bcm2712_ht-hc01p-spi=y` in the Pi 5 board config.

Note the Heltec devices carry `DEVICE_PACKAGES += -morse-fw-8108 -morse-fw-8108-tlm -morse-fw-8108-flm`
and `DISTROCONFIG_EXTRA := mm610x-spi` — i.e. HC01P is an MM6108 SPI part reusing the same
overlay as ours. So dropping the Heltec devices costs us nothing on the RF/SPI path.

### Neither (unrelated CI churn — discard)
`.github/workflows/formal.yml` permission change; deletion of `.github/workflows/github-release.yml`.

---

## 5. Regression risk to Pi 4 (bcm2711) and to the WM1302 / Wio-WM6108 / MM6108 SPI path

### Confirmed merge conflicts against `365b276`
`git merge-tree` reports conflicts in:
- `.github/workflows/build-release.yml` (our `needs:` lists differ)
- `boards/ekh-bcm2710/target_diffconfig`
- `boards/ekh-bcm2711/target_diffconfig`
- `target/linux/bcm27xx/base-files/etc/board.d/01_leds`
- `target/linux/bcm27xx/image/Makefile` (`<<<<<<<` around our `Device/bcm2711_raven`)
- `target/linux/bcm27xx/patches-6.6/991-dt-overlays-build-morse-overlays.patch`

A straight `git merge pr46` would leave the tree broken. **Cherry-pick by hand only.**

### Real Pi 4 / WM1302 regression risks

| Risk | Severity | Detail |
|---|---|---|
| **Overwriting `boards/ekh-bcm2711/target_diffconfig`** | HIGH | Our 1.8.0 version encodes the whole `CONFIG_TARGET_PER_DEVICE_ROOTFS` + `kmod-mm6108`/`kmod-mm8108` =y + per-device `-kmod-mm8108 -mm8108-firmware -wpad-basic-mbedtls` scheme. Accepting the PR's version of this file (or resolving the conflict toward "theirs") would silently demote the whole Morse userspace to `=m` and ship LuCI with no theme — the exact failure the file's own comments warn about. **Never take this file.** |
| **Overwriting `991-dt-overlays-build-morse-overlays.patch`** | HIGH | The PR's version drops our `raven.dtbo` registration and uses a stale `@@ -170` hunk offset. Taking "theirs" breaks the Raven board and makes the patch fail to apply. Merge the three `-pi5` lines into *our* file instead. |
| **Overwriting `target/linux/bcm27xx/image/Makefile` hunks** | HIGH | Conflict sits directly on our `Device/bcm2711_raven` block. A careless resolution deletes the Raven Pi 4 device. |
| Mutating the shared `991-0001` / `991-0003` overlays | **RESOLVED in the PR** | Earlier PR commits added RP1 fragments into `mm_wlan-overlay.dts` / `mm610x-spi-overlay.dts` and widened their `compatible` to include `"brcm,bcm2712"` — exactly what coreywagehoft warned about, and it would have broken overlay loading on Pi 3/4 + Seeed. Commit `e2bf741` reverted this. **Verify these two patch files are byte-identical to ours before taking anything**, and never resurrect the earlier approach. |
| `990-0001` touching `bcm2712-rpi-5-b.dts` | LOW for Pi 4 | Different DTS file from the Pi 4 `991-0005` patch. No interaction. But the `Check Kernel patches` CI failure means patch health is unproven for *all* bcm27xx subtargets, since the series is shared. |
| Heltec entries in `01_leds` / `05_set_preinit_iface_brcm2708` | LOW | Purely additive `case` arms; they cannot change Pi 4 behaviour. But taking the PR's whole file would revert our recently added `morse,mm6108-ekh01-sdio` / `morse,mm8108-ekh01-sdio` arms in `01_leds`. |
| Heltec devices on bcm2710/bcm2711 | LOW (functional), MEDIUM (CI time) | Adds two more Pi 3/Pi 4 images to every build. |
| `wpad-basic-mbedtls` inherited from `Device/rpi-5` | MEDIUM (Pi 5 only) | `Device/morse_rpi5_base` never strips it; the Pi 4 profile documents that it clashes with `wpad-openssl`. Will likely break Pi 5 image assembly, not Pi 4. |
| Feed drift | MEDIUM | The PR predates our `feeds.conf.default` pins (`morse` @ `fc332b01`, `openmanet` @ `4736e447`, `luci` @ `53e65158`). Package names it references (`morse-fw-6108`, `luci-app-ekhwizards`, `morse-board-config-hotplug-model`) are not used by any board in our tree; if they no longer exist in the pinned feeds, kconfig will drop them silently and the resulting image will be missing pieces without any build error. |

---

## 6. Recommended cherry-pick plan (highest value first)

1. **`991-0008` overlay patch** — the RP1 SPI overlay for MM6108. Rename to fit our series
   (e.g. `991-0008-dt-overlays-morse-add-rpi5-overlay-variants.patch` is fine), then
   **add the missing `spidev0`/`spidev1` `status = "disabled"` nodes** to match our
   `991-0003`, and drop `mm_wlan-pi5` (SDIO) for now unless it builds cleanly.
2. **Three `*-pi5.dtbo` lines** hand-merged into *our* `991-dt-overlays-build-morse-overlays.patch`.
3. **`990-0001`** gpio-line-names for `bcm2712-rpi-5-b.dts`, with a real patch header, renumbered
   consistently with our `991-0005`.
4. **`Build/boot-rpi5-morse`** + `boards/rpi5/distroconfig.txt` +
   `boards/rpi5/distroconfig-mm610x-spi.txt` (review the `dwc2` / `ramoops` lines).
5. **`Device/morse_rpi5_base` + `Device/bcm2712_mm6108-spi`**, rewritten with our package
   naming (`kmod-mm6108`, `mm6108-firmware`, `netifd-morse`) and a `-wpad-basic-mbedtls` exclusion.
6. **`boards/ekh-bcm2712/`** — 12 symlinks verbatim; `target_diffconfig` written fresh from
   `boards/ekh-bcm2711/target_diffconfig`.
7. **Board names** `bcm2712,mm6108-spi` (and `mm8108`) added to `01_leds`, `02_network`, and
   `05_set_preinit_iface_brcm2708` — the PR forgot these entirely.
8. **`.github/workflows/build-pr-bcm2712.yml`** verbatim; `build-release.yml` job added by hand.
9. **`persistent-vars-storage-bcm2712`** only after checking the pinned `morse` feed for an
   existing bcm2712 variant.
10. Everything Heltec, and both unrelated CI workflow changes: **skip**.
