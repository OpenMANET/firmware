# WM6108 SPI reset — no-flash verification

Date: 2026-09-07. Branch: `fix/wm6108-spi-reset` in firmware and packages.
Scope: Seeed WM6108/WM1302 SPI on Pi 3B, Zero 2W, CM4 and Pi 4B.
No image has been flashed and no running node has been modified.

## Implementation

- BSP 1.0-r11 owns a boot-only helper and `/etc/wm6108-spi-reset.conf`.
- The extra reset ships disabled (`enabled=0`); the kernel's normal reset is
  unchanged. Hardware evidence is required before default enablement.
- One explicit marker in the WM6108 overlay opts the wiring profile in. The
  helper validates the base board, SPI0/CE0, GPIO provider and GPIO17 mapping.
- Missing/invalid/ambiguous configuration, missing GPIO controller, occupied
  GPIO, or an already loaded/bound driver cannot trigger a pulse. Runtime
  service starts/restarts are no-ops. A guard prevents repeated boot attempts.
- Physical low is followed by input within the same exclusive libgpiod request.
  Failure/signal cleanup is tested; there is no bus or module recovery path.
- A mandatory common firmware feed patch makes the old vendor reset entry point
  a no-op on bcm27xx, including calls from driver switching. Other targets keep
  the vendor implementation. Package install order no longer exposes the old
  MMC-unbind behavior on Pi when using this patched bundle.
- MM8108 SPI, USB and SDIO are not opted in. The CM4 MM8108 USB no-overlay
  distroconfig fix, onboard Wi-Fi configuration, and openmanetd are untouched.

## Sources and build inputs

- Firmware implementation: `50cceac62c96a6aa56cad8a2cf82f1595685bf98`, based on
  `5f5e20f0fcd45fc4de32eada539b46981f3a13f3`. Subsequent changes are tests/report
  only and do not change image runtime content.
- Packages pin: `74f9975c7642591bbe54ccae33f8cb9b51dabdb9` (local commit; publish
  the packages branch before expecting another machine to fetch this pin).
- Morse feed: `fc332b01aa2df952e057efe73763de3ff71cb3b0`, plus the tracked common
  feed patch; bundle release 3.
- Kernel 6.6.138; target GCC 13.3.0; libgpiod 2.1.3; libfdt 1.7.1.
- Raspberry Pi utils `dtmerge` revision
  `65bad738fb9b40d19659f210705fd629db4fc7b0`.
- Host ShellCheck 0.8.0; QEMU user-static 6.2. Tools were extracted under `/tmp`,
  not installed into the host system. Host fixtures use the system libfdt;
  the static ARM fixtures compile the target libfdt sources.
- Initial package tests used a generated BSP symlink to the packages working
  tree. The OpenMANET feed has since been fetched from that local repository and
  checked out at the exact new pin; the normal generated feed symlink is
  restored. Only the BSP changed relative to the previous pin. No remote branch
  has been pushed.

## Results

| Check | Status | Evidence / limit |
| --- | --- | --- |
| Native safety tests | PASS | 12 test groups, including all four identities, malformed DT/config, absent/ambiguous providers, transport exclusions, occupied line, bound driver, concurrency, signal and injected GPIO/timing/allocation failures; UBSan enabled |
| ARM64 safety tests | PASS | Same 12 groups executed under QEMU using a static AArch64 fixture binary and GPIO mock; no GPIO passthrough |
| Shell checks | PASS | BusyBox ash syntax and ShellCheck on the new init script; host common-patch script checked separately |
| Pi 3B effective DT | PASS | Actual base DTB merged with baseline/new WM6108 overlay; only opt-in differs; actual detector accepts new profile |
| Zero 2W effective DT | PASS | Same comparison and detector execution |
| CM4 effective DT | PASS | Same comparison, including unchanged unrelated/onboard Wi-Fi nodes |
| Pi 4B effective DT | PASS | Same comparison and detector execution |
| MM8108 SPI / unmarked / USB exclusions | PASS | Actual merged MM8108 DT and no-overlay base DT reject reset on all four boards; USB fragment still adds no overlays |
| SDIO exclusion | PASS (offline) | Non-SPI compatible and absent-marker fixtures skip; final SDIO image has no SPI overlay selection and retains the harmless vendor entry point |
| Mandatory feed patch | PASS | Applies cleanly, second application is a no-op, incompatible input fails closed |
| Package install/reinstall order | PASS (isolated harness) | Actual bundle install recipe and BSP postinst in temporary roots; patched vendor entry point remains harmless; non-Pi recipe unchanged |
| Cortex-A72 packages | PASS | BSP 1.0-r11 and patched morse-bundle 3 built using OpenWrt; package contents/control metadata inspected |
| Cortex-A53 helper/libraries | PASS (cross-build) | Helper linked against locally rebuilt A53 libgpiod/libfdt; not a complete bcm2710 package/image build |
| Production ELF loading | PASS | Packaged ARM64 binary loads target shared libraries under QEMU; no-argument invocation safely skips |
| Boot sequence | PASS (source/final-image inspection) | S09 before S10 normal kmodloader; Morse absent from the final images' modules-boot.d; not hardware timing proof |
| Full bcm2711 SPI/SDIO/USB images | PASS (build/inspection) | Full make exited 0; all three final FAT/squashfs images pass helper/default-off/service/library/vendor-noop/transport checks |
| CM4 onboard Wi-Fi / MM8108 USB contents | PASS (offline) | Final USB image retains the no-HaLow-overlay boot selection, brcmfmac driver, 43455 firmware and CM4 NVRAM alias; traffic remains untested |
| Full bcm2710 images | NOT RUN | CPU cross-build/emulation and both actual base DTBs are covered above |
| Complete opkg/sysupgrade migration | NOT RUN | Install recipe/postinst harness is not a full device package-manager or sysupgrade test |
| GPIO simulator / electrical behavior | NOT RUN | GPIO mock covers control flow, not real GPIO ioctls, voltage, pulse shape or carrier wiring |
| Physical boot/mesh/onboard Wi-Fi traffic | NOT RUN | Requires separately authorized hardware testing; no flashing performed |

