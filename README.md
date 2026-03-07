# OpenMANET Firmware
A MANET (Mobile Ad-Hoc Network) is a self-forming wireless mesh where each node connects directly without centralized infrastructure. This technology is especially useful in the civilian space for search and rescue, disaster response, airsoft events, and any disconnected communications scenario. Designed to be budget-friendly with excellent long-range performance. The build is designed to integrate with ATAK over multicast, but works equally well over standard IP and internet links.

**Software Specifications**
- OpenWRT 24.10 Base
- Linux Kernel 6.6.102
- Wifi Drivers back-ported from 6.12.6
- Morse Micro Drivers 1.16

## Supported Hardware
### SBC
| Device            | Status    | Onboard WiFi      | Notes                        |
|-------------------|-----------|-------------------|------------------------------|
| Raspberry Pi 4    | ✅ Tested | ✅ Working (SPI)  | Onboard Wifi Only in AP Mode |
| Raspberry Pi CM4  | ✅ Tested | ✅ Working (SPI)  | Onboard Wifi Only in AP Mode |
| Raspberry Pi 3B   | ✅ Tested | ✅ Working (SPI)  | Onboard Wifi Only in AP Mode |
| Raspberry Pi 2W   | ✅ Tested | ✅ Working (SPI)  | Onboard Wifi Only in AP Mode |
| HaLowLink 2       | ✅ Tested | ✅ Working        | Storage limited              |

### HaLow

| Device              | Status    | Interface  | MM Chipset | Notes                                 |
|---------------------|-----------|------------|------------|---------------------------------------|
| Wio-WM6108 + WM1302 | ✅ Tested |   SPI      | 6108       | Best performing with HaLow currently  |
| Silex SX-SDMAH      | ✅ Tested |   SDIO     | 6108       | Very low dBm and high amount of noise |
| Alfa AHPI6108E      | ✅ Tested |   SDIO     | 6108       | Decent performance                    |
| TBD                 | ✅ Tested |   USB      | 8108       | Great performance                     |

## Building OpenMANET Firmware
### Dependencies

To build the OpenMANET OpenWrt, you need a working Linux environment. This has been tested with Ubuntu 24.04 and higher.

Install build environment packages with
```
> sudo apt update
> sudo apt install build-essential clang flex g++ gawk gcc-multilib g++-multilib git gettext \
  libncurses5-dev libssl-dev python3-setuptools rsync unzip golang-go zlib1g-dev swig file wget libnl-3-dev \
  libnl-genl-3-dev libgps-dev libcap-dev pkg-config libopus-dev \
  libopusfile-dev portaudio19-dev net-tools libpcre3-dev libpcre3 upx-ucl
```

### Usage

Run the `./scripts/openmanet_setup.sh` script to configure the build for your board of choice.

For example, Using seeedstudio's WiFi Halow Modules on Raspberry Pi4.
```
> ./scripts/openmanet_setup.sh -i -b ekh-bcm2711
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

### Extending OpenMANET

If you want to contribute a custom package for OpenMANET, and can build it as an OpenWRT package, feel free to open a pull request in the [OpenMANET Packages Repository](https://github.com/OpenMANET/packages).
