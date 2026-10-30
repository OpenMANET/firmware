# Morse 2.2 trials on Raspberry Pi 4

Two opt-in images are built on branch `codex/morse-2.2-trial`, incorporating
`1.8.1-dev` firmware `a1eee8863dfa4635d0bfa75fe499738a48861e83` and packages
`ec6146eff8c28eb44f2afa8496a5ecafcb379f1a`. These are disposable bench images;
no rollback artifact is required. Existing branches can reproduce older builds.
Hardware validation is required before promotion.

| Profile | Driver | Chip firmware | BCF |
| --- | --- | --- | --- |
| `usb` / `rpi4-mm8108-2.2-trial` | MM8108 2.2.3 | MM8108 2.2.3 | M20-US from the pinned 2.2 firmware source |
| `spi` / `rpi4-mm6108-2.2-trial` | MM6108 2.2.2 | MM6108 2.2.2 | Existing board-specific BCF selection |

Exact source commits, archive hashes and firmware hashes are recorded in
`scripts/mm8108-trial/sources.json`. Firmware comes from untagged upstream
commit `db4b69fd212990c59c5f1712e23060cbb94276ec`, not a moving branch.
Each driver builds `morse.ko` with integrated dot11ah; neither image contains
a standalone `dot11ah.ko` or a second radio driver. Baseline radio packages
remain unchanged. Shared userspace keeps its upstream versions, with trial
package release suffixes and explicit dependencies on the selected trial driver.
Netifd recognizes trial module configuration files and applies channelization
to `morse.ko`; baseline split-module loading remains supported.

The SPI trial preserves inter-transaction delays, optional FEM voltage GPIO,
regulatory discovery, AP/STA channel alignment, userspace-owned interface
creation, and channel-flag compatibility fixes. The optional FEM GPIO uses
device-managed ownership at SPI probe. The legacy module rename is unnecessary
because trial drivers conflict and cannot be installed together. Upstream
CMD53 ready polling remains enabled. Runtime timing and reset behavior are
unverified until tested on hardware.

## Build

From a fresh firmware checkout with the matching packages commit:

```sh
./scripts/mm8108-trial/setup.sh /absolute/path/to/packages usb
make download
make -j8
python3 scripts/mm8108-trial/check-config.py usb
python3 scripts/mm8108-trial/check-artifacts.py bin/targets/bcm27xx/bcm2711 usb
python3 scripts/mm8108-trial/check-rootfs.py bin/targets/bcm27xx/bcm2711/*sysupgrade.img.gz usb
```

Use `spi` in place of `usb` for the SPI image. For an existing initialized
builder, run `scripts/mm8108-trial/configure.sh usb` (or `spi`) before download
and build. An existing compatible external toolchain can be explicitly selected
with `MORSE_TRIAL_EXTERNAL_TOOLCHAIN=/absolute/toolchain/path`; record this
alongside `.config`, feed revisions, manifests and image hashes.
Do not run concurrent builds against the same staging or build directories.

## Acceptance on devices

Check chip firmware and module versions, country/BCF, interfaces, LuCI saves,
GPS startup, and encrypted mesh with existing 2.0 nodes. Exercise cold boots,
reboots, radio restarts, bidirectional TCP/UDP, loaded latency, and CoT multicast.
For USB, test unplug/replug recovery. For SPI, examine CMD53 busy timeouts, CRC
errors, reset timing and repeated boot success with the existing board clock.
Run sustained mesh traffic before promotion. Compilation and rootfs inspection
do not establish firmware command compatibility or RF performance.
