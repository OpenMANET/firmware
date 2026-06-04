FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV FORCE_UNSAFE_CONFIGURE=1

RUN apt-get update -q && apt-get install -y --no-install-recommends \
    build-essential clang flex g++ gawk \
    git gettext ca-certificates \
    libncurses5-dev libssl-dev python3-setuptools \
    rsync unzip golang-go zlib1g-dev swig file wget \
    libnl-3-dev libnl-genl-3-dev libgps-dev libcap-dev \
    pkg-config libopus-dev libopusfile-dev portaudio19-dev \
    net-tools libpcre3-dev libpcre3 upx-ucl perl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY . .
RUN git config --global --add safe.directory /build

RUN ./scripts/openmanet_setup.sh -i -b ekh-bcm2712
RUN make download -j$(nproc)
RUN make -j$(nproc) V=s
