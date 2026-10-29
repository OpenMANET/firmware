#!/usr/bin/env python3
"""Drop optional m packages after resolution, retaining device package roots.
Resolving first preserves last-assignment semantics in overlapping fragments.
Kconfig reselects dependencies of the retained per-device packages afterward.
"""
import pathlib
profile = 'DEVICE_bcm2711_mm8108-usb-trial'
active = False
required = None
for line in pathlib.Path('tmp/.targetinfo').read_text().splitlines():
    if line.startswith('Target-Profile: '):
        active = line.split(': ', 1)[1] == profile
    if active and line.startswith('Target-Profile-Packages: '):
        required = set(line.split(': ', 1)[1].split())
        break
assert required and 'kmod-mm8108-trial' in required, 'trial profile metadata missing'
p = pathlib.Path('.config')
lines = p.read_text().splitlines()
for line in lines:
    if line.startswith('CONFIG_TARGET_DEVICE_PACKAGES_bcm27xx_bcm2711_' + profile + '='):
        for package in line.split('=', 1)[1].strip('"').split():
            if package.startswith('-'):
                required.discard(package[1:])
            else:
                required.add(package)
removed = 0
for i, line in enumerate(lines):
    if line.startswith('CONFIG_PACKAGE_') and line.endswith('=m'):
        key = line.split('=', 1)[0]
        if key.removeprefix('CONFIG_PACKAGE_') not in required:
            lines[i] = '# ' + key + ' is not set'
            removed += 1
p.write_text('\n'.join(lines) + '\n')
print(f'Omitted {removed} optional package roots; retained device package roots')
