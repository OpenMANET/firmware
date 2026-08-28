# Last Claude Report — Raspberry Pi 5 Port, Session 2

Date: 2026-08-27
Branch: `pi5-wm6108-port` · Head: `619022f` · Baseline: `365b276`

## COMPLETED

**BUILD VERIFIED — both targets green.**

| Target | Result |
|---|---|
| `ekh-bcm2712` (Pi 5) | `make -j20` exit 0. `openmanet-1.8.0-rpi5-mm6108-spi-squashfs-sysupgrade.img.gz`, 53,400,452 bytes. |
| `ekh-bcm2711` (Pi 4 regression) | `make -j10` exit 0. All three shipping images built: mm6108-spi, mm6108-sdio, mm8108-usb. |

The WSL2 reboot blocker from session 1 was cleared, the environment provisioned, and
both boards built from the same commit.

**The Pi 5 image was verified by extraction, not inference.** Gunzipped, partition
table read, FAT listed with mtools, squashfs unpacked. It contains `kernel_2712.img`,
all six Pi 5 DTBs, `overlays/mm610x-spi-pi5.dtbo`, a correctly assembled
`distroconfig.txt` ending in `dtoverlay=mm610x-spi-pi5` and
`dtoverlay=sysinfo,board-name="bcm2712,mm6108-spi"`, plus `mm6108_sdio.ko`,
`batman-adv.ko`, `mm6108.bin`, `bcf_fgh100mhaamd.bin`, `openmanetd`, `morse_cli`,
hostapd/wpa_supplicant/alfred/gpiod.

**Device tree verified in binary form.** The new `991-0006` puts MM_RESET/MM_WAKE/
MM_BUSY into both compiled Pi 5 DTBs (including D0 silicon). The Pi 5 overlay
decompiles to exactly three external label fixups — `rp1_spi0`, `rp1_spi0_gpio9`,
`rp1_gpio` — and all three resolve in both base DTBs. Since the firmware rejects an
overlay whose labels are unresolvable, that is the strongest evidence available
short of hardware that the overlay will load.

**Three real defects fixed from the gpio helper's audit** (commit `4750f24`):
`991-0006` gpio-line-names; a chipreset.sh path that would unbind the Pi 5's SD
controller and never rebind it if the overlay failed to load; and a gpsboard.init
that hardcodes `gpiochip0` and the BCM2711 SPI0 sysfs path.

**Three build blockers fixed — none were Pi 5 regressions** (commits `b7eb941`,
`619022f`). Every one reproduced identically on the untouched Pi 4 board, which is
why it was built in parallel from the start: a golang `go`-symlink mismatch between
the openmanet and packages feeds that broke runc/docker/containerd; openmanetd
*hanging* (not failing) on scp-style SSH submodule URLs with no `url.insteadOf`
rewrite; and missing host `-dev` libraries for the alfred bindings, which build with
the host toolchain. The last two were gaps between the WSL provisioning script and
what CI installs; `provision-build-env.sh` now matches CI.

**Pi 4 preserved.** Its build is green, `MM_RESET` is still in the built
`bcm2711-rpi-4-b.dtb`, its distroconfig still selects `mm610x-spi`, and the 507-vs-457
package manifest diff is fully accounted for — camera stack, mm8108 variant, BCM283x
SPI/I2C kmods, EKH01 carrier NIC, and the bcm2711-gated persistent-vars package.

## CURRENT

Software work for Phase 1 is complete and BUILD VERIFIED. It is emphatically **NOT
HARDWARE VERIFIED**: nothing has run on a Pi 5.

## OWNER ACTION REQUIRED

**One action: flash and boot a Pi 5.**

The image is already copied to Windows at:

    C:\AI-Projects\OpenMANET-Pi5\images\openmanet-1.8.0-rpi5-mm6108-spi-squashfs-sysupgrade.img.gz

sha256 3686d0b3c28a0e7ed7760bb40f1ca6c385030a3cde175d3ddb3bca382e064cea, 53,400,458 bytes
(verified against the regenerated `sha256sums` after the copy)

1. Flash it to an SD card (Raspberry Pi Imager or `dd`; it is a full disk image).
2. Fit the card in the Pi 5 with the WM1302 HAT + Wio-WM6108.
3. Plug the Waveshare Pi 5 3-pin UART lead into the dedicated JST-SH debug UART
   connector between the HDMI ports. Open it at 115200 8N1. No jumper wires needed.
4. **Cold power cycle** — pull power, do not warm-reboot. The MM6108 first probe
   requires it.
5. Send me the serial boot log.

What the log needs to show, in order: RP1 enumerating over PCIe and `pinctrl-rp1`
probing; `spi-dw-mmio` binding and `spi0` appearing; the morse driver probing on
`spi0.0`; `bcf_fgh100mhaamd.bin` and `mm6108.bin` loading; a HaLow interface
appearing. Also watch for `morsechipreset` logging "unable to reset as MM_RESET is
not in gpio-line-names" — that would mean the overlay did not load.

One unit proves boot, SPI and MM6108 probe. Two are needed for the Phase 1 mesh
objective.

## NEXT

Nothing further can be verified without hardware. The one remaining non-hardware
task is wiring `build-ekh-bcm2712` into `build-release.yml`, which was deliberately
left until the Pi 5 build went green — it is now unblocked, but CI wiring cannot be
validated without pushing, so it waits for a decision to push the branch.
