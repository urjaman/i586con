#!/bin/bash
cd "$1"
mkdir -p isofs.tmp/{isolinux,boot}
cp syslinux/* isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/ldlinux.c32 isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/libutil.c32 isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/menu.c32 isofs.tmp/isolinux/
cp $BR2_EXTERNAL_I586CON_PATH/board/isolinux.cfg isofs.tmp/isolinux/isolinux.cfg
cp bzImage isofs.tmp/boot/
cp rootfs.cpio isofs.tmp/boot/rootfs.bin
$HOST_DIR/bin/genisoimage -V i586con -J -r -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -o i586con.iso isofs.tmp
rm -rf isofs.tmp
$HOST_DIR/bin/isohybrid -t 0x96 i586con.iso
