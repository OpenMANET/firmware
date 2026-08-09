#
# Copyright 2023 Morse Micro
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

include $(TOPDIR)/rules.mk


PKG_NAME:=persistent-vars-storage-bcm2712
PKG_RELEASE=1

PKG_MAINTAINER:=Morse Micro

include $(INCLUDE_DIR)/package.mk

define Package/persistent-vars-storage-bcm2712
        SECTION:=Utilities
  CATEGORY:=Morse Micro
  SUBMENU:=Hardware
        PROVIDES:=persistent-vars-storage
        TITLE:=Reads (or maybe writes in future) key-value pairs from(/into) the RPi 5 EEPROM memory
        DEPENDS:= +bcm27xx-userland @TARGET_bcm27xx_bcm2712
endef

define Build/Compile

endef

define Package/persistent-vars-storage-bcm2712/install
        $(INSTALL_DIR) $(1)/sbin
        $(INSTALL_BIN) ./files/sbin/persistent_vars_storage.sh $(1)/sbin/persistent_vars_storage.sh
endef

$(eval $(call BuildPackage,persistent-vars-storage-bcm2712))
