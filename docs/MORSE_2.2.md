# Morse 2.2 image upgrade

Branch `codex/morse-2.2` upgrades the normal driver and firmware packages.
All deployed nodes will be rebuilt with new images. There is no opt-in trial
stack, parallel 2.0 driver stack, standalone dot11ah module, or rollback-image
requirement on this branch.

The branch includes `1.8.1-dev` firmware commit
`a1eee8863dfa4635d0bfa75fe499738a48861e83` and packages commit
`ec6146eff8c28eb44f2afa8496a5ecafcb379f1a`.

| Image profile | Normal packages | Driver and firmware |
| --- | --- | --- |
| `rpi4-mm8108-usb` | `kmod-mm8108`, `mm8108-firmware` | 2.2.3 |
| `rpi4-mm6108-spi` | `kmod-mm6108`, `mm6108-firmware` | 2.2.2 |

Both drivers build the integrated `morse.ko`. Netifd sends channelization
parameters directly to that module. MM6108 board defaults preserve external
crystal initialization in UCI so radio restarts retain it. MM8108 keeps USB/SDIO
support and MM6108 keeps SPI/SDIO support. Each image selects one chip driver.

Exact commits and archive hashes are in `scripts/morse-2.2/sources.json`.
MM8108 uses the matching 2.2 M20-US calibration file. MM6108 SPI retains the
existing Quectel board calibration and its package ownership. The validated
OpenMANET regulatory, AP/STA channel alignment, interface-creation, SPI timing
and optional FEM GPIO changes are rebased onto the 2.2 sources.

## Build and verify

In a fresh firmware checkout, using the pinned packages checkout:

```sh
./scripts/morse-2.2/setup.sh /absolute/path/to/packages usb
make download
make -j8
python3 scripts/morse-2.2/check-config.py usb
python3 scripts/morse-2.2/check-artifacts.py bin/targets/bcm27xx/bcm2711 usb
python3 scripts/morse-2.2/check-rootfs.py bin/targets/bcm27xx/bcm2711/*sysupgrade.img.gz usb
```

Use `spi` for MM6108. In an initialized builder use
`./scripts/morse-2.2/configure.sh usb` or `spi` before the download/build.
`MORSE_EXTERNAL_TOOLCHAIN=/absolute/toolchain/path` can select an existing
compatible toolchain. Preserve the resolved config, feed/build revisions,
manifest and image hashes with each image. Do not run concurrent builds in
one build/staging directory.

If source submodules use GitHub SSH URLs, apply an HTTPS rewrite to both
commands, for example:

```sh
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=url.https://github.com/.insteadOf
export GIT_CONFIG_VALUE_0=git@github.com:
make download
make -j8
```

## Hardware validation still required

Compilation and filesystem checks do not establish RF performance or runtime
firmware-command compatibility. Test the new images on the rebuilt nodes:
chip/module versions, country/BCF, cold boots, reboots, radio restarts, LuCI
configuration, GPS startup, encrypted mesh, bidirectional TCP/UDP, loaded
latency and CoT multicast. For USB test unplug/replug recovery; for SPI check
CMD53 busy timeouts, CRC errors, reset timing and repeated boot success at the
board's existing clock. Run sustained mesh traffic before deployment.
