#!/usr/bin/env python3
"""Fail closed if the trial configuration selects another radio or image."""
import pathlib
import sys
c = dict(line.strip().split('=', 1) for line in pathlib.Path('.config').read_text().splitlines() if line.startswith('CONFIG_') and '=' in line)
required = ['OPENMANET_MM8108_TRIAL', 'TARGET_bcm27xx_bcm2711', 'TARGET_MULTI_PROFILE', 'TARGET_PER_DEVICE_ROOTFS', 'PACKAGE_kmod-mm8108-trial', 'PACKAGE_kmod-dot11ah-mm8108-trial', 'PACKAGE_mm8108-trial-firmware', 'PACKAGE_openmanet-morse-stack', 'PACKAGE_morsecli', 'PACKAGE_hostapd_s1g', 'PACKAGE_wpa_supplicant_s1g']
for key in required:
    assert c.get('CONFIG_' + key) == 'y', f'{key} must be y'
for key in ['kmod-mm6108', 'kmod-mm8108', 'kmod-dot11ah', 'kmod-morse', 'mm6108-firmware', 'mm8108-firmware', 'morse-fw-6108', 'morse-fw-8108']:
    assert c.get('CONFIG_PACKAGE_' + key, 'n') == 'n', f'baseline package selected: {key}'
devices = [k for k, v in c.items() if k.startswith('CONFIG_TARGET_DEVICE_') and not k.startswith('CONFIG_TARGET_DEVICE_PACKAGES_') and v == 'y']
assert devices == ['CONFIG_TARGET_DEVICE_bcm27xx_bcm2711_DEVICE_bcm2711_mm8108-usb-trial'], devices
print('PASS: RPi4 MM8108 trial only; baseline radio packages excluded')
