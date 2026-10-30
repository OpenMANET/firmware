#!/usr/bin/env bash
# Resolve the standard image first, then omit optional package-repository builds.
set -euo pipefail
resolve_config() {
  mkdir -p tmp
  make defconfig 2>&1 | tee tmp/morse-trial-defconfig.log
  if grep -q 'error:' tmp/morse-trial-defconfig.log; then
    echo 'Kconfig reported an error despite make succeeding' >&2
    exit 1
  fi
}
radio=${1:-usb}
case "$radio" in
  usb) board=rpi4-mm8108-2.2-trial ;;
  spi) board=rpi4-mm6108-2.2-trial ;;
  *) echo "usage: configure.sh [usb|spi]" >&2; exit 1 ;;
esac
./scripts/mm8108-trial/apply-board-patches.sh
# Existing builders may still link the old Morse-feed camera package.
# -f overrides core packages only; uninstall the stale feed link first.
if [[ -L package/feeds/morse/camera-onvif-server ]]; then
  ./scripts/feeds uninstall camera-onvif-server
fi
./scripts/feeds install -f -p openmanet camera-onvif-server
awk 1 boards/common/*_diffconfig "boards/$board/"*_diffconfig > .config
if [[ -n ${MORSE_TRIAL_EXTERNAL_TOOLCHAIN:-} ]]; then
  ./scripts/ext-toolchain.sh --toolchain "$MORSE_TRIAL_EXTERNAL_TOOLCHAIN" --overwrite-config --config bcm27xx/bcm2711
fi
resolve_config
cp .config tmp/mm8108-trial-full.config
python3 scripts/mm8108-trial/prune-config.py "$radio"
resolve_config
python3 scripts/mm8108-trial/check-config.py "$radio"
