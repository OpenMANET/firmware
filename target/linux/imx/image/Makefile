# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2013 OpenWrt.org

include $(TOPDIR)/rules.mk
include $(INCLUDE_DIR)/image.mk

DEVICE_VARS += SYSINFO_MODEL SYSINFO_BOARD_NAME DISTROCONFIG_EXTRA

include $(SUBTARGET).mk

$(eval $(call BuildImage))
