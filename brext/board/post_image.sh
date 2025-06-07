#!/bin/bash
cd "$1"
mkdir -p isofs.tmp/{boot,img,rdparts}
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
$HOST_DIR/bin/fakeroot $BR2_EXTERNAL_I586CON_PATH/board/make-initramfs.sh "$(realpath mini-initramfs)" "$(realpath isofs.tmp/rdparts/ram.img)"
cp $BR2_EXTERNAL_I586CON_PATH/board/initramfs/init-cd mini-initramfs/init
$HOST_DIR/bin/fakeroot $BR2_EXTERNAL_I586CON_PATH/board/make-initramfs.sh "$(realpath mini-initramfs)" "$(realpath isofs.tmp/rdparts/cd.img)"

mkdir -p fsmod
$BR2_EXTERNAL_I586CON_PATH/util/moddir.py ../target/lib/modules/*.* fsmod isofs
find fsmod | cpio -o -H newc | gzip > isofs.tmp/rdparts/isofs.cpio.gz

rm fsmod/*
$BR2_EXTERNAL_I586CON_PATH/util/moddir.py ../target/lib/modules/*.* fsmod ext4 crc32c_generic
find fsmod | cpio -o -H newc | gzip > isofs.tmp/rdparts/ext4.cpio.gz

rm fsmod/*
$BR2_EXTERNAL_I586CON_PATH/util/moddir.py ../target/lib/modules/*.* fsmod vfat nls_cp437 nls_iso8859-1
find fsmod | cpio -o -H newc | gzip > isofs.tmp/rdparts/vfat.cpio.gz

cat ro.cpio rootfs.cpio.gz > isofs.tmp/img/rootfs.img
stat --printf="%s" ro.cpio > isofs.tmp/img/ro-size
cp rootfs.tar.gz isofs.tmp/img/save.tgz

# Up to here; add files required for HD install/upgrade process
$HOST_DIR/bin/genisoimage -V I586CON -J -r -o i586con-upgrade.img isofs.tmp
# After here: rest of the files on the actual CD
# (i named the upgrade image NOT .iso to avoid people burning it and trying to boot)

cat isofs.tmp/rdparts/{ram.img,isofs.cpio.gz} > isofs.tmp/boot/ram.img
cat isofs.tmp/rdparts/{cd.img,isofs.cpio.gz} > isofs.tmp/boot/cd.img

mkdir -p isofs.tmp/isolinux
cp syslinux/* isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/{ldlinux,libutil,menu,poweroff,chain,vesainfo}.c32 isofs.tmp/isolinux/
cp $HOST_DIR/share/syslinux/memdisk isofs.tmp/isolinux/

cp $BR2_EXTERNAL_I586CON_PATH/board/f*.txt isofs.tmp/isolinux/
sed -i "s|%VERSION%|$(cat $TARGET_DIR/etc/i586con/version)|" isofs.tmp/isolinux/f1.txt
cp $BR2_EXTERNAL_I586CON_PATH/board/isolinux.cfg isofs.tmp/isolinux/isolinux.cfg

dd if=/dev/zero of=isofs.tmp/boot/grubflop.bin bs=1k count=1440
$HOST_DIR/bin/python3 $BR2_EXTERNAL_I586CON_PATH/board/rootfs-overlay/root/make-grub-floppy.py isofs.tmp/boot/grubflop.bin $HOST_DIR/bin ../target/usr/lib/grub/i386-pc

cp memtest.bin isofs.tmp/boot/mt86p.bin

if [ -d "$BR2_EXTERNAL_I586CON_PATH/../mp3" ]; then
	cp -a "$BR2_EXTERNAL_I586CON_PATH/../mp3" isofs.tmp/
fi
$HOST_DIR/bin/genisoimage -V I586CON -J -r -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -o i586con.iso isofs.tmp
(cd isofs.tmp; ls --block-size=K -s boot/bzImage img/rootfs.img)
rm -rf isofs.tmp mini-initramfs fsmod
$HOST_DIR/bin/isohybrid -t 0x96 i586con.iso
