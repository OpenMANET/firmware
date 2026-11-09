#
# Copyright 2025 Gateworks
#
# This is free software, licensed under the GPL 2 license.
#

include $(TOPDIR)/rules.mk

PKG_NAME:=mm8108-driver
PKG_RELEASE:=1.diag2

PKG_VERSION:=2.2.3
PKG_LICENSE:=GPLv2
PKG_LICENSE_FILES:=LICENSE
PKG_SOURCE_VERSION:=270da4733cd4dc62e78e897746f98f6dfb3bef80
PKG_SOURCE_URL:=https://github.com/MorseMicro/morse_driver.git
PKG_SOURCE:=$(PKG_NAME)-$(PKG_SOURCE_VERSION).tar.zst
PKG_MIRROR_HASH:=5960e498da1ce76c4aa4e126ff13fe1ab97a47954ca3500598895072b186346d
PKG_SOURCE_PROTO:=git

PKG_MAINTAINER:=OpenMANET
PKG_BUILD_PARALLEL:=1

include $(INCLUDE_DIR)/kernel.mk
include $(INCLUDE_DIR)/package.mk

# Extract mac80211 version
MAC80211_VERSION:=v$(shell grep '^PKG_VERSION:=' $(TOPDIR)/package/kernel/mac80211/Makefile | cut -d'=' -f2 | head -1)
MORSE_VERSION:=$(PKG_VERSION)-g$(call version_abbrev,$(PKG_SOURCE_VERSION))-diag2

define KernelPackage/mm8108
  SUBMENU:=Wireless Drivers
  TITLE:=Morse Micro WIFI HaLow mm8108 USB/SDIO driver
  DEPENDS:= +kmod-mac80211 +kmod-lib-crc7 +kmod-usb-core +kmod-mmc
  FILES:= $(PKG_BUILD_DIR)/morse.ko
  AUTOLOAD:=$(call AutoProbe,morse)
  MODPARAMS.morse:=country=US
  PROVIDES:=kmod-morse
endef

define KernelPackage/mm8108/description
	This package contains the wireless driver for the Morse Micro MM8108 chip USB and SDIO interfaces.
endef

MORSE_MAKEDEFS += \
  MORSE_VERSION="$(MORSE_VERSION)" \
  KERNEL_SRC=$(LINUX_DIR) \
  CONFIG_BACKPORT_VERSION=$(MAC80211_VERSION) \
  CONFIG_MORSE_USB=y \
  CONFIG_MORSE_SDIO=y \
  CONFIG_MORSE_SDIO_ALIGNMENT=4 \
  CONFIG_MORSE_SPI=n \
  CONFIG_MORSE_USER_ACCESS=y \
  CONFIG_MORSE_POWERSAVE_MODE=0 \
  CONFIG_MORSE_VENDOR_COMMAND=y \
  CONFIG_MORSE_RC=y \
  CONFIG_MORSE_MONITOR=y \
  CONFIG_MORSE_DEBUGFS=y \
  CONFIG_MORSE_COUNTRY=US \
  CONFIG_WLAN_VENDOR_MORSE=m

NOSTDINC_FLAGS = \
	-I$(PKG_BUILD_DIR) \
	-I$(STAGING_DIR)/usr/include/mac80211-backport/uapi \
	-I$(STAGING_DIR)/usr/include/mac80211-backport \
	-I$(STAGING_DIR)/usr/include/mac80211/uapi \
	-I$(STAGING_DIR)/usr/include/mac80211 \
	-include backport/autoconf.h \
	-include backport/backport.h

include $(INCLUDE_DIR)/kernel-defaults.mk

define Build/Compile
	$(MAKE) $(MORSE_MAKEDEFS) $(PKG_JOBS) -C "$(LINUX_DIR)" \
		$(KERNEL_MAKE_FLAGS) \
		M="$(PKG_BUILD_DIR)" \
		NOSTDINC_FLAGS="$(NOSTDINC_FLAGS)" \
		modules
endef

$(eval $(call KernelPackage,mm8108))
