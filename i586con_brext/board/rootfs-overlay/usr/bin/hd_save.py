#!/usr/bin/python3

import subprocess
import os
import sys
import struct

boot_part = "/dev/disk/by-label/I586CON_BOOT"

def sub(*args, **kwargs):
	return subprocess.run(*args, **kwargs).returncode == 0

if os.path.exists(boot_part) is False:
	sys.exit("Boot partition not found")

if sub(['mountpoint','-q','/boot']):
	sub(['umount','/boot'])

if sub(['mount','-t','ext4',boot_part,'/boot']) is False:
	sys.exit("Mounting boot partition failed")

save_tmp = '/boot/save.cpio.gz'

if sub('cpio -omH newc < /etc/saved_files | gzip -9 > ' + save_tmp, shell=True) is False:
	sys.exit("Creation of the save archive failed")

if sub('cat /boot/initrd.sqf_base ' + save_tmp + ' > /boot/initrd.sqf', shell=True) is False:
	sys.exit("Combining initrd.sqf and save archive failed")

os.unlink(save_tmp)

# The save.cpio needs to be included in the squashfs bytes_used header field for kernel
# to copy it to ramdisk (from initrd/initramfs area where the image is first provided)
# We also align/pad the image to a nice 4k while at it.
size_k = None
with open('/boot/initrd.sqf', 'r+b') as f:
	f.seek(0, 2)
	size = f.tell()
	if (size % 4096):
		round = 4096 - (size % 4096)
		f.write(bytes(round))
		size += round
	# magic 4, inode_count 4, mod time 4, block size 4
	# fragment entry count 4, compression id 2, block_log 2, flags 2, id_count 2, version_major 2, version_minor 2
	# root_inode_ref 8, bytes_used 8
	# 16+16+8 = 40 bytes until bytes_used
	f.seek(40, 0)
	f.write(struct.pack('<Q', size))
	size_k = size // 1024

# Then finally, it is good* for the rd_size parameter to match the actual image size,
# thus edit the grub.cfg.
# * Too big and the unpacker will dd a bunch of zeroes for no point, too small
#   and the save image wont fit in it. So best just adjust it.
grub_cfg = '/boot/grub/grub.cfg'
grub_cfg_new = grub_cfg + '.new'

rd_size = 'brd.rd_size='
with open(grub_cfg_new, 'w') as fout:
	with open(grub_cfg, 'r') as fin:
		for l in fin:
			if rd_size in l:
				cut = l.find(rd_size)
				pre = l[:cut]
				(dummy, post) = l[cut:].split(' ',1)
				new_l = pre + rd_size + str(size_k) + ' ' + post
				#print('old: ' + l, end='')
				#print('new: ' + new_l, end='')
				l = new_l
			fout.write(l)

os.replace(grub_cfg_new, grub_cfg)
sub(['umount','/boot'])
print("Save complete")