Ordinary `fdtoverlay` rejects the existing baseline overlay's labeled fragment
root with `FDT_ERR_NOTFOUND`. Raspberry Pi's own merger successfully applies
both baseline and new overlays. No pinctrl changes or overlay normalization were
made to obtain those passing comparisons.

## Built artifacts

Generated locally at 18:49 UTC. Images are under
`bin/targets/bcm27xx/bcm2711/`; none has been flashed.

| Image | SHA256 |
| --- | --- |
| `openmanet-1.8.0-rpi4-mm6108-spi-squashfs-sysupgrade.img.gz` | `a0a9feccf74b2b5e3e81429ef248496d252ec03350cc56f217ba18e1485d9a5f` |
| `openmanet-1.8.0-rpi4-mm6108-sdio-squashfs-sysupgrade.img.gz` | `03c98ae8fcf3ffbf44099abe6053863dad0f651326fea0cb37959f78b65c5578` |
| `openmanet-1.8.0-rpi4-mm8108-usb-squashfs-sysupgrade.img.gz` | `8a121388a77b0c2591005f615de793b51bcc08f4a6478b8261bff59600081a7d` |

Final package hashes:

- BSP 1.0-r11: `2908f1ff9218bf5c82decbfdfcebfeaf7750e460c7c5044dbe4f2540a5139d0e`.
- Morse bundle 3: `71e119b719df908b47e4c7498e2e27cd62dfacd5f1d3b5e5981be65c93a4bf9e`.

## Re-run commands

From `packages` (replace build paths for a different target tree):

```sh
python3 boards/bsp-bcm271x/tests/test_spi_reset.py \
  --headers ../firmware/staging_dir/target-aarch64_cortex-a72_musl/usr/include --sanitize
```

The same runner supports `--cc`, `--runner` (qemu-aarch64-static), and
`--libfdt-source` for static ARM fixture tests. No real GPIO backend is linked
into either fixture binary.

From `firmware`:

```sh
python3 scripts/tests/test_wm6108_packaging.py --packages ../packages
python3 scripts/tests/test_wm6108_overlays.py \
  --kernel-tree build_dir/target-aarch64_cortex-a72_musl/linux-bcm27xx_bcm2711/linux-6.6.138 \
  --packages ../packages \
  --headers staging_dir/target-aarch64_cortex-a72_musl/usr/include \
  --dtmerge /tmp/wm6108-dtmerge
make package/feeds/openmanet/bsp-bcm271x/compile package/feeds/morse/morse-bundle/compile -j4 V=s
make -j4 V=s
```

The image inspector reads gzip/FAT/squashfs into temporary files without mounting
or writing a block device. Supply the built image paths and, if needed,
`--mcopy staging_dir/host/bin/mcopy`.

Local logs: `/tmp/wm6108-unit-tests.log`, `/tmp/wm6108-arm-tests.log`,
`/tmp/wm6108-overlay-tests.log`, `/tmp/wm6108-packaging-tests.log`,
`/tmp/wm6108-package-build.log`, `/tmp/wm6108-bsp-final-build.log`,
`/tmp/wm6108-firmware-build.log`, `/tmp/wm6108-image-inspection.log`.
Prior SPI and USB images were copied to `/tmp/wm6108-baseline-images/` before
starting the new build.

## Remaining gate

Do not enable the extra pulse by default based on these offline results. Prove
its benefit and check cold/warm boots, physical GPIO behavior, mesh traffic and
CM4 onboard Wi-Fi/MM8108 USB coexistence on real hardware first. Persistent GPIO
reconfiguration failure, SIGKILL and kernel faults cannot be made electrically
safe by a userspace cleanup handler alone.
