# OpenMANET Package Comparison: RPi4 (Stock) vs HaLow Link 2

This document details what packages were removed from the stock OpenMANET
RPi4 build to fit on the HaLow Link 2's 32MB flash, and what was added
for device-specific support.

**Stock RPi4 image**: ~120MB+ (no flash constraint)
**HaLow Link 2 image**: ~23MB squashfs (31.4MB firmware partition, ~8MB free overlay)

---

## Packages REMOVED (disabled to save space)

### WiFi Firmware & Drivers (~15MB saved)
These are for WiFi chips not present on the HaLow Link 2:

| Package | Description | Why Removed |
|---------|-------------|-------------|
| kmod-ath10k, ath10k-firmware-* | Qualcomm 802.11ac | Not on device |
| kmod-ath11k, ath11k-firmware-* | Qualcomm 802.11ax | Not on device |
| kmod-ath9k-common, kmod-ath9k-htc | Atheros 802.11n | Not on device |
| kmod-ath3k, kmod-ath5k, kmod-ath6kl-* | Legacy Atheros | Not on device |
| kmod-iwlwifi, iwlwifi-firmware-* | Intel WiFi | Not on device |
| kmod-mt7915e, kmod-mt7915-firmware | MediaTek WiFi 6 | Not on device |
| kmod-mt7916-firmware | MediaTek WiFi 6E | Not on device |
| kmod-rtw88-*, kmod-rtw89-* | Realtek WiFi 5/6 | Not on device |
| kmod-rtl8192*, kmod-rtl8723*, kmod-rtl8812*, kmod-rtl8821* | Realtek legacy | Not on device |
| kmod-owl-loader | QCA95xx EEPROM | Not on device |
| kmod-brcmfmac, brcmfmac-firmware-* | Broadcom WiFi | Not on device |

### Audio/Sound (~2MB saved)
| Package | Description | Why Removed |
|---------|-------------|-------------|
| alsa-lib, alsa-ucm-conf, alsa-utils | ALSA audio framework | No audio hardware use case |
| portaudio | Cross-platform audio I/O | No PTT voice on this device |
| kmod-sound-core | Linux sound subsystem | No audio needed |
| kmod-usb-audio | USB audio devices | No audio needed |
| kmod-sound-soc-* | SoC audio codecs | No audio needed |
| libopus, libopusfile | Opus audio codec | No audio needed |

### Filesystems (~1.5MB saved)
| Package | Description | Why Removed |
|---------|-------------|-------------|
| kmod-fs-btrfs | Btrfs filesystem | Not needed for flash storage |
| kmod-fs-ext4 | ext4 filesystem | Not needed (squashfs+jffs2) |
| kmod-fs-f2fs | Flash-friendly FS | Not needed |
| kmod-fs-ntfs, kmod-fs-ntfs3 | Windows NTFS | Not needed |
| kmod-fs-xfs | XFS filesystem | Not needed |
| kmod-fs-hfs, kmod-fs-hfsplus | macOS HFS | Not needed |
| kmod-fs-isofs | CD-ROM ISO9660 | Not needed |
| kmod-fs-reiserfs, kmod-fs-jfs | Legacy filesystems | Not needed |
| f2fs-tools | F2FS utilities | Not needed |

### USB Gadget Mode (~0.5MB saved)
| Package | Description | Why Removed |
|---------|-------------|-------------|
| kmod-usb-gadget | USB gadget framework | No USB device mode |
| kmod-usb-gadget-eth | USB Ethernet gadget | No USB device mode |
| kmod-usb-gadget-serial | USB serial gadget | No USB device mode |
| kmod-usb-gadget-mass-storage | USB mass storage gadget | No USB device mode |
| kmod-usb-gadget-hid | USB HID gadget | No USB device mode |
| kmod-usb-gadget-ncm | USB NCM gadget | No USB device mode |

### USB Serial/Network Drivers
| Package | Description | Why Removed |
|---------|-------------|-------------|
| kmod-usb-serial-edgeport | Edgeport USB serial | Missing firmware dep |
| kmod-usb-net-rtl8152 | Realtek USB Ethernet | Missing firmware dep |
| kmod-usb-net-lan78xx | Microchip USB Ethernet | RPi-specific |
| kmod-usb-net-smsc75xx | SMSC USB Ethernet | RPi-specific |
| kmod-usb-net-aqc111 | Aquantia USB Ethernet | Not needed |

### Video/Camera
| Package | Description | Why Removed |
|---------|-------------|-------------|
| kmod-video-core | V4L2 video framework | No camera use case |
| kmod-video-codec-bcm2835 | RPi video codec | RPi-specific hardware |
| v4l2loopback | Virtual video device | No video needed |

