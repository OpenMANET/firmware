#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "=== [1/4] Installing dependencies ==="
apt-get update -q
apt-get install -y --no-install-recommends \
  build-essential clang flex g++ gawk \
  git gettext ca-certificates \
  libncurses5-dev libssl-dev python3-setuptools \
  rsync unzip golang-go zlib1g-dev swig file wget \
  libnl-3-dev libnl-genl-3-dev libgps-dev libcap-dev \
  pkg-config libopus-dev libopusfile-dev portaudio19-dev \
  net-tools libpcre3-dev libpcre3 upx-ucl

# gcc-multilib only exists on x86_64 (32-bit shim libs not available on arm64)
if dpkg --print-architecture | grep -q amd64; then
  apt-get install -y --no-install-recommends gcc-multilib g++-multilib
fi

echo "=== [2/4] Configuring build for ekh-bcm2712 ==="
git config --global --add safe.directory /build
./scripts/openmanet_setup.sh -i -b ekh-bcm2712

echo "=== [3/4] Downloading sources ==="
make download -j"$(nproc)"

echo "=== [4/4] Building firmware ==="
make -j"$(nproc)" V=s 2>&1 | tee build.log

echo ""
echo "=== Build complete ==="
find bin/targets/bcm27xx/bcm2712/ -name "*.img.gz" | sort
