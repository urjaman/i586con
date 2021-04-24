#!/usr/bin/python3

import os
import sys
import subprocess
import hd_save


def sub(*args, **kwargs):
    return subprocess.run(*args, **kwargs).returncode == 0


if len(sys.argv) != 2:
    sys.exit("Usage: " + sys.argv[0] + " <new-i586con.iso>")

hd_save.mount_boot()

print("Note: this upgrade is very simple replacement of the base squashfs and kernel.")
print("If there are updates to files you overwrite with /etc/saved_files, new kernel")
print("commandline parameters or a better grub version shipped in the new i586con,")
print("you will need to apply those yourself.")

iso9660_mp = "/tmp/upgrade_hdi_isomp"

os.makedirs(iso9660_mp, exist_ok=True)

if not sub(["mount", "-o", "loop,ro", "-t", "iso9660", sys.argv[1], iso9660_mp]):
    sys.exit("Mounting '" + sys.argv[1] + "' failed")

bk = ".bak"
bzI = "bzImage"
sqf = "initrd.sqf"
bt = "/boot/"

os.chdir(iso9660_mp + "/boot")
if not os.path.exists(bzI):
    sys.exit("Upgrade kernel (bzImage) not found")

if not os.path.exists(sqf):
    sys.exit("Upgrade squashfs not found")

os.replace(bt + bzI, bt + bzI + bk)
os.replace(bt + sqf, bt + sqf + bk)

if not sub(["cp", bzI, bt + bzI]):
    sys.exit("Copying bzImage failed")

if not sub(["cp", sqf, bt + sqf]):
    sys.exit("Copying squashfs failed")

hd_save.hd_save()

os.unlink(bt + bzI + bk)
os.unlink(bt + sqf + bk)

# then finally umount things
os.chdir("/")
sub(["umount", "/boot"])
sub(["umount", iso9660_mp])
print("Upgrade complete")
