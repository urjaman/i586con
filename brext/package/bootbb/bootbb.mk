################################################################################
#
# busybox
#
################################################################################

BOOTBB_VERSION = 1.37.0
BOOTBB_SITE = https://www.busybox.net/downloads
BOOTBB_SOURCE = busybox-$(BOOTBB_VERSION).tar.bz2
BOOTBB_LICENSE = GPL-2.0, bzip2-1.0.4
BOOTBB_LICENSE_FILES = LICENSE archival/libarchive/bz/LICENSE
BOOTBB_CPE_ID_VENDOR = busybox

define BOOTBB_HELP_CMDS
	@echo '  bootbb-menuconfig     - Run BusyBox (boot/2nd copy) menuconfig'
endef

BOOTBB_CFLAGS = \
	$(TARGET_CFLAGS)

BOOTBB_LDFLAGS = \
	$(TARGET_LDFLAGS)

# Allows the build system to tweak CFLAGS
BOOTBB_MAKE_ENV = \
	$(TARGET_MAKE_ENV) \
	CFLAGS="$(BOOTBB_CFLAGS)" \
	CFLAGS_busybox="$(BOOTBB_CFLAGS_busybox)"

ifeq ($(BR2_REPRODUCIBLE),y)
BOOTBB_MAKE_ENV += \
	KCONFIG_NOTIMESTAMP=1
endif

BOOTBB_MAKE_OPTS = \
	CC="$(TARGET_CC)" \
	ARCH=$(KERNEL_ARCH) \
	PREFIX="$(TARGET_DIR)" \
	EXTRA_LDFLAGS="$(BOOTBB_LDFLAGS)" \
	CROSS_COMPILE="$(TARGET_CROSS)" \
	CONFIG_PREFIX="$(TARGET_DIR)" \
	SKIP_STRIP=y

ifndef BOOTBB_CONFIG_FILE
BOOTBB_CONFIG_FILE = $(call qstrip,$(BR2_PACKAGE_BOOTBB_CONFIG))
endif

BOOTBB_KCONFIG_FILE = $(BOOTBB_CONFIG_FILE)
BOOTBB_KCONFIG_EDITORS = menuconfig xconfig gconfig
BOOTBB_KCONFIG_OPTS = $(BOOTBB_MAKE_OPTS)

define BOOTBB_PERMISSIONS
	/busybox                     f 4755 0  0 - - - - -
endef

ifeq ($(BR2_USE_MMU),y)
define BOOTBB_SET_MMU
	$(call KCONFIG_DISABLE_OPT,CONFIG_NOMMU)
endef
else
define BOOTBB_SET_MMU
	$(call KCONFIG_ENABLE_OPT,CONFIG_NOMMU)
	$(call KCONFIG_DISABLE_OPT,CONFIG_SWAPON)
	$(call KCONFIG_DISABLE_OPT,CONFIG_SWAPOFF)
	$(call KCONFIG_DISABLE_OPT,CONFIG_ASH)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_BASH_COMPAT)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_BRACE_EXPANSION)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_HELP)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_INTERACTIVE)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_SAVEHISTORY)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_JOB)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_TICK)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_IF)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_LOOPS)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_CASE)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_FUNCTIONS)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_LOCAL)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_RANDOM_SUPPORT)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_EXPORT_N)
	$(call KCONFIG_ENABLE_OPT,CONFIG_HUSH_MODE_X)
endef
endif

define BOOTBB_KCONFIG_FIXUP_CMDS
	$(BOOTBB_SET_MMU)
endef

define BOOTBB_BUILD_CMDS
	$(BOOTBB_MAKE_ENV) $(MAKE) $(BOOTBB_MAKE_OPTS) -C $(@D)
endef

define BOOTBB_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/busybox $(TARGET_DIR)/busybox
endef

# Checks to give errors that the user can understand
# Must be before we call to kconfig-package
ifeq ($(BR2_PACKAGE_BOOTBB)$(BR_BUILDING),yy)
ifeq ($(call qstrip,$(BR2_PACKAGE_BOOTBB_CONFIG)),)
$(error No BootBusybox configuration file specified, check your BR2_PACKAGE_BOOTBB_CONFIG setting)
endif
endif

$(eval $(kconfig-package))
