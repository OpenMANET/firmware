#!/usr/bin/env python3
"""Check final image inventory and radio package manifest; no hardware claims."""
import pathlib, sys
p = pathlib.Path(sys.argv[1])
radio = sys.argv[2] if len(sys.argv) > 2 else 'usb'
assert radio in ('usb', 'spi')
chip = 'mm6108' if radio == 'spi' else 'mm8108'
other = 'mm8108' if radio == 'spi' else 'mm6108'
images = list(p.glob('*.img.gz'))
assert images and all(f'rpi4-{chip}-{radio}-2.2-trial' in f.name.lower() for f in images), images
manifests = list(p.glob('*.manifest'))
assert manifests, 'missing manifest'
for f in manifests:
    packages = {line.split()[0] for line in f.read_text().splitlines() if line.strip()}
    assert {f'kmod-{chip}-trial', f'{chip}-trial-firmware'} <= packages, f
    forbidden = {f'kmod-{other}-trial', f'{other}-trial-firmware', 'kmod-dot11ah-mm8108-trial', 'kmod-mm8108','kmod-mm6108','kmod-dot11ah','kmod-morse','mm8108-firmware','mm6108-firmware'}
    assert not packages & forbidden, packages & forbidden
print('PASS: trial-only images and radio package manifest')
