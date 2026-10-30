# Morse 2.2 image upgrade

Branch `codex/morse-2.2` upgrades the normal driver and firmware packages.
All deployed nodes will be rebuilt. It includes the `1.8.1-dev` baselines:
firmware `a1eee8863dfa4635d0bfa75fe499738a48861e83` and packages
`ec6146eff8c28eb44f2afa8496a5ecafcb379f1a`.

| Standard image | Driver and firmware |
| --- | --- |
| RPi4 MM8108 USB | 2.2.3 |
| RPi4 MM6108 SPI | 2.2.2 |
| RPi4 MM6108 SDIO | 2.2.2 |

The standard `ekh-bcm2711` board setup builds all three images together.
Both chip drivers compile as packages (`=m`); each device definition installs
its own driver and firmware. This avoids installing two providers of
`morse.ko` into the shared rootfs. Common Morse userspace remains selected
at `=y`. Netifd passes channelization parameters to the integrated module.

## Normal build

Use the repository workflow from `AGENTS.md`, starting in `firmware/`:

```sh
./scripts/openmanet_setup.sh -i -b ekh-bcm2711
make download
make -j8
```

`feeds.conf.default` pins the companion 2.2 packages commit. No custom
configuration helper, package pruning, or external toolchain is required.
The existing setup script applies the board feed patches and installs feeds.
Re-run this sequence after a clean operation.

Images and checksums are generated directly in
`firmware/bin/targets/bcm27xx/bcm2711/`:

- `openmanet-1.8.1-rpi4-mm8108-usb-squashfs-sysupgrade.img.gz`
- `openmanet-1.8.1-rpi4-mm6108-spi-squashfs-sysupgrade.img.gz`
- `openmanet-1.8.1-rpi4-mm6108-sdio-squashfs-sysupgrade.img.gz`
- `sha256sums`

The earlier separate-builder images are superseded by this normal-workflow
rebuild. Their hashes do not describe the new images.

## Verification

The scripts below inspect build results; they do not configure or build images:

```sh
python3 scripts/morse-2.2/check-config.py
python3 scripts/morse-2.2/check-artifacts.py
python3 scripts/morse-2.2/check-rootfs.py bin/targets/bcm27xx/bcm2711/*rpi4-mm8108-usb-squashfs-sysupgrade.img.gz usb
python3 scripts/morse-2.2/check-rootfs.py bin/targets/bcm27xx/bcm2711/*rpi4-mm6108-spi-squashfs-sysupgrade.img.gz spi
python3 scripts/morse-2.2/check-rootfs.py bin/targets/bcm27xx/bcm2711/*rpi4-mm6108-sdio-squashfs-sysupgrade.img.gz sdio
```

Exact driver, firmware and calibration source hashes are recorded in
`scripts/morse-2.2/sources.json`. Rootfs checks verify each image's driver,
firmware, calibration, module parameters and package ownership separately;
the shared multi-profile manifest alone cannot establish per-image contents.

## Hardware validation still required

Compilation and filesystem checks do not establish RF performance or runtime
firmware-command compatibility. Test chip/module versions, country/BCF, cold
boots, reboots, radio restarts, LuCI configuration, GPS startup, encrypted mesh,
bidirectional TCP/UDP, loaded latency and CoT multicast. For USB test
unplug/replug recovery; for SPI check CMD53 busy timeouts, CRC errors and
repeated boot success at the board's existing clock. Test SDIO enumeration
and restart recovery on its hardware. Run sustained mesh traffic before deployment.
