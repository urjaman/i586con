#!/usr/bin/python3

import subprocess
import os
import sys
import struct

boot_part = "/dev/disk/by-label/I586CON_BOOT"

def cmdline_int_val(line, par):
	if par in line:
		off = line.find(par)
		ls = line[off+len(par):].split(' ',1)
		return int(ls[0])
	return None

upgrade_sz = None
if len(sys.argv) == 2:
	upgrade_sz = cmdline_int_val(sys.argv[1], "upgrade=")
	if upgrade_sz is None:
		sys.exit('hd_save.py expects no arguments in normal use')

def sub(*args, **kwargs):
	return subprocess.run(*args, **kwargs).returncode == 0

if upgrade_sz is None:
	if os.path.exists(boot_part) is False:
		sys.exit("Boot partition not found")

	if sub(['mountpoint','-q','/boot']):
		sub(['umount','/boot'])

	if sub(['mount','-t','ext4',boot_part,'/boot']) is False:
		sys.exit("Mounting boot partition failed")

save_tmp = '/boot/save.cpio.gz'

if sub('cpio -omH newc < /etc/saved_files | gzip -9 > ' + save_tmp, shell=True) is False:
	sys.exit("Creation of the save archive failed")


if upgrade_sz is None:
	with open('/proc/cmdline') as f:
		cmdline = f.read()

	off_k = cmdline_int_val(cmdline, 'i586con.offset=')
	if off_k is None:
		off_k = cmdline_int_val(cmdline,'brd.rd_size=')
		if off_k is None:
			sys.exit('Cannot determine actual squashfs size')
else:
	off_k = upgrade_sz

# The save.cpio needs to be included in the squashfs bytes_used header field for kernel
# to copy it to ramdisk (from initrd/initramfs area where the image is first provided)
# We also align/pad the image to a nice 4k while at it.
size_k = None
with open('/boot/initrd.sqf', 'r+b') as f:
	f.seek(off_k*1024, 0)
	blksz = 4096
	with open(save_tmp, 'rb') as fin:
		while True:
			block = fin.read(blksz)
			if len(block) == 0:
				break
			if len(block) < blksz:
				round = blksz - len(block)
				block = block + bytes(round)
			f.write(block)
	size = f.tell()
	# magic 4, inode_count 4, mod time 4, block size 4
	# fragment entry count 4, compression id 2, block_log 2, flags 2, id_count 2, version_major 2, version_minor 2
	# root_inode_ref 8, bytes_used 8
	# 16+16+8 = 40 bytes until bytes_used
	f.seek(40, 0)
	f.write(struct.pack('<Q', size))
	size_k = size // 1024
	f.flush()
	os.truncate(f.fileno(), size)

os.unlink(save_tmp)

# Then finally, it is good* for the rd_size parameter to match the actual image size,
# thus edit the grub.cfg.
# * Too big and the unpacker will dd a bunch of zeroes for no point, too small
#   and the save image wont fit in it. So best just adjust it.

# Note: we're capable of also adjusting the offset= parameter when doing a hdi upgrade, shh..

grub_cfg = '/boot/grub/grub.cfg'
grub_cfg_new = grub_cfg + '.new'

rd_size = 'brd.rd_size='
offset_s = 'i586con.offset='

def splice_par(l, par, val):
	cut = l.find(par)
	pre = l[:cut]
	(dummy, post) = l[cut:].split(' ',1)
	return pre + par + val + ' ' + post

with open(grub_cfg_new, 'w') as fout:
	with open(grub_cfg, 'r') as fin:
		for l in fin:
			if rd_size in l:
				l = splice_par(l, rd_size, str(size_k))
			if upgrade_sz is not None and offset_s in l:
				l = splice_par(l, offset_s, str(upgrade_sz))
			fout.write(l)

os.replace(grub_cfg_new, grub_cfg)
if upgrade_sz is None:
	sub(['umount','/boot'])
print("Save complete")

