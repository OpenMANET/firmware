include $(TOPDIR)/rules.mk

PKG_NAME:=ht-service
PKG_VERSION:=1.0
PKG_RELEASE:=1

include $(INCLUDE_DIR)/package.mk

define Package/ht-service
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=Heltec HT-HD01 LED and button service
  DEPENDS:=+gpioctl-sysfs +swconfig
  PKGARCH:=all
endef

define Package/ht-service/description
  Heltec HT-HD01-V2 RGB LED indicator and button handler.
  Controls the RGB LED (GPIO 41/42/43) to show device status:
  boot, connection state, AP/STA mode, ethernet/USB target.
  Handles the button (GPIO 38) for mode switching, config mode,
  and factory reset.
endef

define Build/Compile
endef

define Package/ht-service/install
	$(INSTALL_DIR) $(1)/bin
	$(INSTALL_BIN) ./files/bin/gpio $(1)/bin/gpio

	$(INSTALL_DIR) $(1)/ht-service
	$(INSTALL_BIN) ./files/ht-service/rgb $(1)/ht-service/rgb
	$(INSTALL_BIN) ./files/ht-service/checkkey $(1)/ht-service/checkkey
	$(INSTALL_BIN) ./files/ht-service/checkstatus $(1)/ht-service/checkstatus
	$(INSTALL_BIN) ./files/ht-service/config.sh $(1)/ht-service/config.sh
	$(INSTALL_DATA) ./files/ht-service/product $(1)/ht-service/product

	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./files/etc/init.d/checkkey $(1)/etc/init.d/checkkey
	$(INSTALL_BIN) ./files/etc/init.d/checkstat $(1)/etc/init.d/checkstat
endef

$(eval $(call BuildPackage,ht-service))
