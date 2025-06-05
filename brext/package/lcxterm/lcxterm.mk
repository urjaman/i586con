################################################################################
#
# LCXterm
#
################################################################################

LCXTERM_VERSION = v0.9.5
LCXTERM_SITE = https://codeberg.org/AutumnMeowMeow/lcxterm.git
LCXTERM_SITE_METHOD = git
LCXTERM_DEPENDENCIES = ncurses
LCXTERM_AUTORECONF = YES

ifeq ($(BR2_PACKAGE_GPM),y)
LCXTERM_CONF_OPTS += --enable-gpm
LCXTERM_DEPENDENCIES += gpm
else
LCXTERM_CONF_OPTS += --disable-gpm
endif

$(eval $(autotools-package))
