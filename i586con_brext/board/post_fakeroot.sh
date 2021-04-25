#!/bin/bash
cd "$1"
TYPE="$(basename $(dirname $1))"
[ "$TYPE" = "tar" ] || $HOST_DIR/bin/mksquashfs usr etc ro.sqfs -comp zstd -b 256K -no-exports -no-xattrs
rm -rf usr etc
mkdir usr etc
if [ "$TYPE" = "tar" ]; then
	rm -f init busybox ro.sqfs
fi
