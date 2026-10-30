#!/usr/bin/env bash
# Apply the same feed fixes as the production RPi4 board, failing on drift.
set -euo pipefail
for patch_file in patches/ekh-bcm2711/*.patch; do
  if patch --dry-run --forward --batch --fuzz=0 -p1 < "$patch_file" >/dev/null 2>&1; then
    patch --forward --batch --fuzz=0 -p1 < "$patch_file"
  elif patch --dry-run --forward --batch --fuzz=0 -R -p1 < "$patch_file" >/dev/null 2>&1; then
    echo "Already applied: $patch_file"
  else
    echo "Cannot apply board feed patch cleanly: $patch_file" >&2
    exit 1
  fi
done
