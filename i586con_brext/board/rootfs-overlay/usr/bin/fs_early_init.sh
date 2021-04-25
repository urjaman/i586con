#!/bin/sh
exit 0
do_overlay_mount() {
	mkdir -p $1-ro $1-wk $1-ov
	mount --bind /$1 $1-ro
	mount -t overlay overlay -o lowerdir=$1-ro,upperdir=$1-ov,workdir=$1-wk /$1
}

grep /dev/root /proc/mounts | grep -q squashfs && (
	echo 'Setting up tmpfs overlays (/etc,/root,/usr,/home)'
	mount -t tmpfs tmpfs /.o
	cd /.o

	do_overlay_mount etc
	do_overlay_mount root
	do_overlay_mount usr
	do_overlay_mount home
)

grep -q i586con.offset= /proc/cmdline && (
	echo 'Unpacking appended saved state...'
	OFFSET="$(tr ' ' '\n' < /proc/cmdline | grep i586con.offset= | cut -f 2 -d '=')"
	SIZE="$(tr ' ' '\n' < /proc/cmdline | grep i586con.size= | cut -f 2 -d '=')"
	cd /
	dd if=/dev/ram0 bs=1k skip=$OFFSET count=$SIZE status=none | gunzip | cpio -idumH newc
	rm -f /usr/bin/hdinstall.sh
)
