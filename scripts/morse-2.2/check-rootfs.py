#!/usr/bin/env python3
"""Inspect the RPi4 image without mounting or writing an SD card.
Usage: check-rootfs.py image.img.gz [usb|spi|sdio]
Requires unsquashfs in PATH. Extracts only squashfs bytes to a temporary file.
"""
import gzip, hashlib, json, pathlib, struct, subprocess, sys, tempfile
image = pathlib.Path(sys.argv[1])
radio = sys.argv[2] if len(sys.argv) > 2 else 'usb'
assert radio in ('usb', 'spi', 'sdio')
chip = 'mm6108' if radio != 'usb' else 'mm8108'
other = 'mm8108' if radio != 'usb' else 'mm6108'
sources = json.loads(pathlib.Path(__file__).with_name('sources.json').read_text())

with tempfile.TemporaryDirectory() as d:
    rootfs = pathlib.Path(d) / 'rootfs.squashfs'
    with gzip.open(image, 'rb') as f:
        mbr = f.read(512)
        assert mbr[510:512] == b'\x55\xaa', 'invalid MBR'
        start, sectors = struct.unpack_from('<II', mbr, 446 + 16 + 8)
        f.seek(start * 512)
        sb = f.read(96)
        assert sb[:4] == b'hsqs', 'partition 2 is not squashfs'
        used = struct.unpack_from('<Q', sb, 40)[0]
        assert 96 <= used <= sectors * 512, 'invalid squashfs size'
        with rootfs.open('wb') as out:
            out.write(sb)
            left = used - 96
            while left:
                chunk = f.read(min(left, 1024 * 1024))
                assert chunk, 'truncated image'
                out.write(chunk)
                left -= len(chunk)
    def cat(path):
        return subprocess.check_output(['unsquashfs', '-cat', str(rootfs), path])
    inventory = subprocess.check_output(['unsquashfs', '-ll', str(rootfs)], text=True)
    paths = [line.split('squashfs-root/', 1)[1].split(' -> ', 1)[0] for line in inventory.splitlines() if 'squashfs-root/' in line]
    status = cat('usr/lib/opkg/status').decode()
    packages = {}
    for paragraph in status.split('\n\n'):
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))
        if 'Package' in fields:
            packages[fields['Package']] = fields
    required = {f'kmod-{chip}', f'{chip}-firmware'}
    forbidden = {'kmod-dot11ah', 'kmod-morse', 'kmod-mm6108-trial', 'kmod-mm8108-trial', 'mm6108-trial-firmware', 'mm8108-trial-firmware', f'kmod-{other}', f'{other}-firmware'}
    assert required <= packages.keys(), required - packages.keys()
    assert not forbidden & packages.keys(), forbidden & packages.keys()
    assert len([p for p in paths if p.endswith('/morse.ko')]) == 1
    assert not any(p.endswith(('/dot11ah.ko', '/mm6108_sdio.ko')) for p in paths)
    version = '2.2.2' if radio != 'usb' else '2.2.3'
    module_path = next(p for p in paths if p.endswith('/morse.ko'))
    module = cat(module_path)
    driver_source = sources['spi']['driver'] if radio != 'usb' else sources['driver']
    release = version + '-g' + driver_source['commit'][:8]
    # OpenWrt CONFIG_MODULE_STRIPPED removes version/device-alias metadata.
    # Check the actual release string used by the driver's startup log instead.
    assert b'\0' + release.encode() + b'\0' in module, 'wrong compiled driver version'
    assert b'parmtype=channelization_scheme:' in module, 'missing integrated channelization parameter'
    if radio == 'spi':
        assert b'\0morse_spi_init\0' in module and b'\0mm6108-spi\0' in module, 'SPI frontend missing'
        assert b'\0morse_usb_init\0' not in module, 'unexpected USB frontend'
    elif radio == 'sdio':
        assert b'\0morse_sdio_init\0' in module, 'SDIO frontend missing'
        assert b'\0morse_usb_init\0' not in module, 'unexpected USB frontend'
    else:
        assert b'\0morse_usb_init\0' in module, 'USB frontend missing'
        assert b'\0morse_spi_init\0' not in module, 'unexpected SPI frontend'
    for name in required:
        assert version in packages[name]['Version'], packages[name]
    firmware = 'mm6108.bin' if radio != 'usb' else 'mm8108b2-rl.bin'
    expected = sources['spi']['firmware']['mm6108_sha256'] if radio != 'usb' else sources['firmware']['mm8108b2_sha256']
    assert hashlib.sha256(cat('lib/firmware/morse/' + firmware)).hexdigest() == expected, 'wrong chip firmware'
    owned_paths = ['lib/firmware/morse/' + firmware]
    if radio == 'spi':
        bcf = sources['spi']['bcf']
        bcf_path = 'lib/firmware/morse/' + bcf['file']
        assert hashlib.sha256(cat(bcf_path)).hexdigest() == bcf['sha256'], 'wrong SPI board calibration'
        assert packages['morse-board-config']['Version'] == bcf['package_version'], 'changed baseline BCF package'
        defaults = cat('etc/uci-defaults/99_morse_radio_defaults')
        assert b'/etc/modules.d/mm6108' in defaults, 'SPI missing persistent crystal initialization'
        owned_paths.append(bcf_path)
    if radio == 'sdio':
        bcf = sources['sdio_bcf']
        bcf_path = 'lib/firmware/morse/' + bcf['file']
        assert hashlib.sha256(cat(bcf_path)).hexdigest() == bcf['sha256'], 'wrong SDIO board calibration'
        assert bcf['package'] in packages
        owned_paths.append(bcf_path)
    if radio == 'usb':
        bcf = cat('lib/firmware/morse/bcf_mm8108_m20_us.bin')
        assert hashlib.sha256(bcf).hexdigest() == sources['bcf_sha256'], 'wrong M20-US BCF'
        assert 'bcf_boardtype_0808.bin -> bcf_mm8108_m20_us.bin' in inventory
        owned_paths += ['lib/firmware/morse/bcf_mm8108_m20_us.bin', 'lib/firmware/morse/bcf_boardtype_0808.bin']
    assert f'etc/modules.d/{chip}' in paths
    if 'camera-onvif-server' in packages:
        assert b'option service_port 8082' in cat('etc/config/camera-onvif-server'), 'missing 1.8.1-dev ONVIF port fix'
    # Check ownership from installed package file lists, rather than manifest alone.
    for owned in owned_paths:
        owners = []
        for p in paths:
            if p.startswith('usr/lib/opkg/info/') and p.endswith('.list'):
                if '/' + owned in cat(p).decode().splitlines():
                    owners.append(p)
        assert len(owners) == 1, (owned, owners)
    print('PASS:', image.name, radio, 'radio modules, firmware, calibration and ownership')
