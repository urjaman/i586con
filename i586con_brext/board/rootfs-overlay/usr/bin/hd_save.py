#!/usr/bin/python3

import subprocess
import os
import sys
import struct
from enum import IntEnum

boot_part = "/dev/disk/by-label/I586CON_BOOT"

# Okay so, injecting data into a squashfs initrd in a way where the kernel
# loads said data into the ramdisk (for later extraction via dd) was kinda
# hard (needed to fugde bytes_used) in kernel 5.4... kernel 5.10 made it
# ... kinda silly hard, but since I started it, I'm gonna do it.
# And yeah, this code creates a space in the "middle" of a squashfs image
# for the injected data, and mangles the absolute positions in the tables.
# Luckily (or maybe by design?) this seems to be possible without recompressing
# anything (exception being XATTR, but we dont use XATTR so it's ok).

def roundk(x, k):
	return (x + k-1) & ~(k-1)

def roundkd(x, k):
	return roundk(x, k) // k

class SBF(IntEnum):
	MAGIC = 0
	INODE_COUNT = 1
	MODIFICATION_TIME = 2
	BLOCK_SIZE = 3
	FRAGMENT_ENTRY_COUNT = 4
	COMPRESSION_ID = 5
	BLOCK_LOG = 6
	FLAGS = 7
	ID_COUNT = 8
	VERSION_MAJOR = 9
	VERSION_MINOR = 10
	ROOT_INODE_REF = 11
	BYTES_USED = 12
	ID_TABLE_START = 13
	XATTR_ID_TABLE_START = 14
	INODE_TABLE_START = 15
	DIRECTORY_TABLE_START = 16
	FRAGMENT_TABLE_START = 17
	EXPORT_TABLE_START = 18

class SQSB:
	struct_fmt = "<5L6H8Q"
	sb_len = struct.calcsize(struct_fmt)

	def __init__(s, f):
		s.f = f
		f.seek(0, 0)
		s.sb = list(struct.unpack(s.struct_fmt, f.read(s.sb_len)))
		if s.sb[SBF.MAGIC] != 0x73717368:
			raise Exception("Not a SquashFS")

	def bytes_used(s):
		return s.sb[SBF.BYTES_USED]

	def datablocks_end(s):
		return s.sb[SBF.INODE_TABLE_START]

	def adj(s, id, amt):
		if s.sb[id] == 2**64 -1:
			return
		s.sb[id] += amt

	def adj_list(s, id, cnt, amt):
		fmt = '<Q'
		el = struct.calcsize(fmt)
		st = s.sb[id]
		if st == 2**64 -1:
			return

		s.adj(id, amt)

		s.f.seek(st, 0)
		for _ in range(cnt):
			v, = struct.unpack(fmt, s.f.read(el))
			v += amt
			s.f.seek(-el, 1)
			s.f.write(struct.pack(fmt, v))


	def shuffle_tables(s, new_start):
		old_start = s.sb[SBF.INODE_TABLE_START]
		old_end = s.sb[SBF.BYTES_USED]
		amt = new_start - old_start
		if amt == 0:
			return

		if s.sb[SBF_XATTR_ID_TABLE_START] != 2**64 -1:
			raise Exception("XATTR not supported")

		s.adj_list(SBF.ID_TABLE_START, roundkd(s.sb[SBF.ID_COUNT], 2048), amt)
		s.adj_list(SBF.FRAGMENT_TABLE_START, roundkd(s.sb[SBF.FRAGMENT_ENTRY_COUNT], 512), amt)
		s.adj_list(SBF.EXPORT_TABLE_START, roundkd(s.sb[SBF.INODE_COUNT], 1024), amt)
		s.adj(SBF.INODE_TABLE_START, amt)
		s.adj(SBF.XATTR_ID_TABLE_START, amt)
		s.adj(SBF.DIRECTORY_TABLE_START, amt)
		s.adj(SBF.BYTES_USED, amt)
		bs = 64*1024
		if amt >= 0: # increasing size? copy in reverse...
			rp = old_end
			while True:
				rem = rp - old_start
				if rem > bs:
					rem = bs
				if not rem:
					break
				rp -= rem
				s.f.seek(rp, 0)
				block = s.f.read(rem)
				s.f.seek(rp + amt, 0)
				s.f.write(block)
			# increasing size? clear the area (the caller might not touch all of it, so to be nice)
			s.f.seek(old_start, 0)
			s.f.write(bytes(amt))
		else:
			rp = old_start
			while True:
				rem = old_end - rp
				if rem > bs:
					rem = bs
				if not rem:
					break
				s.f.seek(rp, 0)
				block = s.f.read(rem)
				s.f.seek(rp + amt, 0)
				s.f.write(block)
				rp += rem
			# decreasing size ? truncate
			s.f.truncate(s.bytes_used())

	def close(s):
		s.f.seek(0, 0)
		s.f.write(struct.pack(s.struct_fmt, *tuple(s.sb)))
		s.f.close()


