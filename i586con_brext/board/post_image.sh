#!/bin/bash
cd "$1"
mkdir -p isofs.tmp/{isolinux,boot}
cp syslinux/* isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/ldlinux.c32 isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/libutil.c32 isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/menu.c32 isofs.tmp/isolinux/
RD_SIZE="$(stat --printf=%s rootfs.squashfs)"
RD_SIZE=$((RD_SIZE / 1024))
sed s/XXXRDSIZEXXX/$RD_SIZE/ < $BR2_EXTERNAL_I586CON_PATH/board/isolinux.cfg > isofs.tmp/isolinux/isolinux.cfg
cp bzImage isofs.tmp/boot/
cp rootfs.squashfs isofs.tmp/boot/initrd.sqf
$HOST_DIR/bin/genisoimage -V i586con -J -R -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -o i586con.iso isofs.tmp
rm -rf isofs.tmp
$HOST_DIR/bin/isohybrid -t 0x96 i586con.iso
