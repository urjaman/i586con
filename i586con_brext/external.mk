
# our post_image script uses genisoimage, so ask buildroot to install it for us
target-post-image: host-cdrkit

# bump the squashfs block size to improve compression ... but not too much,
# the target computers are old...
ROOTFS_SQUASHFS_ARGS += -b 256K