### Networking (Optional)
| Package | Description | Why Removed |
|---------|-------------|-------------|
| tailscale | VPN mesh overlay | Saves ~10MB, optional feature |
| docker | Container runtime | Too large for 32MB flash |

### Hardware Monitoring (kmod-hwmon-*)
All 48+ hardware monitoring kernel modules removed - these are for
temperature/voltage/fan sensors on desktop/server hardware not present
on the MT7621.

### Development/Scripting
| Package | Description | Why Removed |
|---------|-------------|-------------|
| python3 (all variants) | Python interpreter | Too large, not needed at runtime |
| collectd (all modules) | Statistics collection | Not needed |
| glib2, libffi, libltdl | Development libraries | Only needed by removed packages |

### Miscellaneous
| Package | Description | Why Removed |
|---------|-------------|-------------|
| kmod-ftdi-usb-spi | FTDI USB-SPI bridge | Gateworks-specific, build failure |
| kmod-google-firmware | Google Coreboot | Not applicable |
| bzip2 | Compression utility | Not needed |
| wireshark | Packet analyzer | Too large |

---

## Packages ADDED (HaLow Link 2 specific)

### Device Support
| Package | Description | Why Added |
|---------|-------------|-----------|
| kmod-sdhci-mt7620 | MediaTek SDIO host controller | Required for MM8108 HaLow chip |
| kmod-mmc | MMC/SD card support | SDIO bus for HaLow |
| kmod-mt7603 | MediaTek MT7603 WiFi | 2.4GHz WiFi on device |

### HaLow Radio (from morse-feed)
| Package | Description |
|---------|-------------|
| kmod-morse | MorseMicro HaLow (802.11ah) driver |
| netifd-morse | MorseMicro network interface daemon |
| morse-fw-6108 | MM6108 firmware |
| morse-fw-8108 | MM8108 firmware |
| hostapd_s1g | HaLow access point daemon |
| wpa_supplicant_s1g | HaLow WPA supplicant |
| morsecli | MorseMicro CLI tools |
| morse-leds | LED control for MorseMicro devices |
| morse-button | Button handler |
| morse-mode | Mode switching (AP/STA) |
| morse-boot-prints | Boot diagnostics |
| morse-bundle | MorseMicro bundle package |
| smart-manager | Device management |
| dpp-handler | DPP provisioning |

### Kernel Configs Added
| Config | Description |
|--------|-------------|
| CONFIG_PWM=y | PWM subsystem (for RGB LEDs) |
| CONFIG_PWM_GPIO=y | GPIO-based software PWM |
| CONFIG_LEDS_CLASS_MULTICOLOR=y | Multicolor LED class |
| CONFIG_LEDS_PWM_MULTICOLOR=y | PWM-driven multicolor LEDs |
| CONFIG_LEDS_PWM=y | PWM-driven LEDs |

---

## Packages KEPT (core functionality preserved)

### Mesh Networking (full stack)
- batman-adv, batctl-full, alfred
- openmanetd (with MIPS32 SQLite fix)
- kmod-batman-adv

### LuCI Web Interface (full)
- luci-base, luci-mod-admin-full
- luci-mod-network, luci-mod-status, luci-mod-system
- luci-app-morseconfig, luci-app-ekhwizards
- luci-theme-openmanetargon
- luci-proto-batman-adv

### Core Networking
- firewall4, nftables
- dnsmasq, odhcpd
- kmod-tun, kmod-vxlan
- relayd, ethtool
- gpsd

### GPIO/I2C/Hardware
- kmod-gpio-pca953x, kmod-leds-gpio
- kmod-i2c-core, i2c-tools
- gpioctl-sysfs, gpiod-tools, libgpiod

### Diagnostics (as modules, =m)
- iperf3
- iio-utils
- tcpdump

---

## Size Impact Summary

| Category | Estimated Savings |
|----------|------------------|
| WiFi firmware (unused chips) | ~15MB |
| Tailscale | ~10MB |
| Audio stack | ~2MB |
| Filesystems | ~1.5MB |
| Docker + dependencies | ~5MB |
| USB gadget/serial drivers | ~0.5MB |
| Hardware monitoring | ~1MB |
| Python + dev libraries | ~3MB |
| Misc (wireshark, collectd, etc.) | ~2MB |
| **Total saved** | **~40MB** |

Stock RPi4 rootfs: ~60MB+ → HaLow Link 2 rootfs: ~20MB
