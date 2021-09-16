#!/bin/bash
cd "$1"
mkdir -p isofs.tmp/{isolinux,boot,img}
cp syslinux/* isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/ldlinux.c32 isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/libutil.c32 isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/menu.c32 isofs.tmp/isolinux/
cp $BR2_EXTERNAL_I586CON_PATH/board/isolinux.cfg isofs.tmp/isolinux/isolinux.cfg
cp bzImage isofs.tmp/boot/
cpio -i busybox < rootfs.cpio
mkdir -p mini-initramfs/{dev,proc,sys,mnt}
mv busybox mini-initramfs/
cp $BR2_EXTERNAL_I586CON_PATH/board/initramfs/* mini-initramfs
rm -f mini-initramfs/init-*
mkdir -p mini-initramfs/atamod
$BR2_EXTERNAL_I586CON_PATH/util/atamoddir.py ../target/lib/modules/*.* mini-initramfs/atamod ../target/lib/modules/*.*/kernel/drivers/ata/*.ko
mkdir -p mini-initramfs/usbmod
$BR2_EXTERNAL_I586CON_PATH/util/usbmoddir.py ../target/lib/modules/*.* mini-initramfs/usbmod usb-storage usbhid hid-generic
mkdir -p mini-initramfs/zram
$BR2_EXTERNAL_I586CON_PATH/util/moddir.py ../target/lib/modules/*.* mini-initramfs/zram lzo_rle zram
cp $BR2_EXTERNAL_I586CON_PATH/board/initramfs/init-ram mini-initramfs/init
$HOST_DIR/bin/fakeroot $BR2_EXTERNAL_I586CON_PATH/board/make-initramfs.sh "$(realpath mini-initramfs)" "$(realpath isofs.tmp/boot/ram.img)"
cp $BR2_EXTERNAL_I586CON_PATH/board/initramfs/init-cd mini-initramfs/init
$HOST_DIR/bin/fakeroot $BR2_EXTERNAL_I586CON_PATH/board/make-initramfs.sh "$(realpath mini-initramfs)" "$(realpath isofs.tmp/boot/cd.img)"
cp $BR2_EXTERNAL_I586CON_PATH/board/initramfs/init-hd mini-initramfs/init
$HOST_DIR/bin/fakeroot $BR2_EXTERNAL_I586CON_PATH/board/make-initramfs.sh "$(realpath mini-initramfs)" "$(realpath isofs.tmp/boot/hd.img)"

mkdir -p isofs.tmp/rdparts
cp isofs.tmp/boot/{ram,cd,hd}.img isofs.tmp/rdparts
mkdir -p fsmod
$BR2_EXTERNAL_I586CON_PATH/util/moddir.py ../target/lib/modules/*.* fsmod isofs
find fsmod | cpio -o -H newc | gzip > isofs.tmp/rdparts/isofs.cpio.gz
cat isofs.tmp/rdparts/isofs.cpio.gz >> isofs.tmp/boot/ram.img
cat isofs.tmp/rdparts/isofs.cpio.gz >> isofs.tmp/boot/cd.img
cat isofs.tmp/rdparts/isofs.cpio.gz >> isofs.tmp/boot/hd.img

rm fsmod/*
$BR2_EXTERNAL_I586CON_PATH/util/moddir.py ../target/lib/modules/*.* fsmod ext4 crc32c_generic
find fsmod | cpio -o -H newc | gzip > isofs.tmp/rdparts/ext4.cpio.gz

rm fsmod/*
$BR2_EXTERNAL_I586CON_PATH/util/moddir.py ../target/lib/modules/*.* fsmod vfat nls_cp437 nls_iso8859-1
find fsmod | cpio -o -H newc | gzip > isofs.tmp/rdparts/vfat.cpio.gz

cat ro.cpio rootfs.cpio.gz > isofs.tmp/img/rootfs.img
stat --printf="%s" ro.cpio > isofs.tmp/img/ro-size
cp rootfs.tar.gz isofs.tmp/img/save.tgz

if [ -d "$BR2_EXTERNAL_I586CON_PATH/../mp3" ]; then
	cp -a "$BR2_EXTERNAL_I586CON_PATH/../mp3" isofs.tmp/
fi
$HOST_DIR/bin/genisoimage -V I586CON -J -r -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -o i586con.iso isofs.tmp
$HOST_DIR/bin/genisoimage -V I586CON  -J -r -m mp3 -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -o i586con-upgrade.iso isofs.tmp
rm -rf isofs.tmp mini-initramfs fsmod
$HOST_DIR/bin/isohybrid -t 0x96 i586con.iso
