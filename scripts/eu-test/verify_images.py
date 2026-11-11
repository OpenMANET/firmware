#!/usr/bin/env python3
"""Inspect actual EU test images and assemble only the intended release assets."""
import argparse
import hashlib
import json
import mmap
import pathlib
import shutil
import struct
import subprocess
import tarfile
import tempfile
import urllib.request
import zlib


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def unpack_gzip(image, path):
    # OpenWrt builds `gzip | append-metadata`: fwtool records follow the first
    # gzip member. gzip.open incorrectly treats their JSON as another member.
    decoder = zlib.decompressobj(31)
    with image.open('rb') as source, path.open('wb') as dest:
        while not decoder.eof:
            chunk = source.read(65536)
            if not chunk:
                raise RuntimeError(f'{image}: truncated gzip member')
            while chunk:
                dest.write(decoder.decompress(chunk, 1024 * 1024))
                chunk = decoder.unconsumed_tail
                if decoder.eof:
                    trailer = decoder.unused_data + source.read()
                    break
    # zlib validates the gzip CRC. Recognize complete fwtool records rather
    # than silently ignoring arbitrary trailing bytes; the full image is also
    # checked against the original build's SHA256 before inspecting its rootfs.
    metadata = None
    while trailer:
        if len(trailer) < 16:
            raise RuntimeError(f'{image}: incomplete fwtool trailer')
        magic, _crc, kind, size = struct.unpack('>4sI4sI', trailer[-16:])
        if magic != b'FWx0' or not 16 <= size <= len(trailer):
            raise RuntimeError(f'{image}: unrecognized data after gzip member')
        payload = trailer[-size:-16]
        if kind == b'\x01\x00\x00\x00':
            if payload[:8] != bytes(8):
                raise RuntimeError(f'{image}: unsupported fwtool metadata header')
            metadata = json.loads(payload[8:])
        elif kind != bytes(4):
            raise RuntimeError(f'{image}: unsupported fwtool record type')
        trailer = trailer[:-size]
    return metadata


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
        metadata = unpack_gzip(image, path)
        if metadata and 'bcm2711,mm8108-usb' not in metadata.get('supported_devices', []):
            raise RuntimeError(f'{image}: unexpected supported-device metadata')
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
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    parser.add_argument('--build-commit')
    args = parser.parse_args()
    source, output = args.source, args.output
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
        checksum = digest(image)
        sums = (image.parent / 'sha256sums').read_text().splitlines()
        built_checksums = {name.lstrip('*'): sha for sha, name in (line.split(maxsplit=1) for line in sums)}
        if built_checksums.get(image.name) != checksum:
            raise RuntimeError(f'{image}: checksum differs from original build output')
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
                if 'country=US' not in modules:
                    raise RuntimeError(f'{image}: normal module country default was changed')
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
        shutil.copy2(image, output / image.name)
        results.append({'image': image.name, 'sha256': checksum, 'contents_verified': True})
        print(f'PASS {image.name}: normal US module default, pinned selectable-EU netifd/defaults, firmware 2.2.3, version 1.8-eu')
    (output / 'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['image']}\n" for r in results))
    verification_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    firmware_sha = args.build_commit or verification_sha
    (output / 'BUILD_INFO.json').write_text(json.dumps({
        'firmware_commit': firmware_sha, 'packages_commit': packages_sha,
        'verification_commit': verification_sha,
        'release': '1.8-eu', 'images': results,
        'defaults': 'standard boot defaults; select EU in normal LuCI wizard',
        'hardware_validation': 'EU initialization validated separately on CM4/MM8108 USB at 0 dBm; these images and EU 16 dBm operation have not been boot/RF tested',
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
