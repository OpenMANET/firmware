#!/usr/bin/env python3
"""Check normal image names and the selected 2.2 radio packages."""
import pathlib, sys
p = pathlib.Path(sys.argv[1]); radio = sys.argv[2]
assert radio in ('usb', 'spi')
chip = 'mm6108' if radio == 'spi' else 'mm8108'
other = 'mm8108' if radio == 'spi' else 'mm6108'
images = list(p.glob('*.img.gz'))
assert images and all(f'rpi4-{chip}-{radio}' in f.name.lower() and 'trial' not in f.name.lower() for f in images), images
manifests = list(p.glob('*.manifest')); assert manifests
for f in manifests:
    packages = {line.split()[0] for line in f.read_text().splitlines() if line.strip()}
    assert {f'kmod-{chip}', f'{chip}-firmware'} <= packages
    assert not {f'kmod-{other}', f'{other}-firmware', 'kmod-dot11ah', 'kmod-morse'} & packages
    assert not any('trial' in name for name in packages)
print('PASS: standard image names and 2.2 radio package manifest')
