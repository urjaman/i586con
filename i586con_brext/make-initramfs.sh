#!/bin/bash
cd "$1"
chown -R 0:0 .
mknod dev/console c 5 1
chmod 600 dev/console
chmod a+x init busybox
find . -depth -print | cpio -oH newc | gzip -9 > "$2"
