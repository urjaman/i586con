################################################################################
#
# mocp (a fork from someone on github)
#
################################################################################

MOCP_VERSION = 48b48e593690ef0c398d5e33dc119b0a4fc73a2b
MOCP_SITE = $(call github,jonsafari,mocp,$(MOCP_VERSION))
MOCP_AUTORECONF = YES
MOCP_DEPENDENCIES = ncurses libtool
MOCP_CONF_OPTS  = --with-ncurses --without-rcc --enable-cache=no
# TODO (I'm very lazy)
MOCP_CONF_OPTS += --without-oss --without-sndio --without-jack
MOCP_CONF_OPTS += --without-ffmpeg
MOCP_CONF_OPTS += --without-sidplay2
MOCP_CONF_OPTS += --without-sndfile
MOCP_CONF_OPTS += --without-speex
MOCP_CONF_OPTS += --without-timidity
MOCP_CONF_OPTS += --without-vorbis
MOCP_CONF_OPTS += --without-wavpack

ifeq ($(BR2_PACKAGE_MOCP_ALSA),y)
MOCP_DEPENDENCIES += alsa-lib
else
MOCP_CONF_OPTS += --without-alsa
endif

ifeq ($(BR2_PACKAGE_MOCP_LIBSAMPLERATE),y)
MOCP_DEPENDENCIES += libsamplerate
else
MOCP_CONF_OPTS += --without-samplerate
endif

ifeq ($(BR2_PACKAGE_MOCP_MAD),y)
MOCP_DEPENDENCIES += libid3tag libmad
else
MOCP_CONF_OPTS += --without-mp3
endif

ifeq ($(BR2_PACKAGE_MOCP_FAAD2),y)
MOCP_DEPENDENCIES += faad2
else
MOCP_CONF_OPTS += --without-aac
endif

ifeq ($(BR2_PACKAGE_MOCP_FLAC),y)
MOCP_DEPENDENCIES += flac
else
MOCP_CONF_OPTS += --without-flac
endif

ifeq ($(BR2_PACKAGE_MOCP_MODPLUG),y)
MOCP_DEPENDENCIES += libmodplug
else
MOCP_CONF_OPTS += --without-modplug
endif

ifeq ($(BR2_PACKAGE_MOCP_CURL),y)
MOCP_DEPENDENCIES += libcurl
else
MOCP_CONF_OPTS += --without-curl
endif

$(eval $(autotools-package))
