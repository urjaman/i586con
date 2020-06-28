#!/bin/bash
set -e

if [ "$#" -ne 3 ]; then
        echo "Usage: $0 <i586con_media_device> <harddrive_partition_device> <grub_install_device>"
        exit 1
fi

echo "Hey, i will make a new filesystem on $2!!!"
echo "It should be atleast 64M in size."
echo "Press enter to continue (Ctrl-C to quit)"
read dummy

mount -t iso9660 "$1" /mnt
mkfs.ext4 -m 0 -L I586CON_BOOT "$2"
mount -t ext4 "$2" /boot
cp /mnt/boot/bzImage /boot/bzImage
# we no longer need the i586con media, try to release it
umount /mnt || true
# splurt the squashfs image from RAM to HDD (this is a nice part of having a legit ramdisk instead of initramfs...)
dd if=/dev/ram0 of=/boot/initrd.sqf_base bs=4k
mkdir -p /boot/grub
grub-install "$3"
VGA_PARAM="$(tr ' ' '\n' < /proc/cmdline | grep vga=)"
SQF_SZ="$(tr ' ' '\n' < /proc/cmdline | grep brd.rd_size= | cut -f 2 -d '=')"
cat > /boot/grub/grub.cfg <<EOF
set timeout=5
set default=0

set menu_color_highlight=black/light-gray
set menu_color_normal=black/blue
set color_normal=cyan/black

menuentry "i586con hdinstall" {
	linux16 /bzImage brd.rd_size=32768 root=/dev/ram0 i586con.offset=$SQF_SZ $VGA_PARAM
	initrd16 /initrd.sqf
}
EOF

# Initialize the saved files list (these are for a minimal identity of a system beyond just "i586con" with random ssh host keys)
cat > /etc/saved_files <<EOF
/etc/saved_files
/etc/ssh/ssh_host_dsa_key
/etc/ssh/ssh_host_dsa_key.pub
/etc/ssh/ssh_host_ecdsa_key
/etc/ssh/ssh_host_ecdsa_key.pub
/etc/ssh/ssh_host_ed25519_key
/etc/ssh/ssh_host_ed25519_key.pub
/etc/ssh/ssh_host_rsa_key
/etc/ssh/ssh_host_rsa_key.pub
/etc/hostname
/etc/hosts
EOF
echo "Running first save (use hd_save.py to do this later)..."
hd_save.py

