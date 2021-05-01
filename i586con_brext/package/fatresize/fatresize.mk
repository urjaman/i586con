################################################################################
#
# fatresize
#
################################################################################

FATRESIZE_VERSION = 1.1.0
FATRESIZE_SOURCE = v$(FATRESIZE_VERSION).tar.gz
FATRESIZE_SITE = https://github.com/ya-mouse/fatresize/archive/refs/tags
FATRESIZE_DEPENDENCIES = parted
FATRESIZE_LICENSE = GPL-3.0+
FATRESIZE_LICENSE_FILES = COPYING
FATRESIZE_AUTORECONF = YES

$(eval $(autotools-package))
