#!/usr/bin/env python3
"""Inspect the RPi4 image without mounting or writing an SD card.
Usage: check-rootfs.py trial.img.gz [usb|spi]
Requires unsquashfs in PATH. Extracts only squashfs bytes to a temporary file.
"""
import gzip, hashlib, json, pathlib, struct, subprocess, sys, tempfile
image = pathlib.Path(sys.argv[1])
radio = sys.argv[2] if len(sys.argv) > 2 else 'usb'
assert radio in ('usb', 'spi')
chip = 'mm6108' if radio == 'spi' else 'mm8108'
other = 'mm8108' if radio == 'spi' else 'mm6108'
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
    required = {f'kmod-{chip}-trial', f'{chip}-trial-firmware'}
    forbidden = {'kmod-mm8108', 'kmod-mm6108', 'kmod-dot11ah', 'kmod-morse',
                 'kmod-dot11ah-mm8108-trial', 'mm6108-firmware', 'mm8108-firmware',
                 f'kmod-{other}-trial', f'{other}-trial-firmware'}
    assert required <= packages.keys(), required - packages.keys()
    assert not forbidden & packages.keys(), forbidden & packages.keys()
    assert len([p for p in paths if p.endswith('/morse.ko')]) == 1
    assert not any(p.endswith(('/dot11ah.ko', '/mm6108_sdio.ko')) for p in paths)
    version = '2.2.2' if radio == 'spi' else '2.2.3'
    for name in required:
        assert version in packages[name]['Version'], packages[name]
    firmware = 'mm6108.bin' if radio == 'spi' else 'mm8108b2-rl.bin'
    expected = sources['spi']['firmware']['mm6108_sha256'] if radio == 'spi' else sources['firmware']['mm8108b2_sha256']
    assert hashlib.sha256(cat('lib/firmware/morse/' + firmware)).hexdigest() == expected, 'wrong chip firmware'
    owned_paths = ['lib/firmware/morse/' + firmware]
    if radio == 'usb':
        bcf = cat('lib/firmware/morse/bcf_mm8108_m20_us.bin')
        assert hashlib.sha256(bcf).hexdigest() == sources['bcf_sha256'], 'wrong M20-US BCF'
        assert 'bcf_boardtype_0808.bin -> bcf_mm8108_m20_us.bin' in inventory
        owned_paths += ['lib/firmware/morse/bcf_mm8108_m20_us.bin', 'lib/firmware/morse/bcf_boardtype_0808.bin']
    assert f'etc/modules.d/{chip}-trial' in paths
    # Check ownership from installed package file lists, rather than manifest alone.
    for owned in owned_paths:
        owners = []
        for p in paths:
            if p.startswith('usr/lib/opkg/info/') and p.endswith('.list'):
                if '/' + owned in cat(p).decode().splitlines():
                    owners.append(p)
        assert len(owners) == 1, (owned, owners)
    print('PASS:', image.name, radio, 'radio modules, firmware, calibration and ownership')
