OTHER_MENU:=Other modules

define KernelPackage/pwm-gpio
  SUBMENU:=Other modules
  TITLE:=PWM GPIO Support
  KCONFIG:= \
	CONFIG_PWM=y \
	CONFIG_PWM_GPIO \
	CONFIG_PWM_SYSFS=y
  FILES:= \
	$(LINUX_DIR)/drivers/pwm/pwm-gpio.ko
  AUTOLOAD:=$(call AutoLoad,30,pwm-gpio)
endef

define KernelPackage/pwm-gpio/description
  Generic PWM framework driver for a software PWM toggling a GPIO pin from kernel high-resolution timers.
endef

$(eval $(call KernelPackage,pwm-gpio))