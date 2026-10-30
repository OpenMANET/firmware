#!/usr/bin/env python3
"""Check normal multi-image output; check-rootfs.py verifies per-image packages."""
import pathlib, sys
p = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'bin/targets/bcm27xx/bcm2711')
for radio in ['mm8108-usb', 'mm6108-spi', 'mm6108-sdio']:
    images = list(p.glob(f'*rpi4-{radio}-squashfs-sysupgrade.img.gz'))
    assert len(images) == 1, (radio, images)
assert list(p.glob('*.manifest')), 'missing shared manifest'
for name in ['sha256sums', 'profiles.json', 'config.buildinfo', 'feeds.buildinfo', 'version.buildinfo']:
    assert (p / name).is_file(), name
print('PASS: all three standard RPi4 images and build metadata present')
