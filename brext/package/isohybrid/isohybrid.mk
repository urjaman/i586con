################################################################################
#
# isohybrid tool from syslinux, for the target
#
################################################################################

ISOHYBRID_VERSION = $(SYSLINUX_VERSION)
ISOHYBRID_SOURCE = syslinux-$(SYSLINUX_VERSION).tar.xz
ISOHYBRID_SITE = $(BR2_KERNEL_MIRROR)/linux/utils/boot/syslinux
ISOHYBRID_LICENSE = GPL-2.0+
ISOHYBRID_LICENSE_FILES = COPYING

# keeping these same as syslinux
ISOHYBRID_DEPENDENCIES = \
	host-nasm \
	host-python3 \
	host-upx \
	host-util-linux \
	util-linux


define ISOHYBRID_APPLY_SYSLINUX_PATCHES
	$(Q)$(APPLY_PATCHES) $(@D) $(SYSLINUX_PKGDIR) \*.patch || exit 1;
endef

ISOHYBRID_PRE_PATCH_HOOKS += ISOHYBRID_APPLY_SYSLINUX_PATCHES

# The syslinux tarball comes with pre-compiled binaries.
# Since timestamps might not be in the correct order, a rebuild is
# not always triggered for all the different images.
# Cleanup the mess even before we attempt a build, so we indeed
# build everything from source.
define ISOHYBRID_CLEANUP
	rm -rf $(@D)/bios $(@D)/efi32 $(@D)/efi64
endef
ISOHYBRID_POST_PATCH_HOOKS += ISOHYBRID_CLEANUP

# Build like a normal syslinux build (except point CC_FOR_BUILD at TARGET_CC)
# - we provided a patch to disable building anything else than isohybrid
define ISOHYBRID_BUILD_CMDS
	$(TARGET_MAKE_ENV) $(MAKE1) \
		ASCIIDOC_OK=-1 \
		A2X_XML_OK=-1 \
		CC="$(TARGET_CC)" \
		LD="$(TARGET_LD)" \
		OBJCOPY="$(TARGET_OBJCOPY)" \
		AS="$(TARGET_AS)" \
		NASM="$(HOST_DIR)/bin/nasm" \
		CC_FOR_BUILD="$(TARGET_CC)" \
		CFLAGS_FOR_BUILD="$(CFLAGS)" \
		LDFLAGS_FOR_BUILD="$(LDFLAGS)" \
		PYTHON=$(HOST_DIR)/bin/python3 \
		-C $(@D) bios
endef

# KISS
define ISOHYBRID_INSTALL_TARGET_CMDS
	install -D -t $(TARGET_DIR)/usr/bin $(@D)/bios/utils/isohybrid
endef

$(eval $(generic-package))
