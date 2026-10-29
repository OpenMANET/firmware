#!/usr/bin/env python3
"""Check final image inventory and radio package manifest; no hardware claims."""
import pathlib, sys
p = pathlib.Path(sys.argv[1])
images = list(p.glob('*.img.gz'))
assert images and all('rpi4-mm8108-usb-2.1-trial' in f.name.lower() for f in images), images
manifests = list(p.glob('*.manifest'))
assert manifests, 'missing manifest'
for f in manifests:
    packages = {line.split()[0] for line in f.read_text().splitlines() if line.strip()}
    assert {'kmod-mm8108-trial', 'kmod-dot11ah-mm8108-trial', 'mm8108-trial-firmware'} <= packages, f
    forbidden = {'kmod-mm8108','kmod-mm6108','kmod-dot11ah','kmod-morse','mm8108-firmware','mm6108-firmware'}
    assert not packages & forbidden, packages & forbidden
print('PASS: trial-only images and radio package manifest')
