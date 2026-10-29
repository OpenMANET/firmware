#!/usr/bin/env python3
"""Inspect the RPi4 image without mounting or writing an SD card.
Usage: check-rootfs.py trial.img.gz [--baseline]
Requires unsquashfs in PATH. Extracts only squashfs bytes to a temporary file.
"""
import gzip, hashlib, pathlib, struct, subprocess, sys, tempfile
image = pathlib.Path(sys.argv[1])
baseline = '--baseline' in sys.argv[2:]
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
    trial = {'kmod-mm8108-trial', 'kmod-dot11ah-mm8108-trial', 'mm8108-trial-firmware'}
    original = {'kmod-mm8108', 'kmod-dot11ah', 'mm8108-firmware'}
    required, forbidden = (original, trial) if baseline else (trial, original)
    assert required <= packages.keys(), required - packages.keys()
    assert not (forbidden | {'kmod-mm6108', 'mm6108-firmware', 'kmod-morse'}) & packages.keys(), 'mixed radio packages'
    for module in ['morse.ko', 'dot11ah.ko']:
        assert len([p for p in paths if p.endswith('/' + module)]) == 1, module
    assert not any(p.endswith('/mm6108_sdio.ko') for p in paths)
    for name in required:
        expected = '2.0.0' if baseline else '2.1.0'
        assert expected in packages[name]['Version'], packages[name]
    # Compare the calibration file byte-for-byte with the preserved baseline.
    bcf = cat('lib/firmware/morse/bcf_mm8108_m20_us.bin')
    assert hashlib.sha256(bcf).hexdigest() == '7fdc1f9ed7ecb1cae20369383eb9d24878230226a4ac09c16a7680acd4a5e1e2', 'board calibration changed'
    assert 'bcf_boardtype_0808.bin -> bcf_mm8108_m20_us.bin' in inventory
    if not baseline:
        chip = cat('lib/firmware/morse/mm8108b2-rl.bin')
        assert hashlib.sha256(chip).hexdigest() == '8cfabb9736e6ac047020eb2dc20dd7851a507777d47f47560b5e0afc28cd95cc', 'wrong chip firmware'
    # Check ownership from installed package file lists, rather than manifest alone.
    for owned in ['lib/firmware/morse/bcf_mm8108_m20_us.bin', 'lib/firmware/morse/bcf_boardtype_0808.bin', 'lib/firmware/morse/mm8108b2-rl.bin']:
        owners = []
        for p in paths:
            if p.startswith('usr/lib/opkg/info/') and p.endswith('.list'):
                if '/' + owned in cat(p).decode().splitlines():
                    owners.append(p)
        assert len(owners) == 1, (owned, owners)
    print('PASS:', image.name, 'baseline' if baseline else 'trial', 'radio modules, firmware, calibration and ownership')
