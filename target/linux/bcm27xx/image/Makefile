# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2012-2019 OpenWrt.org
# Copyright (C) 2016-2017 LEDE project

include $(TOPDIR)/rules.mk
include $(INCLUDE_DIR)/image.mk

DEVICE_VARS += SYSINFO_MODEL SYSINFO_BOARD_NAME DISTROCONFIG_EXTRA

FAT32_BLOCK_SIZE=1024
FAT32_BLOCKS=$(shell echo $$(($(CONFIG_TARGET_KERNEL_PARTSIZE)*1024*1024/$(FAT32_BLOCK_SIZE))))

define Build/Compile
	$(CP) $(LINUX_DIR)/COPYING $(KDIR)/COPYING.linux
endef

### Image scripts ###
define Build/boot-common
	echo $(IMG_PART_SIGNATURE) > $@-partuuid.txt
	sed \
		-e 's#@ROOT@#PARTUUID=$(IMG_PART_SIGNATURE)-02#g' \
		cmdline.txt > $@-cmdline.txt

	rm -f $@.boot
	mkfs.fat -n boot -C $@.boot $(FAT32_BLOCKS)
	mcopy -i $@.boot $(KDIR)/COPYING.linux ::
	mcopy -i $@.boot $(KDIR)/LICENCE.broadcom ::
	mcopy -i $@.boot $@-cmdline.txt ::cmdline.txt
	mcopy -i $@.boot config.txt ::
	mcopy -i $@.boot distroconfig.txt ::
	mcopy -i $@.boot $@-partuuid.txt ::partuuid.txt
	mcopy -i $@.boot $(IMAGE_KERNEL) ::$(KERNEL_IMG)
	$(foreach dts,$(shell echo $(DEVICE_DTS)),mcopy -i $@.boot $(DTS_DIR)/$(dts).dtb ::;)
	mmd -i $@.boot ::/overlays
	mcopy -i $@.boot $(DTS_DIR)/overlays/*.dtbo ::/overlays/
	mcopy -i $@.boot $(DTS_DIR)/overlays/README ::/overlays/
endef

define Build/boot-2708
	mcopy -i $@.boot $(KDIR)/bootcode.bin ::
	mcopy -i $@.boot $(KDIR)/start.elf ::
	mcopy -i $@.boot $(KDIR)/start_cd.elf ::
	mcopy -i $@.boot $(KDIR)/start_x.elf ::
	mcopy -i $@.boot $(KDIR)/fixup.dat ::
	mcopy -i $@.boot $(KDIR)/fixup_cd.dat ::
	mcopy -i $@.boot $(KDIR)/fixup_x.dat ::
endef

define Build/boot-2711
	mcopy -i $@.boot $(KDIR)/start4.elf ::
	mcopy -i $@.boot $(KDIR)/start4cd.elf ::
	mcopy -i $@.boot $(KDIR)/start4x.elf ::
	mcopy -i $@.boot $(KDIR)/fixup4.dat ::
	mcopy -i $@.boot $(KDIR)/fixup4cd.dat ::
	mcopy -i $@.boot $(KDIR)/fixup4x.dat ::
endef

define Build/boot-2710
	mcopy -i $@.boot $(KDIR)/bootcode.bin ::
	mcopy -i $@.boot $(KDIR)/start.elf ::
	mcopy -i $@.boot $(KDIR)/start_cd.elf ::
	mcopy -i $@.boot $(KDIR)/start_x.elf ::
	mcopy -i $@.boot $(KDIR)/fixup.dat ::
	mcopy -i $@.boot $(KDIR)/fixup_cd.dat ::
	mcopy -i $@.boot $(KDIR)/fixup_x.dat ::
endef

define Build/boot-ekh01
	# Put ekh01 model info into device tree (picked up by 01_sysinfo).
	# This uses a custom overlay which accepts parameters (via RPI's __overrides__ mechanism),
	# and writes those parameters into the root of the device tree (as sysinfo-model
	# and sysinfo-board-name).
	# Note that we cannot easily put it on the rootfs, because our multi-profile builds share this
	# (i.e. they only differ in /boot).
	# We can't easily use /boot directly because that's not mounted early in the preinit process.
	# As well as this, we have a custom DISTROCONFIG_EXTRA section which is used to define
	# the necessary SPI/SDIO overlays for the product.

	echo -e '\ndtoverlay=sysinfo,board-name="$(SYSINFO_BOARD_NAME)",model="$(SYSINFO_MODEL)"' | cat boards/ekh01/distroconfig.txt boards/ekh01/distroconfig-$(DISTROCONFIG_EXTRA).txt - | mcopy -o -i $@.boot - ::/distroconfig.txt

endef

define Build/sdcard-img
	SIGNATURE="$(IMG_PART_SIGNATURE)" \
	./gen_rpi_sdcard_img.sh $@ $@.boot $(IMAGE_ROOTFS) \
		$(CONFIG_TARGET_KERNEL_PARTSIZE) $(CONFIG_TARGET_ROOTFS_PARTSIZE)
endef

### Devices ###
define Device/Default
  DEVICE_VENDOR := Raspberry Pi
  KERNEL := kernel-bin
  KERNEL_IMG := kernel.img
  IMAGES := factory.img.gz sysupgrade.img.gz
  IMAGE/sysupgrade.img.gz := boot-common | boot-2708 | sdcard-img | gzip | append-metadata
  IMAGE/factory.img.gz := boot-common | boot-2708 | sdcard-img | gzip
endef

define Device/rpi
  DEVICE_MODEL := A/A+/B/B+/CM/Zero/ZeroW
  DEVICE_DTS := \
	broadcom/bcm2708-rpi-b broadcom/bcm2708-rpi-b-rev1 broadcom/bcm2708-rpi-b-plus \
	broadcom/bcm2708-rpi-cm \
	broadcom/bcm2708-rpi-zero broadcom/bcm2708-rpi-zero-w
  SUPPORTED_DEVICES := \
	rpi-a rpi-a-plus \
	rpi-b rpi-b-plus \
	rpi-cm \
	rpi-zero rpi-zero-w \
	raspberrypi,model-a raspberrypi,model-a-plus \
	raspberrypi,model-b raspberrypi,model-b-plus raspberrypi,model-b-rev2 \
	raspberrypi,compute-module raspberrypi,compute-module-1 \
	raspberrypi,model-zero raspberrypi,model-zero-w
  DEVICE_PACKAGES := \
	cypress-firmware-43430-sdio \
	brcmfmac-nvram-43430-sdio \
	kmod-brcmfmac wpad-basic-mbedtls \
	kmod-i2c-bcm2835 kmod-spi-bcm2835 \
	kmod-spi-bcm2835-aux
endef
ifeq ($(SUBTARGET),bcm2708)
  TARGET_DEVICES += rpi
endif

define Device/rpi-2
  DEVICE_MODEL := 2B/2B 1.2
  DEVICE_VARIANT := (32bit)
  DEVICE_ALT0_VENDOR := Raspberry Pi
  DEVICE_ALT0_MODEL := 3A+/3B/3B+/CM3/Zero2/Zero2W
  DEVICE_ALT0_VARIANT := (32bit)
  DEVICE_ALT1_VENDOR := Raspberry Pi
  DEVICE_ALT1_MODEL := 4B/400/CM4
  DEVICE_ALT1_VARIANT := (32bit)
  DEVICE_DTS := \
	broadcom/bcm2709-rpi-2-b broadcom/bcm2710-rpi-2-b \
	broadcom/bcm2710-rpi-3-b broadcom/bcm2710-rpi-3-b-plus \
	broadcom/bcm2711-rpi-4-b broadcom/bcm2711-rpi-400 \
	broadcom/bcm2710-rpi-cm3 broadcom/bcm2711-rpi-cm4 \
	broadcom/bcm2710-rpi-zero-2 broadcom/bcm2710-rpi-zero-2-w
  SUPPORTED_DEVICES := \
	rpi-2-b \
	rpi-3-a-plus \
	rpi-3-b rpi-3-b-plus \
	rpi-4-b rpi-400 \
	rpi-cm \
	rpi-zero-2 rpi-zero-2-w \
	raspberrypi,2-model-b raspberrypi,2-model-b-rev2 \
	raspberrypi,3-model-a-plus \
	raspberrypi,3-model-b raspberrypi,3-model-b-plus \
	raspberrypi,3-compute-module raspberrypi,compute-module-3 \
	raspberrypi,400 raspberrypi,4-compute-module raspberrypi,4-model-b \
	raspberrypi,model-zero-2 raspberrypi,model-zero-2-w
  DEVICE_PACKAGES := \
	cypress-firmware-43430-sdio \
	brcmfmac-nvram-43430-sdio \
	cypress-firmware-43455-sdio \
	brcmfmac-nvram-43455-sdio \
	kmod-brcmfmac wpad-basic-mbedtls \
	kmod-i2c-bcm2835 kmod-spi-bcm2835 \
	kmod-spi-bcm2835-aux
  IMAGE/sysupgrade.img.gz := boot-common | boot-2708 | boot-2711 | sdcard-img | gzip | append-metadata
  IMAGE/factory.img.gz := boot-common | boot-2708 | boot-2711 | sdcard-img | gzip
endef
ifeq ($(SUBTARGET),bcm2709)
  TARGET_DEVICES += rpi-2
endif

define Device/rpi-3
  DEVICE_MODEL := 3A+/3B/3B+/CM3/Zero2/Zero2W
  DEVICE_VARIANT := (64bit)
  DEVICE_ALT0_VENDOR := Raspberry Pi
  DEVICE_ALT0_MODEL := 2B-1.2
  DEVICE_ALT0_VARIANT := (64bit)
  KERNEL_IMG := kernel8.img
  DEVICE_DTS := \
	broadcom/bcm2710-rpi-2-b \
	broadcom/bcm2710-rpi-3-b broadcom/bcm2710-rpi-3-b-plus \
	broadcom/bcm2710-rpi-cm3 \
	broadcom/bcm2710-rpi-zero-2 broadcom/bcm2710-rpi-zero-2-w
  SUPPORTED_DEVICES := \
	rpi-3-a-plus \
	rpi-3-b rpi-3-b-plus \
	rpi-zero-2 rpi-zero-2-w \
	raspberrypi,2-model-b-rev2 \
	raspberrypi,3-model-a-plus \
	raspberrypi,3-model-b raspberrypi,3-model-b-plus \
	raspberrypi,3-compute-module raspberrypi,compute-module-3 \
	raspberrypi,model-zero-2 raspberrypi,model-zero-2-w
  DEVICE_PACKAGES := \
	cypress-firmware-43430-sdio \
	brcmfmac-nvram-43430-sdio \
	cypress-firmware-43455-sdio \
	brcmfmac-nvram-43455-sdio \
	kmod-brcmfmac wpad-basic-mbedtls \
	kmod-i2c-bcm2835 kmod-spi-bcm2835 \
	kmod-spi-bcm2835-aux
endef
ifeq ($(SUBTARGET),bcm2710)
  TARGET_DEVICES += rpi-3
endif

define Device/rpi-4
  DEVICE_MODEL := 4B/400/CM4
  DEVICE_VARIANT := (64bit)
  KERNEL_IMG := kernel8.img
  DEVICE_DTS := \
	broadcom/bcm2711-rpi-400 \
	broadcom/bcm2711-rpi-4-b \
	broadcom/bcm2711-rpi-cm4
  SUPPORTED_DEVICES := \
	raspberrypi,400 \
	raspberrypi,4-compute-module \
	raspberrypi,4-model-b
  DEVICE_PACKAGES := \
	cypress-firmware-43455-sdio \
	brcmfmac-nvram-43455-sdio \
	kmod-brcmfmac wpad-basic-mbedtls \
	kmod-i2c-bcm2835 kmod-spi-bcm2835 \
	kmod-spi-bcm2835-aux \
	kmod-i2c-brcmstb \
	kmod-usb-net-lan78xx \
	kmod-r8169
  IMAGE/sysupgrade.img.gz := boot-common | boot-2711 | sdcard-img | gzip | append-metadata
  IMAGE/factory.img.gz := boot-common | boot-2711 | sdcard-img | gzip
endef
ifeq ($(SUBTARGET),bcm2711)
  TARGET_DEVICES += rpi-4
endif

define Device/rpi-5
  DEVICE_MODEL := 5/500/CM5
  KERNEL_IMG := kernel_2712.img
  DEVICE_DTS := \
	broadcom/bcm2712-rpi-5-b \
	broadcom/bcm2712-rpi-cm5-cm4io \
	broadcom/bcm2712-rpi-cm5-cm5io \
	broadcom/bcm2712-rpi-cm5l-cm4io \
	broadcom/bcm2712-rpi-cm5l-cm5io \
	broadcom/bcm2712d0-rpi-5-b
  SUPPORTED_DEVICES := \
	raspberrypi,500 \
	raspberrypi,5-compute-module \
	raspberrypi,5-model-b
  DEVICE_PACKAGES := \
	cypress-firmware-43455-sdio \
	brcmfmac-nvram-43455-sdio \
	kmod-brcmfmac wpad-basic-mbedtls \
	kmod-i2c-bcm2835 kmod-spi-bcm2835 \
	kmod-i2c-brcmstb \
	kmod-i2c-designware-platform kmod-spi-dw-mmio \
	kmod-hwmon-pwmfan kmod-thermal
  IMAGE/sysupgrade.img.gz := boot-common | sdcard-img | gzip | append-metadata
  IMAGE/factory.img.gz := boot-common | sdcard-img | gzip
endef
ifeq ($(SUBTARGET),bcm2712)
  TARGET_DEVICES += rpi-5
endif

define Device/rpi-4-mmeval
  $(Device/rpi-4)
  DEVICE_VARIANT := (64bit) (Morse Micro Eval)
  # remove the factory image (causes confusion)
  IMAGES := sysupgrade.img.gz
  IMAGE_PREFIX = $$(VERSION_DIST_SANITIZED)-$$(IMG_PREFIX_VERCODE)$$(IMG_PREFIX_EXTRA)rpi-4-mmeval
  DEVICE_IMG_NAME = $$(IMAGE_PREFIX)-$$(1)-$$(2)
  DEVICE_PACKAGES += kmod-morse netifd-morse morse-fw-8108
  SUPPORTED_DEVICES += morse,ekh01-01
endef
ifeq ($(SUBTARGET),bcm2711)
  TARGET_DEVICES += rpi-4-mmeval
endif

define Device/morse_ekh01_base
  $(Device/rpi-4)
  SYSINFO_BOARD_NAME := $(subst _,$(comma),$(1))
  SUPPORTED_DEVICES := $$(SYSINFO_BOARD_NAME)
  DEVICE_VENDOR := RPI
  # remove the factory image (causes confusion)
  IMAGES := sysupgrade.img.gz
  # Simplify by removing board and OpenWRT version.
  IMAGE_PREFIX = $$(VERSION_DIST_SANITIZED)-$$(IMG_PREFIX_VERCODE)$$(IMG_PREFIX_EXTRA)$$(call sanitize,$$(DEVICE_MODEL)-$$(DEVICE_VARIANT))
  DEVICE_IMG_NAME = $$(IMAGE_PREFIX)-$$(1)-$$(2)
  DEVICE_PACKAGES += kmod-morse netifd-morse morse-fw-6108 morse-fw-8108
  IMAGE/sysupgrade.img.gz := boot-common | boot-2711 | boot-ekh01 | sdcard-img | gzip | append-metadata
  IMAGE/factory.img.gz := boot-common | boot-2711 | boot-ekh01 | sdcard-img | gzip
endef

define Device/morse_pi3_base
  $(Device/rpi-3)
  SYSINFO_BOARD_NAME := $(subst _,$(comma),$(1))
  SUPPORTED_DEVICES := $$(SYSINFO_BOARD_NAME)
  DEVICE_VENDOR := RPI
  # remove the factory image (causes confusion)
  IMAGES := sysupgrade.img.gz
  # Simplify by removing board and OpenWRT version.
  IMAGE_PREFIX = $$(VERSION_DIST_SANITIZED)-$$(IMG_PREFIX_VERCODE)$$(IMG_PREFIX_EXTRA)$$(call sanitize,$$(DEVICE_MODEL)-$$(DEVICE_VARIANT))
  DEVICE_IMG_NAME = $$(IMAGE_PREFIX)-$$(1)-$$(2)
  DEVICE_PACKAGES += kmod-morse netifd-morse morse-fw-6108 morse-fw-8108
  IMAGE/sysupgrade.img.gz := boot-common | boot-2710 | boot-ekh01 | sdcard-img | gzip | append-metadata
  IMAGE/factory.img.gz := boot-common | boot-2710 | boot-ekh01 | sdcard-img | gzip
endef

define Device/morse_mmx108-ekh01-sdio
  $(Device/morse_ekh01_base)
  DEVICE_MODEL := MMx108-EKH01
  DEVICE_VARIANT := SDIO
  SYSINFO_MODEL := $$(DEVICE_VENDOR) $$(DEVICE_MODEL) ($$(DEVICE_VARIANT))
  # We name ourselves a generic morse,ekh01, and allow upgrading to this
  # from any of the legacy images, even those that will require BCF forcing (at least on
  # an upgrade the BCF will remain set).
  # We keep morse,mmx108-ekh01-sdio on the list of supported devices for
  # now as we temporarily used this name for internal builds.
  SYSINFO_BOARD_NAME := morse,ekh01
  SUPPORTED_DEVICES += morse,ekh01 morse,ekh01-01 morse,ekh01v1 morse,ekh01v2 morse,ekh01-03 morse,ekh01-05us
  DISTROCONFIG_EXTRA := mmx10x-sdio
endef
ifeq ($(SUBTARGET),bcm2711)
  TARGET_DEVICES += morse_mmx108-ekh01-sdio
endif

define Device/morse_mm8108-ekh01-spi
  $(Device/morse_ekh01_base)
  DEVICE_MODEL := MM8108-EKH01
  DEVICE_VARIANT := SPI
  SYSINFO_MODEL := $$(DEVICE_VENDOR) $$(DEVICE_MODEL) ($$(DEVICE_VARIANT))
  SUPPORTED_DEVICES += morse,ekh01 morse,ekh01-01
  DISTROCONFIG_EXTRA := mm810x-spi
endef
ifeq ($(SUBTARGET),bcm2711)
  TARGET_DEVICES += morse_mm8108-ekh01-spi
endif

define Device/morse_mm6108-ekh01-spi
  $(Device/morse_ekh01_base)
  DEVICE_MODEL := MM6108-EKH01
  DEVICE_VARIANT := SPI
  SYSINFO_MODEL := $$(DEVICE_VENDOR) $$(DEVICE_MODEL) ($$(DEVICE_VARIANT))
  SUPPORTED_DEVICES += morse,ekh01 morse,ekh01v1 morse,ekh01v2 morse,ekh01-03 morse,ekh01-05us
  DISTROCONFIG_EXTRA := mm610x-spi
endef
ifeq ($(SUBTARGET),bcm2711)
  TARGET_DEVICES += morse_mm6108-ekh01-spi
endif

define Device/morse_mm6108-ekh01-sdio
  $(Device/morse_ekh01_base)
  DEVICE_MODEL := MM6108-EKH01
  DEVICE_VARIANT := SDIO
  SYSINFO_MODEL := $$(DEVICE_VENDOR) $$(DEVICE_MODEL) ($$(DEVICE_VARIANT))
  SUPPORTED_DEVICES += morse,ekh01 morse,ekh01v1 morse,ekh01v2 morse,ekh01-03 morse,ekh01-05us
  DISTROCONFIG_EXTRA := mm610x-sdio
endef
ifeq ($(SUBTARGET),bcm2711)
  TARGET_DEVICES += morse_mm6108-ekh01-sdio
endif

define Device/bcm2711_mm6108-spi
  $(Device/morse_ekh01_base)
  DEVICE_MODEL := RPI4-MM6108
  DEVICE_VARIANT := SPI
  SYSINFO_MODEL := $$(DEVICE_VENDOR) $$(DEVICE_MODEL) ($$(DEVICE_VARIANT))
  SUPPORTED_DEVICES += morse,ekh01 morse,ekh01v1 morse,ekh01v2 morse,ekh01-03 morse,ekh01-05us bcm2711,mm6108-seeed-spi
  DISTROCONFIG_EXTRA := mm6108-seeed-spi
endef
ifeq ($(SUBTARGET),bcm2711)
  TARGET_DEVICES += bcm2711_mm6108-spi
endif

define Device/bcm2711_mm6108-sdio
  $(Device/morse_ekh01_base)
  DEVICE_MODEL := RPI4-MM6108
  DEVICE_VARIANT := SDIO
  SYSINFO_MODEL := $$(DEVICE_VENDOR) $$(DEVICE_MODEL) ($$(DEVICE_VARIANT))
  SUPPORTED_DEVICES += morse,ekh01 morse,ekh01v1 morse,ekh01v2 morse,ekh01-03 morse,ekh01-05us bcm2711,mm6108-sdio
  DISTROCONFIG_EXTRA := mm610x-sdio
endef
ifeq ($(SUBTARGET),bcm2711)
  TARGET_DEVICES += bcm2711_mm6108-sdio
endif

define Device/bcm2710_mm6108-spi
  $(Device/morse_pi3_base)
  DEVICE_MODEL := RPI3-MM6108
  DEVICE_VARIANT := SPI
  SYSINFO_MODEL := $$(DEVICE_VENDOR) $$(DEVICE_MODEL) ($$(DEVICE_VARIANT))
  SUPPORTED_DEVICES += bcm2710,mm6108-seeed-spi
  DISTROCONFIG_EXTRA := mm6108-seeed-spi
endef
ifeq ($(SUBTARGET),bcm2710)
  TARGET_DEVICES += bcm2710_mm6108-spi
endif

define Device/bcm2710_mm6108-sdio
  $(Device/morse_pi3_base)
  DEVICE_MODEL := RPI3-MM6108
  DEVICE_VARIANT := SDIO
  SYSINFO_MODEL := $$(DEVICE_VENDOR) $$(DEVICE_MODEL) ($$(DEVICE_VARIANT))
  SUPPORTED_DEVICES += bcm2710,mm6108-sdio
  DISTROCONFIG_EXTRA := mm610x-sdio
endef
ifeq ($(SUBTARGET),bcm2710)
  TARGET_DEVICES += bcm2710_mm6108-sdio
endif

$(eval $(call BuildImage))
