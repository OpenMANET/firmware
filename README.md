# OpenMANET Firmware
OpenMANET firmware is based on OpenWRT.

## Dependencies

To build the OpenMANET OpenWrt, you need a working Linux environment. This has been tested with Ubuntu 24.04 and higher.

Install build environment packages with
```
> sudo apt update
> sudo apt install build-essential clang flex g++ gawk gcc-multilib g++-multilib git gettext \
  libncurses5-dev libssl-dev python3-setuptools rsync unzip zlib1g-dev swig file wget libnl-3-dev \
  libnl-genl-3-dev libgps-dev libcap-dev pkg-config libopus-dev \
  libopusfile-dev portaudio19-dev net-tools libpcre3-dev libpcre3
```

## Usage

Run the `./scripts/openmanet_setup.sh` script to configure the build for your board of choice.

For example, Using seeedstudio's WiFi Halow Modules on Raspberry Pi.
```
> ./scripts/openmanet_setup.sh -i -b ekh01
```

For the Gateworks 7500
```
> ./scripts/openmanet_setup.sh -i -b gw7500
```

Run this to download all dependencies before starting a build.  It will make building more reliable.
```
> make download
```

After configuration is complete, run the build with
```
> make -j8
```

For verbose compilation, consider using
```
> make -j8 V=sc 2>&1 | tee log.txt
```

Once the build is complete a compiled image can be found in `bin/target/<platform>/<target>/`
