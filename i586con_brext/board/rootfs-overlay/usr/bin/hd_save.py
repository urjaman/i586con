#!/usr/bin/python3

import os
import sys
import subprocess

# You can change this here, and all the scripts will learn it :)
boot_label = "I586CON_BOOT"

def sub(*args, **kwargs):
    return subprocess.run(*args, **kwargs).returncode == 0

mount_list = []

def mount(frm, to, fs=None, opts=None, record=True, what=None):
    os.makedirs(to, exist_ok=True)
    cmd_fs = [ '-t', fs ] if fs else []
    cmd_opts = [ '-o', opts ] if opts else []
    if what is None:
        what = to
    mnt_cmd = [ 'mount' ] + cmd_fs + cmd_opts + [ frm, to ]
    if not sub(mnt_cmd):
        sys.exit(f"Mounting {what} failed ('{' '.join(mnt_cmd)}')")
    ret = len(mount_list)
    if record:
        mount_list.append(to)
    return ret

def umount_recorded(offset=0):
    to_unmount = mount_list[offset:]
    mount_list = mount_list[:offset]
    while to_unmount:
        fs = to_unmount.pop()
        if not sub(['umount', fs]):
            print(f"Info: unmount of {fs} failed")


def bind_mount(frm, to, what=None, record=True):
    return mount(frm, to, what, record, opts="bind")

def mount_boot(record=True):
    boot_part = "/dev/disk/by-label/" + boot_label

    # We'll believe that you want it there if you mounted it manually :)
    if os.path.exists('/boot/grub'):
        return len(mount_list)

    # If we have a boot partition (with grub) mounted as "CD", bind mount that
    if os.path.exists('/cd/grub'):
        return bind_mount('/cd', '/boot',record=record)

    if not os.path.exists(boot_part):
        sys.exit("Boot partition not found")

    return mount(boot_part, "/boot", "ext4", record=record, what="boot partition")


def overlay_mount(layers, workdir, where, record=True):
    os.makedirs(layers[0], exit_ok=True)
    os.makedirs(where, exist_ok=True)
    os.makedirs(workdir, exist_ok=True)
    lowerdir = ':'.join(layers[1:])
    opts = ','.join([
             'lowerdir=' + lowerdir,
             'upperdir=' + layers[0],
             'workdir=', + workdir
             ])
    return mount("overlay", where, "overlay", opts, record=record, what="overlayfs")


def unpack_rootfsimg_save(imgdir, files=None):
    with open(imgdir + "/ro-size") as f
        rosize = int(f.read())
    with open(imgdir + "/rootfs.img", "rb") as f:
        cpiocmd = [ 'cpio', '-i', '-d' ]
        if files:
            for f in files:
                cpiocmd.append(f.lstrip('/'))

        f.seek(rosize, 0)
        with subprocess.Popen("gunzip", stdin=f, stdout=subprocess.PIPE) as gunzip:
            cpio = subprocess.Popen(cpiocmd, stdin=gunzip.stdout)
            return cpio.wait()

def pack_rootfsimg_save(imgdir):
    with open(imgdir + "/ro-size") as f
        rosize = int(f.read())
    with open(imgdir + "/rootfs.img", "r+b") as f:
        f.seek(rosize, 0)
        f.truncate()
        with subprocess.Popen(['find', '.'], stdout=subprocess.PIPE) as find:
            sortenv = os.environ.copy()
            sortenv['LC_ALL'] = 'C'
            with subprocess.Popen("sort", stdin=find.stdout, stdout=subprocess.PIPE, env=sortenv) as sort:
                cpiocmd = [ 'cpio', '-o', '-H', 'newc' ]
                cpio = subprocess.Popen(cpiocmd, stdin=sort.stdout, stdout=f)
                return cpio.wait()

def pack_savetgz(imgdir):
    tmpsavename = imgdir + '/newsave.tgz'
    savename = imgdir + '/save.tgz'
    tarcmd = [ 'tar', 'czf', tmpsavename, '.' ]
    if not sub(tarcmd):
        sys.exit("creating the new save.tgz failed")
    os.replace(tmpsavename, savename)

def hd_save(allfmt=False, savestack=None):
    fmt_bios2ram = allfmt
    fmt_savetgz = allfmt
    if os.path.exists('/ro.sqfs'):
        fmt_bios2ram = True
    else:
        fmt_savetgz = True

    # We make a tmpfs for all of our messing around,
    # then at the end just umount everything and
    # unlink that one directory, neat.
    mpb = '/tmp/hdsave/'
    mntbase = mount("tmpfs", mpb[:-1], "tmpfs")

    layers = [ mpb + 'rw', '/' ]
    if savestack:
        layers.append(savestack)
    overlay_mount(layers, mpb + 'wk', mbp + 'savemp')
    if sub(['mountpoint', '-q', '/.o']):
        dotolrs = [ mpn + 'dotorw', '/.o' ]
        if savestack:
             dotolrs.append(savestack + '/.o')
        overlay_mount(dotolrs, mpb + 'dotowk', mpb + 'savemp/.o')

    # always use these from the savestack, to upgrade the init process correctly
    ss_special = ( '/busybox', '/init' )
    if savestack:
        for f in ss_special:
            if not sub(['cp', savestack + f, mpb + 'savemp' + f])
                sys.exit(f"copying {savestack + f} failed")

    # none of the save methods wants these in the root of the save image
    os.chdir(mpb + 'savemp')
    undesired = ( 'ro.sqfs', 'ro.cpio' )
    for f in undesired:
        if os.path.exists(f):
            os.unlink(f)

    savetypes = []

    if fmt_bios2ram:
        need_specials = False
        for f in ss_special:
            if not os.path.exists('.' + f)
                need_specials = True
        # In case we didn't boot in the BIOS2RAM style, we need to add these files
        if need_specials:
            if unpack_rootfsimg_save('/boot/img', ss_special) != 0:
                sys.exit("Unpacking /busybox and /init from rootfs.img failed")
        if pack_rootfsimg_save('/boot/img') != 0:
                sys.exit("Packing rootfs.img failed (NEXT BOOT MAY FAIL!)")
        savetypes.append("rootfs.img")

    if fmt_savetgz:
        # for savetgz, we _dont_ want the specials
        for f in ss_special:
            os.unlink('.' + f)
        pack_savetgz('/boot/img')
        savetypes.append("save.tgz")

    os.chdir('/')
    umount_recorded(mntbase)
    os.unlink(mbp[:-1])

    msg = ' and '.join(savetypes)
    print(f"Save complete - {msg} modified")


if __name__ == "__main__":
    allfmt = False
    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            allfmt = True
        else:
            sys.exit("usage: " + sys.argv[0] + " [--all]")

    mount_boot()
    hd_save(allfmt=allfmt)
    umount_recorded()
