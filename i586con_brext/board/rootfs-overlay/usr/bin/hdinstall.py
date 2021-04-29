#!/usr/bin/python3

import os
import sys
import time
import stat
import subprocess
import hd_save as hds

def sub(*args, **kwargs):
    return subprocess.run(*args, **kwargs).returncode == 0

def schk(*args, **kwargs):
    emsg = kwargs['emsg']
    del kwargs['emsg']
    if not sub(*args, **kwargs):
        sys.exit(emsg)

def devpath(majmin):
    mms = ':'.join([str(x) for x in majmin])
    return '/sys/dev/block/' + mms + '/'

def sysfs_str(path):
    with open(path) as f:
        return f.read().strip()

def sysfs_int(path):
    return int(sysfs_str(path))

def stat_blockdev(path):
    x = os.stat(path)
    if not stat.S_ISBLK(x.st_mode):
        sys.exit(f'{path} is not a block device node.')
    return x

if len(sys.argv) != 3:
    sys.exit(f"usage: {sys.argv[0]} <hdd_part_dev> <grub_install_dev>")

pdev = sys.argv[1]
grubdev = sys.argv[2]

pstat = stat_blockdev(pdev)
stat_blockdev(grubdev)

p_majmin = os.major(pstat.st_rdev), os.minor(pstat.st_rdev)

dpath_part = devpath(p_majmin) + 'partition'
if not os.path.exists(dpath_part):
    sys.exit(f'{pdev} is not a partition.')

partition_nr = sysfs_int(dpath_part)
partition_size = sysfs_int(devpath(p_majmin) + 'size') / 2 / 1024
# This is just rule-of-thumb'd, if youre serious just change it
if partition_size < 100.0:
    sys.exit(f'{pdev} is too small: {partition_size} MiB < 100 MiB')

whole_mm = p_majmin[0], p_majmin[1] - partition_nr
whole_sizegb = sysfs_int(devpath(whole_mm) + 'size') / 2 / 1024 / 1024

vend  = sysfs_str(devpath(whole_mm) + 'device/vendor')
model =  sysfs_str(devpath(whole_mm) + 'device/model')

print('The given disk partition will be ERASED, check that it is correct:')
print(f'Device {pdev} is a {partition_size:.1f} MiB partition {partition_nr}')
print(f'Disk Vendor/Type: {vend}')
print(f'Disk Model: {model}')
print(f'Disk Size: {whole_sizegb:.3f} GiB')
r = input('Type yes to continue: ')
if r.strip().lower() != 'yes':
    sys.exit('Everything is as it was.')

print('Continuing in 3 seconds')
time.sleep(3)

umountcd = False
if not sub(['mountpoint','-q','/cd']):
    os.makedirs('/cd', exist_ok=True)
    schk(['mount', '-t', 'iso9660', '/dev/disk/by-label/I586CON', '/cd' ],
           emsg='Mounting i586con media failed')
    umountcd = True

cdbt = '/cd/boot/'
bt = '/boot/'
bzI = 'bzImage'

schk(['mkfs.ext4', '-m', '0', '-L', hds.boot_label, pdev ], emsg = 'mkfs.ext4 failed')
schk(['mount', '-t', 'ext4', pdev, bt ], emsg='Mounting the newly created /boot partition failed')
schk(['cp', cdbt + bzI, bt + bzI ], emsg='Copying kernel image failed')
for d in ( 'grub', 'img', 'rd', 'root' ):
    os.makedirs(bt + d, exist_ok=True)
for f in ( 'ram', 'cd', 'hd' ):
    schk(['cp', cdbt + f + '.img', bt + 'rd/'], emsg="Copying initramfs images failed")

for f in ( 'rootfs.img', 'ro-size' ):
    schk(['cp', '/cd/img/' + f, '/boot/img/'], emsg="Copying read-only fs image failed")

hds.hd_save(allfmt=True)

schk(['grub-install', grubdev ], emsg='grub-install failed')

## grub.cfg
def menuentry(name, lines):
    el = ['menuentry "', name , '" {\n' ]
    for l in lines:
        el += ['\t', l, '\n']
    el += ['}\n']
    return ''.join(el)

with open("/proc/cmdline") as f:
    cmdline = f.read()

# Your installed i586con will be in the graphical setup that you booted in...
vga_param = [ x for x in cmdline.split() if x.startswith("vga=") ]

k_start = 'linux16 /bzImage'
kern1 = ' '.join([k_start, 'root=LABEL=' + hds.boot_label ] + vga_param)
kern2 = ' '.join([k_start, 'rootfstype=ramfs' ] + vga_param)
inrd = 'initrd16 /rd/'

header = """
set timeout=5
set default=0

set menu_color_highlight=black/light-gray
set menu_color_normal=light-gray/blue
set color_normal=cyan/black
"""[1:]

cfg = [
    header,
    menuentry('i586con/RAM',      [kern1, inrd + 'ram.img']),
    menuentry('i586con/CDlike',   [kern1, inrd + 'cd.img']),
    menuentry('i586con/BIOS2RAM', [kern2, 'initrd16 /img/rootfs.img'])
    ]

with open('/boot/grub/grub.cfg', 'w') as f:
    f.write(''.join(cfg))

sub(['umount', '/boot'])
if umountcd:
    sub(['umount', '/cd'])


print("Installation complete, to new beginnings :)")