def cmdline_int_val(line, par):
	if par in line:
		off = line.find(par)
		ls = line[off+len(par):].split(' ',1)
		return int(ls[0])
	return None

upgrade = None
if len(sys.argv) == 2:
	upgrade = cmdline_int_val(sys.argv[1], "upgrade=")
	if upgrade is None:
		sys.exit('hd_save.py expects no arguments in normal use')

def sub(*args, **kwargs):
	return subprocess.run(*args, **kwargs).returncode == 0

if upgrade is None:
	if os.path.exists(boot_part) is False:
		sys.exit("Boot partition not found")

	if sub(['mountpoint','-q','/boot']):
		sub(['umount','/boot'])

	if sub(['mount','-t','ext4',boot_part,'/boot']) is False:
		sys.exit("Mounting boot partition failed")

save_tmp = '/boot/save.cpio.gz'

if sub('cpio -omH newc < /etc/saved_files | gzip -9 > ' + save_tmp, shell=True) is False:
	sys.exit("Creation of the save archive failed")


if upgrade is None:
	with open('/proc/cmdline') as f:
		cmdline = f.read()

	off_k = cmdline_int_val(cmdline, 'i586con.offset=')
else:
	off_k = None

size_k = None
with open('/boot/initrd.sqf', 'r+b') as f:
	k = 1024
	sqfs = SQSB(f)
	curr_eos = sqfs.datablocks_end()
	if off_k is None:
		curr_sos = roundk(curr_eos, k)
		off_k = curr_sos // k
	else:
		curr_sos = off_k*k

	space = curr_eos - curr_sos
	blksz = k
	with open(save_tmp, 'rb') as fin:
		fin.seek(0, 2)
		sz = roundk(fin.tell(), k)
		read_sz_k = sz // k
		space_tol = 4*k
		if ((space - sz) < 0) or ((space - sz) > space_tol):
			sqfs.shuffle_tables(curr_sos + sz)
		fin.seek(0, 0)
		f.seek(curr_sos, 0)
		while True:
			block = fin.read(blksz)
			if len(block) == 0:
				break
			if len(block) < blksz:
				round = blksz - len(block)
				block = block + bytes(round)
			f.write(block)
	f.seek(sqfs.bytes_used(), 0)
	size = f.tell()
	size_4kp = roundk(size, 4*k)
	if size_4kp - size:
		f.write(bytes(size_4kp - size))

	size_k = size_4kp // 1024
	f.flush()
	sqfs.close()

os.unlink(save_tmp)

# Re-adjust the sizes & offsets in grub.cfg
# (Offset should be static after the first hd_save, but easier to just be able to edit it all)

grub_cfg = '/boot/grub/grub.cfg'
grub_cfg_new = grub_cfg + '.new'

rd_size = 'brd.rd_size='
offset_s = 'i586con.offset='
size_s = 'i586con.size='

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
				if offset_s in l:
					l = splice_par(l, offset_s, str(off_k))
				else:
					l = l[:-1] + ' ' + offset_s + str(off_k) + '\n'
				if size_s in l:
					l = splice_par(l, size_s, str(read_sz_k))
				else:
					l = l[:-1] + ' ' + size_s + str(read_sz_k) + '\n'
			fout.write(l)

os.replace(grub_cfg_new, grub_cfg)
if upgrade is None:
	sub(['umount','/boot'])
print("Save complete")

