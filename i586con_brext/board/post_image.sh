#!/bin/bash
cd "$1"
mkdir -p isofs.tmp/{isolinux,boot,img}
cp syslinux/* isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/ldlinux.c32 isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/libutil.c32 isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/menu.c32 isofs.tmp/isolinux/
cp $BR2_EXTERNAL_I586CON_PATH/board/isolinux.cfg isofs.tmp/isolinux/isolinux.cfg
cp bzImage isofs.tmp/boot/
cp rootfs.cpio isofs.tmp/boot/rootfs.bin
cp rootfs.tar.gz isofs.tmp/img/save.tgz
cpio -i ro.sqfs busybox < rootfs.cpio
mv ro.sqfs isofs.tmp/img/ro.sqf
mkdir -p mini-initramfs/{dev,proc,sys,mnt}
mv busybox mini-initramfs/
cp $BR2_EXTERNAL_I586CON_PATH/board/initramfs/* mini-initramfs
rm -f mini-initramfs/init-*
cp $BR2_EXTERNAL_I586CON_PATH/board/initramfs/init-ram mini-initramfs/init
$HOST_DIR/bin/fakeroot $BR2_EXTERNAL_I586CON_PATH/board/make-initramfs.sh "$(realpath mini-initramfs)" "$(realpath isofs.tmp/boot/ram.bin)"
cp $BR2_EXTERNAL_I586CON_PATH/board/initramfs/init-cd mini-initramfs/init
$HOST_DIR/bin/fakeroot $BR2_EXTERNAL_I586CON_PATH/board/make-initramfs.sh "$(realpath mini-initramfs)" "$(realpath isofs.tmp/boot/cd.bin)"
$HOST_DIR/bin/genisoimage -V I586CON -J -r -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -o i586con.iso isofs.tmp
rm -rf isofs.tmp mini-initramfs
$HOST_DIR/bin/isohybrid -t 0x96 i586con.iso
