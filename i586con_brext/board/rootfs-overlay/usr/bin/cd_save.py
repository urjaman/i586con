#!/usr/bin/python3

import os
import sys
import subprocess
import hd_save as hds

def sub(*args, **kwargs):
    p = subprocess.run(*args, **kwargs)
    if p.returncode != 0:
        return False
    if p.stdout is not None:
        return p.stdout
    return True

def ismsinfo(str):
    if not str:
        return False
    str = str.strip()
    if str[0] != '(':
        return False
    if str[-1] != ')':
        return False
    if ',' not in str:
        return False
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            sys.exit(f"usage: {sys.argv[0]} [additional parameters to wodim]")

    if not os.path.exists('/ro.cpio'):
        print('Saving state to CD-R is only possible when booted with the "Linux to RAM" boot method.')
        # That's a partial lie, but none of the other options are super useful:
        # CDlike HD boot: well, you already booted from a writable HD, save to that...
        # BIOS2RAM CD boot: well, you can't (reliably) save the state that BIOS2RAM
        # loads, so writing a Linux to RAM/Run from CD-boot-style savestate seems... less useful again.
        sys.exit(0)

    # Just to verify that the CD is not mounted...
    if sub(['mountpoint', '-q', '/cd']):
        if not sub(['umount', '/cd']):
            sys.exit("Unmounting /cd failed")

    cdlabel = "I586CON"
    device = "/dev/disk/by-label/" + cdlabel
    devpar = '-dev=' + device

    msinfo = sub(['wodim', devpar, '-msinfo'], stdout=subprocess.PIPE)
    # "(AAA,BBB)" expected
    if not ismsinfo(msinfo):
        sys.exit("Could not acquire multisession info from the CD")

    msinfo = msinfo.strip()

    mpb = '/tmp/cdsave/'
    hds.mount("tmpfs", mpb[:-1], "tmpfs")

    layers = [ mpb + 'rw', '/' ]
    hds.overlay_mount(layers, mpb + 'wk', mpb + 'savemp')

    # none of the save methods wants these in the root of the save image
    os.chdir(mpb + 'savemp')
    # dont save the whole effing RO :P
    hds.unlink('ro.cpio')
    # make the "CD directory" and create a save.tgz there
    os.makedirs(mpb + 'cd/img', exist_ok=True)
    hds.pack_savetgz(mpb + 'cd/img')

    os.chdir(mpb)
    isofn = 'save.iso'
    mkisocmd = ['genisoimage', '-o', isofn, '-J', '-r', '-V', cdlabel,
                '-C', msinfo, '-M', device, 'cd' ]

    if not sub(mkisocmd):
        sys.exit("Creation of the ISO image failed")

    burncmd = [ 'wodim', devpar, '-multi', '-data' ]
    burncmd += sys.argv[1:]
    burncmd.append(isofn)

    print("Ready to try and burn the save image, with these parameters:")
    print("'" + "' '".join(burncmd) + "'")
    reply = input("Type burn to continue: ")
    if reply.strip().lower() != "burn":
        print("Okay, no burn, no panic. Will cleanup.")
        os.chdir("/")
        hds.umount_recorded()
        sys.exit(0)

    if not sub(burncmd):
        sys.exit("Burn failed :/")

    os.chdir("/")
    hds.umount_recorded()
    sys.exit("All seems well.")
