#!/bin/sh
# Apply mandatory feed safety patches, including on individual profile builds.
set -eu
for patch_file in patches/common/*.patch; do
	[ -f "$patch_file" ] || continue
	if patch --dry-run --batch --forward -p1 < "$patch_file" >/dev/null 2>&1; then
		patch --batch --forward -p1 < "$patch_file"
	elif patch --dry-run --batch --reverse -p1 < "$patch_file" >/dev/null 2>&1; then
		echo "Already applied: $patch_file"
	else
		echo "Cannot apply required feed patch: $patch_file" >&2
		exit 1
	fi
done
