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

## Verified normal build (2026-10-30)

The normal setup, `make download`, and `make -j8 V=sc` completed successfully
in `/home/ubuntu/openmanet/firmware`. The images were built from firmware
commit `63724b0be32ce9d3abb06b49e2214be220f38254`, with packages pinned to
`0005a14dcbb3a19bc9459373ab98b9e04e41c7d6`. Subsequent documentation-only
commits do not change this recorded image build revision.

Configuration, output metadata and all three extracted-rootfs checks passed.
`sha256sum -c sha256sums` passed. Each gzip payload also passed `gzip -t`
after removing the OpenWrt metadata trailer from a temporary copy with
`fwtool`; the original downloadable images retain their trailers. Running
`gzip -t` directly on those images reports the expected trailing metadata.

| Image | SHA-256 |
| --- | --- |
| MM8108 USB | `5404d380cad4001db96dcca13ce35777dab433b39c9d288b1655e45fae34b540` |
| MM6108 SPI | `046e7326ea3860ebf8ee8ccf4e0ae3ff7e706d280390d794219ca6b0bfbb9c2a` |
| MM6108 SDIO | `7b49be37b5e4a5b81746e4eda82495b1459f724960026c4d3f95a9fde5159f20` |

The standard board patch disables GLib's optional, implicitly detected
libelf support to avoid an undeclared build dependency during parallel builds.
Both host and target GLib builds passed. Package source archive hashes match
the normal OpenWrt downloader's output, including upstream BCF symlinks.

## Hardware validation still required

Compilation and filesystem checks do not establish RF performance or runtime
firmware-command compatibility. Test chip/module versions, country/BCF, cold
boots, reboots, radio restarts, LuCI configuration, GPS startup, encrypted mesh,
bidirectional TCP/UDP, loaded latency and CoT multicast. For USB test
unplug/replug recovery; for SPI check CMD53 busy timeouts, CRC errors and
repeated boot success at the board's existing clock. Test SDIO enumeration
and restart recovery on its hardware. Run sustained mesh traffic before deployment.
