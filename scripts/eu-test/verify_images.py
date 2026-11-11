#!/usr/bin/env python3
"""Inspect actual EU test images and assemble only the intended release assets."""
import gzip
import hashlib
import json
import mmap
import pathlib
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


def squashfs_offsets(path):
    with path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        start = 0
        while True:
            offset = data.find(b'hsqs', start)
            if offset < 0:
                return
            start = offset + 4
            if offset + 96 > len(data):
                continue
            block_size = struct.unpack_from('<I', data, offset + 12)[0]
            major = struct.unpack_from('<H', data, offset + 28)[0]
            size = struct.unpack_from('<Q', data, offset + 40)[0]
            if major == 4 and 4096 <= block_size <= 1048576 and size <= len(data) - offset:
                yield offset


def image_file(image, directory):
    path = image
    if image.suffix == '.gz':
        path = directory / 'image.img'
        with gzip.open(image, 'rb') as source, path.open('wb') as dest:
            shutil.copyfileobj(source, dest)
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            roots = [m for m in archive.getmembers() if m.isfile() and m.name.endswith('/root')]
            if len(roots) != 1:
                raise RuntimeError(f'Expected one sysupgrade rootfs: {image}')
            result = directory / 'rootfs.bin'
            with archive.extractfile(roots[0]) as source, result.open('wb') as dest:
                shutil.copyfileobj(source, dest)
            return result
    return path


def read_file(image, offset, name):
    return subprocess.check_output(['unsquashfs', '-cat', '-o', str(offset), str(image), name],
                                   stderr=subprocess.PIPE)


def main():
    source, output = map(pathlib.Path, sys.argv[1:])
    output.mkdir(parents=True, exist_ok=True)
    feed_line = next(line for line in pathlib.Path('feeds.conf.default').read_text().splitlines()
                     if line.startswith('src-git openmanet '))
    packages_sha = feed_line.rsplit('^', 1)[1]
    paths = {
        'lib/netifd/wireless/morse.sh': 'morse-micro/netifd-morse/lib/netifd/wireless/morse.sh',
        'etc/uci-defaults/99_morse_radio_defaults': 'boards/bsp-common/files/uci-defaults/99_morse_radio_defaults',
    }
    expected = {}
    for target, repo_path in paths.items():
        url = f'https://raw.githubusercontent.com/OpenMANET/packages/{packages_sha}/{repo_path}'
        with urllib.request.urlopen(url, timeout=60) as response:
            expected[target] = response.read()
    patterns = ['*halowlink2*sysupgrade.bin', '*rpi4-mm8108-usb*.img.gz']
    results = []
    for pattern in patterns:
        images = list(source.rglob(pattern))
        if len(images) != 1:
            raise RuntimeError(f'Expected exactly one {pattern}: {images}')
        image = images[0]
        with tempfile.TemporaryDirectory() as directory:
            filesystem = image_file(image, pathlib.Path(directory))
            for offset in squashfs_offsets(filesystem):
                try:
                    script = read_file(filesystem, offset, 'lib/netifd/wireless/morse.sh')
                except subprocess.CalledProcessError:
                    continue
                if script != expected['lib/netifd/wireless/morse.sh']:
                    raise RuntimeError(f'{image}: netifd differs from pinned source')
                for target, content in expected.items():
                    if read_file(filesystem, offset, target) != content:
                        raise RuntimeError(f'{image}: {target} differs from pinned source')
                modules = read_file(filesystem, offset, 'etc/modules.d/mm8108').decode()
                if 'country=EU' not in modules:
                    raise RuntimeError(f'{image}: module does not default to EU')
                version = read_file(filesystem, offset, 'etc/openwrt_release').decode()
                if '1.8-eu' not in version:
                    raise RuntimeError(f'{image}: wrong version identity: {version}')
                status = read_file(filesystem, offset, 'usr/lib/opkg/status').decode()
                firmware = next((p for p in status.split('\n\n')
                                 if p.startswith('Package: mm8108-firmware\n')), '')
                if 'Version: 2.2.3' not in firmware:
                    raise RuntimeError(f'{image}: MM8108 firmware is not 2.2.3')
                break
            else:
                raise RuntimeError(f'{image}: no readable expected squashfs root')
        checksum = hashlib.file_digest(image.open('rb'), 'sha256').hexdigest()
        shutil.copy2(image, output / image.name)
        results.append({'image': image.name, 'sha256': checksum, 'contents_verified': True})
        print(f'PASS {image.name}: EU module, pinned netifd/defaults, firmware 2.2.3, version 1.8-eu')
    (output / 'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['image']}\n" for r in results))
    firmware_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    (output / 'BUILD_INFO.json').write_text(json.dumps({
        'firmware_commit': firmware_sha, 'packages_commit': packages_sha,
        'release': '1.8-eu', 'images': results,
        'hardware_validation': 'EU initialization validated separately on CM4/MM8108 USB at 0 dBm; these images and EU 16 dBm operation have not been boot/RF tested',
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
