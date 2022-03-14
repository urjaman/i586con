
# These are required by our scripts
PACKAGES += host-cdrkit host-squashfs

include $(sort $(wildcard $(BR2_EXTERNAL_I586CON_PATH)/package/*/*.mk))
