#!/usr/bin/env bash
# Configure only the trial image and dependencies, not the optional package repo.
set -euo pipefail
common=()
for fragment in boards/common/*_diffconfig; do
    [[ ${fragment##*/} == kitchensink_diffconfig ]] || common+=("$fragment")
done
awk 1 "${common[@]}" boards/rpi4-mm8108-2.1-trial/*_diffconfig > .config
make defconfig
python3 scripts/mm8108-trial/check-config.py
