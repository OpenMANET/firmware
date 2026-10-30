#!/usr/bin/env python3
"""Check the normal RPi4 2.2 driver selection."""
import pathlib, sys
radio = sys.argv[1] if len(sys.argv) > 1 else 'usb'
assert radio in ('usb', 'spi')
chip = 'mm6108' if radio == 'spi' else 'mm8108'
other = 'mm8108' if radio == 'spi' else 'mm6108'
c = dict(line.strip().split('=', 1) for line in pathlib.Path('.config').read_text().splitlines() if line.startswith('CONFIG_') and '=' in line)
for key in ['TARGET_bcm27xx_bcm2711', 'TARGET_MULTI_PROFILE', 'TARGET_PER_DEVICE_ROOTFS', f'PACKAGE_kmod-{chip}', f'PACKAGE_{chip}-firmware', 'PACKAGE_openmanet-morse-stack', 'PACKAGE_morsecli', 'PACKAGE_hostapd_s1g', 'PACKAGE_wpa_supplicant_s1g']:
    assert c.get('CONFIG_' + key) == 'y', f'{key} must be y'
for key in [f'kmod-{other}', f'{other}-firmware', 'kmod-dot11ah', 'kmod-morse', 'kmod-mm6108-trial', 'kmod-mm8108-trial', 'mm6108-trial-firmware', 'mm8108-trial-firmware']:
    assert c.get('CONFIG_PACKAGE_' + key, 'n') == 'n', f'unexpected package: {key}'
assert not any('TRIAL' in k and v == 'y' for k, v in c.items())
devices = [k for k,v in c.items() if k.startswith('CONFIG_TARGET_DEVICE_') and not k.startswith('CONFIG_TARGET_DEVICE_PACKAGES_') and v == 'y']
assert devices == [f'CONFIG_TARGET_DEVICE_bcm27xx_bcm2711_DEVICE_bcm2711_{chip}-{radio}'], devices
if c.get('CONFIG_PACKAGE_camera-onvif-server') == 'y':
    info = pathlib.Path('tmp/.packageinfo').read_text()
    assert 'Source-Makefile: package/feeds/openmanet/camera-onvif-server/Makefile' in info
    assert 'Source-Makefile: package/feeds/morse/camera-onvif-server/Makefile' not in info
print(f'PASS: RPi4 {chip} {radio} normal 2.2 packages selected')
