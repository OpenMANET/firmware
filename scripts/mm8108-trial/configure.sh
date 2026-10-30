#!/usr/bin/env bash
# Resolve the standard image first, then omit optional package-repository builds.
set -euo pipefail
awk 1 boards/common/*_diffconfig boards/rpi4-mm8108-2.2-trial/*_diffconfig > .config
make defconfig
cp .config tmp/mm8108-trial-full.config
python3 scripts/mm8108-trial/prune-config.py
make defconfig
python3 scripts/mm8108-trial/check-config.py
