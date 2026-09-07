#!/usr/bin/env python3
"""Read-only inspection of final compressed bcm27xx images. No mounts/flashing.
Extract only the FAT partition and used squashfs bytes into temporary files.
"""
import argparse
import gzip
import hashlib
from pathlib import Path
import struct
import subprocess
import tempfile


def command(*args):
    return subprocess.check_output(args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--unsquashfs", default="unsquashfs")
    parser.add_argument("--mcopy", default="mcopy")
    opts = parser.parse_args()
    for image in opts.images:
        with tempfile.TemporaryDirectory(prefix="wm6108-image-") as tmp:
            tmp = Path(tmp)
            with gzip.open(image, "rb") as stream:
                mbr = stream.read(512)
                assert mbr[510:512] == b"\x55\xaa", image
                partitions = []
                for index in [0, 1]:
                    start, sectors = struct.unpack_from("<II", mbr, 446 + index * 16 + 8)
                    assert start and sectors
                    partitions.append((start * 512, sectors * 512))
                start, size = partitions[0]
                stream.seek(start)
                boot = tmp / "boot.fat"
                boot.write_bytes(stream.read(size))
                start, size = partitions[1]
                stream.seek(start)
                superblock = stream.read(96)
                assert superblock[:4] == b"hsqs", (image, "not squashfs")
                used = struct.unpack_from("<Q", superblock, 40)[0]
                assert 96 <= used <= size
                root = tmp / "root.squashfs"
                root.write_bytes(superblock + stream.read(used - 96))
            def read(path):
                return command(opts.unsquashfs, "-cat", str(root), path)
            assert read("etc/wm6108-spi-reset.conf") == b"enabled=0\n"
            helper = read("usr/libexec/wm6108-spi-reset")
            assert helper[:4] == b"\x7fELF" and b"TEST_ROOT" not in helper
            assert b"target bound or live node unavailable" in helper
            assert b"GPIO unavailable/busy or SPI driver became active" in helper
            stub = read("morse/scripts/chipreset.sh")
            assert b"generic reset disabled on Raspberry Pi" in stub
            assert b"unbind" not in stub and b"rmmod" not in stub
            init = read("etc/init.d/wm6108-spi-reset")
            assert b"START=09" in init and b"start() { :; }" in init
            listing = command(opts.unsquashfs, "-ll", str(root)).decode()
            assert "etc/rc.d/S09wm6108-spi-reset" in listing
            # Some install orders can retain the harmless vendor init. Its entry
            # point must always be the verified no-op above, never the old helper.
            assert "libgpiod.so.3" in listing and "libfdt.so.1" in listing
            def read_boot(name):
                target = tmp / name
                subprocess.run([opts.mcopy, "-i", str(boot), "::" + name, str(target)], check=True)
                return target.read_text()
            boot_config = read_boot("config.txt")
            distro = read_boot("distroconfig.txt")
            assert "distroconfig.txt" in boot_config
            if "mm6108-spi" in image.name:
                assert "dtoverlay=mm610x-spi" in distro
                overlay = tmp / "mm610x-spi.dtbo"
                subprocess.run([opts.mcopy, "-i", str(boot), "::overlays/mm610x-spi.dtbo", str(overlay)], check=True)
                assert command("fdtget", str(overlay), "/fragment@0/__overlay__/mm6108@0", "openmanet,wm6108-reset").strip() == b""
            elif "mm8108-usb" in image.name:
                assert "dtoverlay=mm610x" not in distro and "dtoverlay=mm810x" not in distro
            elif "mm6108-sdio" in image.name:
                assert "dtoverlay=mm610x-spi" not in distro
            else:
                raise AssertionError(f"unknown profile: {image}")
            print("PASS", image.name, "helper/default-off/service/dependencies/vendor-noop/transport-config")
            print("SHA256", hashlib.file_digest(image.open("rb"), "sha256").hexdigest()
                  if hasattr(hashlib, "file_digest") else hashlib.sha256(image.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
