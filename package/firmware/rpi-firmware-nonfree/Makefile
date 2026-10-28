# SPDX-License-Identifier: GPL-2.0-or-later

include $(TOPDIR)/rules.mk

PKG_NAME:=rpi-firmware-nonfree
PKG_VERSION:=20240709
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/RPi-Distro/firmware-nonfree.git
PKG_SOURCE_VERSION:=c91cd2804cf7463aab913e7247c176049f16bbd6
PKG_MIRROR_HASH:=8c704d2193fecd9a243ca94503e3f8fb6b2f69a9cf8be898d7176f9ff5e23964

PKG_LICENSE:=Synaptics
PKG_LICENSE_FILES:=debian/copyright

include $(INCLUDE_DIR)/package.mk

define Package/brcmfmac-firmware-43430b0-sdio
  SECTION:=firmware
  CATEGORY:=Firmware
  TITLE:=Raspberry Pi BCM43430 B0 FullMAC SDIO firmware
  URL:=https://github.com/RPi-Distro/firmware-nonfree
endef

define Build/Compile
	true
endef

define Package/brcmfmac-firmware-43430b0-sdio/install
	$(INSTALL_DIR) $(1)/lib/firmware/brcm
	$(INSTALL_DATA) \
		$(PKG_BUILD_DIR)/debian/config/brcm80211/brcm/brcmfmac43436-sdio.bin \
		$(1)/lib/firmware/brcm/
	$(INSTALL_DATA) \
		$(PKG_BUILD_DIR)/debian/config/brcm80211/brcm/brcmfmac43436-sdio.clm_blob \
		$(1)/lib/firmware/brcm/
	$(INSTALL_DATA) \
		$(PKG_BUILD_DIR)/debian/config/brcm80211/brcm/brcmfmac43436-sdio.txt \
		$(1)/lib/firmware/brcm/
	$(LN) \
		brcmfmac43436-sdio.bin \
		$(1)/lib/firmware/brcm/brcmfmac43430b0-sdio.raspberrypi,model-zero-2-w.bin
	$(LN) \
		brcmfmac43436-sdio.clm_blob \
		$(1)/lib/firmware/brcm/brcmfmac43430b0-sdio.raspberrypi,model-zero-2-w.clm_blob
	$(LN) \
		brcmfmac43436-sdio.txt \
		$(1)/lib/firmware/brcm/brcmfmac43430b0-sdio.raspberrypi,model-zero-2-w.txt
endef

$(eval $(call BuildPackage,brcmfmac-firmware-43430b0-sdio))
