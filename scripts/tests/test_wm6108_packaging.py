#!/usr/bin/env python3
"""Test common feed patch and actual bundle install recipe in disposable roots.
Never run a target service or maintainer script against the host root.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages", type=Path, required=True)
    opts = parser.parse_args()
    fw = Path(__file__).resolve().parents[2]
    feed = fw / "feeds/morse"
    relative = "hardware/morse-bundle"
    with tempfile.TemporaryDirectory(prefix="wm6108-packaging-") as temp:
        tmp = Path(temp)
        target = tmp / "feeds/morse" / relative
        target.parent.mkdir(parents=True)
        shutil.copytree(feed / relative, target)
        original = subprocess.check_output(["git", "-C", str(feed), "show", "HEAD:" + relative + "/Makefile"])
        (target / "Makefile").write_bytes(original)
        if (target / "files/bcm27xx").exists(): shutil.rmtree(target / "files/bcm27xx")
        shutil.copytree(fw / "patches/common", tmp / "patches/common")
        command = ["sh", str(fw / "scripts/openmanet_patch_common.sh")]
        subprocess.run(["patch", "--dry-run", "--batch", "--forward", "-p1"], cwd=tmp,
                       input=(tmp / "patches/common/0001-bcm27xx-disable-generic-morse-reset.patch").read_bytes(), check=True)
        subprocess.run(command, cwd=tmp, check=True)
        applied = (target / "Makefile").read_bytes()
        subprocess.run(command, cwd=tmp, check=True, capture_output=True)
        assert (target / "Makefile").read_bytes() == applied
        print("PASS mandatory patch: applies and is idempotent")

        recipe = applied.decode().split("define Package/morse-bundle/install\n", 1)[1].split("\nendef", 1)[0]
        bsp_make = (opts.packages / "boards/bsp-bcm271x/Makefile").read_text()
        postinst = bsp_make.split("define Package/bsp-bcm271x/postinst\n", 1)[1].split("\nendef", 1)[0].replace("$$", "$")
        script = tmp / "bsp-postinst"
        script.write_text(postinst)
        for board in [True, False]:
            root = tmp / ("pi-root" if board else "other-root")
            makefile = target / "test-install.mk"
            makefile.write_text("CONFIG_TARGET_bcm27xx:=" + ("y" if board else "") + "\n" +
                                "INSTALL_DIR:=install -d\nINSTALL_BIN:=install -m0755\nINSTALL_DATA:=install -m0644\n" +
                                "define bundle_install\n" + recipe + "\nendef\nall:\n\t$(call bundle_install," + str(root) + ")\n")
            install = ["make", "-f", str(makefile)]
            subprocess.run(install, cwd=target, check=True, capture_output=True)
            reset = root / "morse/scripts/chipreset.sh"
            if not board:
                assert reset.read_bytes() == (target / "files/morse/scripts/chipreset.sh").read_bytes()
                print("PASS non-Pi bundle keeps upstream reset policy")
                continue
            assert reset.read_bytes() == (target / "files/bcm27xx/chipreset.sh").read_bytes()
            assert "unbind" not in reset.read_text() and "rmmod" not in reset.read_text()
            subprocess.run(["busybox", "ash", str(reset)], check=True, capture_output=True)
            # Stub rc.common in the fixture, then execute the actual BSP postinst
            # with a nonempty IPKG_INSTROOT. The host /etc is never used.
            rc = root / "etc/rc.common"
            rc.write_text('#!/bin/sh\nexit 0\n')
            rc.chmod(0o755)
            env = {**os.environ, "IPKG_INSTROOT": str(root)}
            subprocess.run(["busybox", "ash", str(script)], env=env, check=True)
            assert not (root / "etc/init.d/morsechipreset").exists()
            subprocess.run(install, cwd=target, check=True, capture_output=True)
            assert reset.read_bytes() == (target / "files/bcm27xx/chipreset.sh").read_bytes()
            subprocess.run(["busybox", "ash", str(script)], env=env, check=True)
            assert not (root / "etc/init.d/morsechipreset").exists()
            print("PASS Pi bundle/BSP install and reinstall ordering: generic reset remains a no-op")

        (target / "Makefile").write_text("incompatible upstream change\n")
        assert subprocess.run(command, cwd=tmp, capture_output=True).returncode != 0
        print("PASS mandatory patch fails closed on incompatible source")

    init = opts.packages / "boards/bsp-bcm271x/files/etc/init.d/wm6108-spi-reset"
    subprocess.run(["busybox", "ash", "-n", str(init)], check=True)
    subprocess.run(["busybox", "ash", "-c", '. "$1"; start; stop; start', "test", str(init)], check=True)
    assert "START=09" in init.read_text()
    print("PASS init syntax and non-boot actions are no-ops")


if __name__ == "__main__":
    main()
