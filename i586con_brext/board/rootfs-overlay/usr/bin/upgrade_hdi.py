#!/usr/bin/python3

import subprocess
import os
import sys

boot_part = "/dev/disk/by-label/I586CON_BOOT"

def sub(*args, **kwargs):
        return subprocess.run(*args, **kwargs).returncode == 0

if len(sys.argv) != 2:
	sys.exit('Usage: ' + sys.argv[0] + ' <new-i586con.iso>')

if os.path.exists(boot_part) is False:
        sys.exit("Boot partition not found")

print('Note: this upgrade is very simple replacement of the base squashfs and kernel.')
print('If there are updates to files you overwrite with /etc/saved_files, new kernel')
print('commandline parameters or a better grub version shipped in the new i586con,')
print('you will need to apply those yourself.')

iso9660_mp = '/tmp/upgrade_hdi_isomp'

os.makedirs(iso9660_mp, exist_ok=True)

if sub(['mount', '-o', 'loop,ro', '-t', 'iso9660', sys.argv[1], iso9660_mp]) is False:
	sys.exit("Mounting '" + sys.argv[1] + "' failed")

if sub(['mountpoint','-q','/boot']):
        sub(['umount','/boot'])

if sub(['mount','-t','ext4',boot_part,'/boot']) is False:
        sys.exit("Mounting boot partition failed")


bk = '.bak'
bzI = 'bzImage'
sqf = 'initrd.sqf'
bt = '/boot/'

rd_size = 'brd.rd_size='

def cmdline_int_val(line, par):
	if par in line:
		off = line.find(par)
		ls = line[off+len(par):].split(' ',1)
		return int(ls[0])
	return None


upgrade_sz = None
with open(iso9660_mp + '/isolinux/isolinux.cfg', 'r') as f:
	for l in f:
		if rd_size in l:
			upgrade_sz = cmdline_int_val(l, rd_size)
			if upgrade_sz is not None:
				break
if upgrade_sz is None:
	sys.exit('parsing isolinux.cfg for squashfs size failed')

os.chdir(iso9660_mp + '/boot')
if os.path.exists(bzI) is False:
	sys.exit('Upgrade kernel (bzImage) not found')

if os.path.exists(sqf) is False:
	sys.exit('Upgrade squashfs not found')

os.replace(bt + bzI, bt + bzI + bk)
os.replace(bt + sqf, bt + sqf + bk)

if sub(['cp', bzI, bt + bzI]) is False:
	sys.exit('Copying bzImage failed')

if sub(['cp', sqf, bt + sqf]) is False:
	sys.exit('Copying squashfs failed')

if sub(['/usr/bin/hd_save.py', 'upgrade=' + str(upgrade_sz) ]) is False:
	sys.exit('Initial save of saved files to new squashfs failed')

os.unlink(bt + bzI + bk)
os.unlink(bt + sqf + bk)

# then finally umount things
os.chdir('/')
sub(['umount','/boot'])
sub(['umount', iso9660_mp])
print('Upgrade complete')

