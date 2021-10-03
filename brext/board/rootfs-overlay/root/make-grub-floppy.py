#!/usr/bin/env python3

import os
import sys
import stat
import subprocess

[device] = sys.argv[1:]

scriptname = os.path.abspath(__file__)

os.chdir("/tmp")

# run-check
def rc(*args, **kwargs):
    print(args)
    r = subprocess.run(*args, **kwargs)
    if r.returncode != 0:
        print(f"Return: {r.returncode}")
        sys.exit(1)

rc(["modprobe", "floppy"])

grub_filesystems = [ "fat", "iso9660", "ext2", "ntfs" ]

grub_mods = [
    # usb
    "usbms", "ohci", "uhci", "ehci",
    # disk
    "pata", "ahci", "biosdisk",
    # partitions related
    "part_msdos", "part_gpt", "parttool", "msdospart",
    # loaders
    "linux", "linux16", "chain", "multiboot", "ntldr",
    # commandline/utility
    "cat", "ls", "minicmd", "reboot", "halt", "help", "hexdump",
    # configs / system scanning / scripting / etc
    "configfile", "syslinuxcfg", "search", "read", "echo", "test", "true",
    # the rest
    "normal", "loopback"
] + grub_filesystems

grubcfg = """
insmod biosdisk
insmod part_msdos
insmod fat
insmod ext2

menuentry "Search for the I586CON CD (image)" {
    insmod iso9660
    if search --label --set bootcd --no-floppy I586CON; then
        echo Found $bootcd
        set root=$bootcd
        syslinux_configfile -i /isolinux/isolinux.cfg
    fi
}

menuentry "Search for an I586CON_BOOT (ext*) partition" {
    if search --label --set bootdisk --no-floppy I586CON_BOOT; then
        echo Found $bootdisk
        set root=$bootdisk
        configfile /grub/grub.cfg
    fi
}

menuentry "Search for an I586CONBT (fat) partition" {
    if search --label --set bootdisk --no-floppy I586CONBT; then
        echo Found $bootdisk
        set root=$bootdisk
        configfile /grub/grub.cfg
    fi
}

menuentry "Search for a boot partition by custom label" {
    echo -n "Enter label to look for: "
    read userlabel
    echo
    if search --label --set bootdisk --no-floppy $userlabel; then
        echo Found $bootdisk
        set root=$bootdisk
        configfile /grub/grub.cfg
    fi
}

menuentry "Load PATA native driver" {
    insmod pata
}

menuentry "Load USB native disk drivers" {
    insmod ehci
    insmod ohci
    insmod uhci
    insmod usbms
}

menuentry "Load AHCI native disk driver" {
    insmod ahci
}

menuentry "Reboot" {
    reboot
}

menuentry "Shutdown (or halt)" {
    halt
}

menuentry "Try next BIOS boot device (exit grub)" {
    exit
}
"""

with open("grubtmp.cfg", "w") as f:
    f.write(grubcfg[1:])

grubout = "grubtmp.img"

rc(["cp","-a","/usr/lib/grub/i386-pc","./grubmods"])

with open("grubmods/fs.lst", "w") as f:
    f.write('\n'.join(grub_filesystems + ['tar']) + '\n')

standalone_cmd = [
    "grub-mkstandalone",
    "-d", "/tmp/grubmods",
    "--themes=",
    "--fonts=",
    "--locales=",
    "--compress=xz",
    "--modules=xzio",
    "--install-modules=" + ' '.join(grub_mods),
    "--format=i386-pc",
    "-o", grubout,
    "/boot/grub/grub.cfg=./grubtmp.cfg"
]


rc(standalone_cmd)
grubsz = os.stat(grubout)[stat.ST_SIZE]
(sectors, rem) = divmod(grubsz, 512)
sectors += 2 if rem else 1

rc(["mkdosfs", "-n", "RAMGRUB2", "-R", str(sectors), "-r", "112", "-F", "12", device])

grub_bootsect_file = "/usr/lib/grub/i386-pc/boot.img"

with open(grub_bootsect_file, "rb") as f:
    grubboot = f.read()
    if len(grubboot) != 512:
        print(f"Wrong length grub boot sector in {grub_bootsect_file}?!?")
        sys.exit(1)

with open(device, "rb") as f:
    fatstart = f.read(512)


# We're sorta re-doing parts of what grub setup.c does; but I don't
# know of a way to have grub do what we're doing - also we're doing
# very little of what they're doing, so ...
# Anyways, mesh bytes from the 3 sources onto the floppy...

bootsect = grubboot[0:3] + fatstart[3:0x5A] + grubboot[0x5A:]

with open(grubout, "rb") as img:
    grub = img.read()

with open(device, "wb") as dev:
    dev.write(bootsect)
    dev.write(grub)

os.sync()

# Finally, mount the FAT and include a little notice for people
rc(["mount", "-t", "vfat", device, "/mnt"])
message = ("The grub memdisk image is hidden in the reserved sectors of this FAT12 filesystem.\n"
           "Thus editing it without recreating the filesystem is difficult (to put it mildly).\n"
           "You can however use the rest of the space on this filesystem and include whatever (small)\n"
           "files that you desire.\n\n"
           "The python script that was used to generate this floppy is included for easier recreation.\n")

with open("/mnt/README.TXT", 'w') as f:
    f.write(message)

rc(["cp",scriptname,"/mnt"])

rc(["umount", "/mnt"])
os.sync()
print("Floppy creation complete.")
