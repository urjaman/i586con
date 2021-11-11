################################################################################
#
# LCXterm
#
################################################################################

LCXTERM_VERSION = eab3f668e2fa2a12d8ef3d9cc05fa2212db7c37a
LCXTERM_SITE = $(call gitlab,klamonte,lcxterm,$(LCXTERM_VERSION))
LCXTERM_DEPENDENCIES = ncurses

ifeq ($(BR2_PACKAGE_GPM),y)
LCXTERM_CONF_OPTS += --enable-gpm
LCXTERM_DEPENDENCIES += gpm
else
LCXTERM_CONF_OPTS += --disable-gpm
endif

$(eval $(autotools-package))
