################################################################################
#
# LCXterm
#
################################################################################

LCXTERM_VERSION = 5f5f259b03dc4f6eb3d30144c0542a70e9427f91
LCXTERM_SITE = $(call gitlab,AutumnMeowMeow,lcxterm,$(LCXTERM_VERSION))
LCXTERM_DEPENDENCIES = ncurses

ifeq ($(BR2_PACKAGE_GPM),y)
LCXTERM_CONF_OPTS += --enable-gpm
LCXTERM_DEPENDENCIES += gpm
else
LCXTERM_CONF_OPTS += --disable-gpm
endif

$(eval $(autotools-package))
