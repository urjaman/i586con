#!/bin/bash
cd "$1"
chown -R 0:0 .
mknod dev/console c 5 1
chmod 600 dev/console
chmod a+x init busybox
# this can be used with rdinit=/sh
rm -f sh
ln -s busybox sh
find . -print | cpio -oH newc | gzip -9 > "$2"
