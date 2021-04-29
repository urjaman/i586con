#!/usr/bin/python3

import os
import sys
import stat
import subprocess
import hd_save as hds


def sub(*args, **kwargs):
    return subprocess.run(*args, **kwargs).returncode == 0

def mount_opts(path):
    opts = 'ro'
    x = os.stat(path)
    if stat.S_ISBLK(x.st_mode):
        return opts
    return opts + ',loop'

if len(sys.argv) != 2:
    sys.exit("Usage: " + sys.argv[0] + " <new-i586con.iso>")

hds.mount_boot()

print("""
Note: this upgrade is very simple replacement of the base squashfs and kernel.
If there are updates to files in already in your save.tgz, new kernel
parameters or a better grub version shipped in the new i586con, you will need
to apply those yourself.
""")

newimg = sys.argv[1]
uphdi = "/tmp/upgrade_hdi"
savex = uphdi + "/savex"
iso9660_mp = uphdi + "/isomp"
hds.mount("tmpfs", uphdi, "tmpfs")
hds.mount(newimg, iso9660_mp, "iso9660", mount_opts(newimg), what="Upgrade image")

os.makedirs(savex, exist_ok=True)
os.chdir(iso9660_mp)

files = [
        ( 'boot/bzImage', '' ),
        ( 'boot/ram.img', 'rd/' ),
        ( 'boot/cd.img', 'rd/' ),
        ( 'boot/hd.img', 'rd/' ),
        ( 'img/ro-size', 'img/' ),
        ( 'img/rootfs.img', 'img/' )
        ( 'img/save.tgz', None ) # Not copied, just checked for existence and unpacked first :)
        ]

upsz = 0
for f, _ in files:
    try:
        s = os.stat(f)
        upsz += s.st_blocks / 2
    except FileNotFoundError:
        sys.exit("Upgrade missing file: " + f)

tarcmd = [ 'tar', 'xzf', files.pop()[0], '-C', savex ]
if not sub(tarcmd):
    sys.exit("Unpacking upgrade save tarball failed")

# Using moves to place the new files into their correct
# places makes it slightly less likely to break the system
# due to media read error or such, but needs some space...
# So do it if we have the space.
usemoves = True

fss = os.statvfs("/boot")
fs_space = (fss.f_frsize * fss.f_bavail) / 1024

if (upsz + 1024) > fs_space:
    usemoves = False
    # Incase we're literally running from the disk, we _will_ actually
    # use ~double the space (2x rootfs.img) even if we "unlink" the file
    # before, thus ... not enough space.
    if not os.path.exists("/ro.cpio") and not os.path.exists("/ro.sqfs"):
        sys.exit("Insufficient disk space for upgrade")

moves = []

for f, t in files:
    fn = "/boot/" + t + os.path.basename(f)
    fnn = fn + '.new' if usemoves else fn
    if usemoves:
        moves.append((fnn, fn))
    if os.path.exists(fnn):
        os.unlink(fnn)
    if sub(['cp',f,fnn]):
        sys.exit(f"Copying upgrade file {f} failed")

for frm, to in moves:
    os.replace(frm, to)

hds.hd_save(allfmt=True, savestack=savex)

# then finally umount things
os.chdir("/")
hds.umount_recorded()
print("Upgrade complete")
