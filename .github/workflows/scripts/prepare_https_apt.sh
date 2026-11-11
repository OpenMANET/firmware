#!/bin/sh
set -eu

# Select a reachable Ubuntu archive before apt's much slower per-package retries.
# All packages remain checked against the runner's existing Ubuntu signing keys.
mirror=
for candidate in https://mirrors.edge.kernel.org/ubuntu https://archive.ubuntu.com/ubuntu; do
    if sudo curl -fsS --connect-timeout 5 --max-time 15 \
        "$candidate/dists/noble/InRelease" -o /dev/null; then
        mirror=$candidate
        break
    fi
done
[ -n "$mirror" ] || { echo 'No reachable HTTPS Ubuntu archive' >&2; exit 1; }
echo "Using Ubuntu archive: $mirror"

# Cover both deb822/list sources and mirror+file mirror lists.
for source_file in /etc/apt/sources.list /etc/apt/sources.list.d/*.list \
                   /etc/apt/sources.list.d/*.sources /etc/apt/apt-mirrors*.txt; do
    [ -f "$source_file" ] || continue
    sudo sed -i \
        -e "s|http://azure.archive.ubuntu.com/ubuntu|$mirror|g" \
        -e "s|http://archive.ubuntu.com/ubuntu|$mirror|g" \
        -e "s|http://security.ubuntu.com/ubuntu|$mirror|g" \
        -e "s|https://archive.ubuntu.com/ubuntu|$mirror|g" \
        -e "s|https://security.ubuntu.com/ubuntu|$mirror|g" \
        "$source_file"
done
printf '%s\n' 'Acquire::ForceIPv4 "true";' 'Acquire::http::Timeout "10";' \
    'Acquire::https::Timeout "10";' 'Acquire::Retries "1";' \
    | sudo tee /etc/apt/apt.conf.d/99-openmanet-build-network > /dev/null
