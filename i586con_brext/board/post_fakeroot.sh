#!/bin/bash
echo "XXXXXXXXXXXXXX RUNNING POST FAKEROOT SCRIPT XXXXXXXXXXXXXXXXXX"
cd "$1"
$HOST_DIR/bin/mksquashfs usr etc ro.sqfs -comp zstd -b 256K -no-exports -no-xattrs
rm -rf usr etc
mkdir usr etc
