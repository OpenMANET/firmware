#!/usr/bin/env python3
"""Fail closed if the trial configuration selects another radio or image."""
import pathlib
import sys
radio = sys.argv[1] if len(sys.argv) > 1 else "usb"
assert radio in ("usb", "spi")
chip = "mm6108" if radio == "spi" else "mm8108"
other = "mm8108" if radio == "spi" else "mm6108"
c = dict(line.strip().split('=', 1) for line in pathlib.Path('.config').read_text().splitlines() if line.startswith('CONFIG_') and '=' in line)
required = ['OPENMANET_MORSE_22_TRIAL', f'OPENMANET_{chip.upper()}_TRIAL', 'TARGET_bcm27xx_bcm2711', 'TARGET_MULTI_PROFILE', 'TARGET_PER_DEVICE_ROOTFS', f'PACKAGE_kmod-{chip}-trial', f'PACKAGE_{chip}-trial-firmware', 'PACKAGE_openmanet-morse-stack', 'PACKAGE_morsecli', 'PACKAGE_hostapd_s1g', 'PACKAGE_wpa_supplicant_s1g']
for key in required:
    assert c.get('CONFIG_' + key) == 'y', f'{key} must be y'
for key in [f'kmod-{other}-trial', f'{other}-trial-firmware', 'kmod-dot11ah-mm8108-trial', 'kmod-mm6108', 'kmod-mm8108', 'kmod-dot11ah', 'kmod-morse', 'mm6108-firmware', 'mm8108-firmware', 'morse-fw-6108', 'morse-fw-8108']:
    assert c.get('CONFIG_PACKAGE_' + key, 'n') == 'n', f'baseline package selected: {key}'
devices = [k for k, v in c.items() if k.startswith('CONFIG_TARGET_DEVICE_') and not k.startswith('CONFIG_TARGET_DEVICE_PACKAGES_') and v == 'y']
assert devices == [f'CONFIG_TARGET_DEVICE_bcm27xx_bcm2711_DEVICE_bcm2711_{chip}-{radio}-trial'], devices
if c.get('CONFIG_PACKAGE_camera-onvif-server') == 'y':
    info = pathlib.Path('tmp/.packageinfo').read_text()
    assert 'Source-Makefile: package/feeds/openmanet/camera-onvif-server/Makefile' in info, 'missing 1.8.1-dev camera override'
    assert 'Source-Makefile: package/feeds/morse/camera-onvif-server/Makefile' not in info, 'stale camera feed provider'
print(f'PASS: RPi4 {chip} {radio} trial only; baseline radio packages excluded')
