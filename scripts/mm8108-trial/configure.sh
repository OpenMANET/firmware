#!/usr/bin/env bash
# Keep installed image defaults; omit explicit optional (=m) repository packages.
# Kconfig still selects per-device packages and dependencies automatically.
set -euo pipefail
awk '!/^CONFIG_PACKAGE_[^=]+=m$/' boards/common/*_diffconfig \
    boards/rpi4-mm8108-2.1-trial/*_diffconfig > .config
make defconfig
python3 scripts/mm8108-trial/check-config.py
