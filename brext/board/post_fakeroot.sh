#!/bin/bash
cd "$1"
mv root home/
ln -s home/root root
sed -i '1 s#/root#/home/root#' etc/passwd
# call the root shell via hush so it says "hush: blah", clearer.
sed -i '1 s#/sh#/hush#' etc/passwd
TYPE="$(basename $(dirname $1))"
[ "$TYPE" = "tar" ] || $HOST_DIR/bin/mksquashfs usr etc home ro.sqfs -comp zstd -b 256K -no-exports -no-xattrs
rm -rf usr etc home
mkdir usr etc home
if [ "$TYPE" = "cpio" ]; then
	echo ro.sqfs | cpio  --quiet -o -H newc > $BUILD_DIR/../images/ro.cpio
	rm -f ro.sqfs
fi
if [ "$TYPE" = "tar" ]; then
	rm -f init busybox ro.sqfs
fi
