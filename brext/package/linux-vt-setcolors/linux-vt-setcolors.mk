################################################################################
#
# linux-vt-setcolors
#
################################################################################

LINUX_VT_SETCOLORS_VERSION = 1dccf7c77f43331b671b6a401c06cf5d919812df
LINUX_VT_SETCOLORS_SITE = $(call github,evanpurkhiser,linux-vt-setcolors,$(LINUX_VT_SETCOLORS_VERSION))
LINUX_VT_SETCOLORS_LICENSE = MIT
LINUX_VT_SETCOLORS_LICENSE_FILES = LICENSE

define LINUX_VT_SETCOLORS_BUILD_CMDS
	$(MAKE) $(TARGET_CONFIGURE_OPTS) -C $(@D) setcolors
endef

define LINUX_VT_SETCOLORS_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/setcolors $(TARGET_DIR)/usr/bin
	mkdir -p $(TARGET_DIR)/usr/share
	cp -r $(@D)/example-colors $(TARGET_DIR)/usr/share/linux-vt-setcolors-example-colors
endef

$(eval $(generic-package))
