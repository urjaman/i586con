#!/bin/sh
cd "$1"
mkdir -p isofs.tmp/boot/grub/
cp bzImage isofs.tmp/boot/
cp grub-eltorito.img isofs.tmp/boot/grub/grub-eltorito.img
cp rootfs.squashfs isofs.tmp/boot/initrd.sqfs
cp $BR2_EXTERNAL_I586CON_PATH/board/grub.cfg isofs.tmp/boot/grub/
genisoimage -J -R -b boot/grub/grub-eltorito.img -no-emul-boot -boot-load-size 4 -boot-info-table -o i586con.iso isofs.tmp
rm -rf isofs.tmp
