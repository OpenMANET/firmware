#!/usr/bin/env bash
# Resolve the standard image first, then omit optional package-repository builds.
set -euo pipefail
radio=${1:-usb}
case "$radio" in
  usb) board=rpi4-mm8108-2.2-trial ;;
  spi) board=rpi4-mm6108-2.2-trial ;;
  *) echo "usage: configure.sh [usb|spi]" >&2; exit 1 ;;
esac
awk 1 boards/common/*_diffconfig "boards/$board/"*_diffconfig > .config
if [[ -n ${MORSE_TRIAL_EXTERNAL_TOOLCHAIN:-} ]]; then
  ./scripts/ext-toolchain.sh --toolchain "$MORSE_TRIAL_EXTERNAL_TOOLCHAIN" --overwrite-config --config bcm27xx/bcm2711
fi
make defconfig
cp .config tmp/mm8108-trial-full.config
python3 scripts/mm8108-trial/prune-config.py "$radio"
make defconfig
python3 scripts/mm8108-trial/check-config.py "$radio"
