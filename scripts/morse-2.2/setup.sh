#!/usr/bin/env bash
# Run in a fresh firmware checkout; packages must be the matching 2.2 branch.
set -euo pipefail
packages=$(realpath "${1:?usage: setup.sh /path/to/packages}")
[[ -f "$packages/morse-micro/mm8108-driver/Makefile" ]]
[[ ! -e .config && ! -e feeds.conf ]] || { echo 'Use a fresh checkout (.config/feeds.conf already exists)' >&2; exit 1; }
[[ "$packages" != *' '* ]] || { echo 'Package path cannot contain spaces' >&2; exit 1; }
revision=$(cat scripts/morse-2.2/packages.rev)
[[ "$(git -C "$packages" rev-parse HEAD)" == "$revision" ]] || { echo "Expected packages commit $revision" >&2; exit 1; }
[[ -z "$(git -C "$packages" status --porcelain)" ]] || { echo 'Packages checkout must be clean' >&2; exit 1; }
{ printf 'src-git openmanet file://%s^%s\n' "$packages" "$revision"; sed '/^src-git openmanet /d' feeds.conf.default; } > feeds.conf
./scripts/openmanet_setup.sh -i
./scripts/morse-2.2/configure.sh "${2:-usb}"
