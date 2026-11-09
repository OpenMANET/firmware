#!/usr/bin/env python3
"""Check the normal ekh-bcm2711 multi-image configuration."""
import pathlib
c = dict(line.split('=', 1) for line in pathlib.Path('.config').read_text().splitlines() if line.startswith('CONFIG_') and '=' in line)
for key in ['TARGET_bcm27xx_bcm2711', 'TARGET_MULTI_PROFILE', 'TARGET_PER_DEVICE_ROOTFS', 'PACKAGE_openmanet-morse-stack', 'PACKAGE_morsecli', 'PACKAGE_hostapd_s1g', 'PACKAGE_wpa_supplicant_s1g']:
    assert c.get('CONFIG_' + key) == 'y', f'{key} must be y'
for chip in ['mm6108', 'mm8108']:
    for package in [f'kmod-{chip}', f'{chip}-firmware']:
        assert c.get('CONFIG_PACKAGE_' + package) == 'm', f'{package} must be per-device (=m)'
for package in ['kmod-dot11ah', 'kmod-morse']:
    assert c.get('CONFIG_PACKAGE_' + package, 'n') == 'n', f'unexpected package: {package}'
assert not any('TRIAL' in k and v == 'y' for k, v in c.items())
devices = {k for k, v in c.items() if k.startswith('CONFIG_TARGET_DEVICE_') and not k.startswith('CONFIG_TARGET_DEVICE_PACKAGES_') and v == 'y'}
expected = {'CONFIG_TARGET_DEVICE_bcm27xx_bcm2711_DEVICE_bcm2711_' + radio for radio in ['mm6108-spi', 'mm6108-sdio', 'mm8108-usb']}
assert devices == expected, devices
if c.get('CONFIG_PACKAGE_camera-onvif-server') == 'y':
    info = pathlib.Path('tmp/.packageinfo').read_text()
    assert 'Source-Makefile: package/feeds/openmanet/camera-onvif-server/Makefile' in info
    assert 'Source-Makefile: package/feeds/morse/camera-onvif-server/Makefile' not in info
print('PASS: normal ekh-bcm2711 setup selects all three images with per-device 2.2 drivers')
