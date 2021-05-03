#!/usr/bin/python3

import os
import sys
import subprocess

# You can change this here, and all the scripts will learn it :)
boot_label = "I586CON_BOOT"
# now with hdslib this is ... really sub-optimal. TODO.

def sub(*args, **kwargs):
    p = subprocess.run(*args, **kwargs)
    if p.returncode != 0:
        return False
    if p.stdout is not None:
        return p.stdout
    return True


unrw_cd = False
mount_list = []


def mount(frm, to, fs=None, opts=None, record=True, what=None):
    global mount_list
    os.makedirs(to, exist_ok=True)
    cmd_fs = ["-t", fs] if fs else []
    cmd_opts = ["-o", opts] if opts else []
    if what is None:
        what = to
    mnt_cmd = ["mount"] + cmd_fs + cmd_opts + [frm, to]
    if not sub(mnt_cmd):
        sys.exit(f"Mounting {what} failed ('{' '.join(mnt_cmd)}')")
    ret = len(mount_list)
    if record:
        mount_list.append(to)
    return ret


def umount_recorded(offset=0):
    global mount_list
    global unrw_cd
    to_unmount = mount_list[offset:]
    mount_list = mount_list[:offset]
    while to_unmount:
        fs = to_unmount.pop()
        if not sub(["umount", fs]):
            print(f"Info: unmount of {fs} failed")
    if not mount_list and unrw_cd:
        sub(["mount", "-o", "remount,ro", "/cd"])
        unrw_cd = False


def bind_mount(frm, to, what=None, record=True):
    return mount(frm, to, opts="bind", record=record, what=what)


def mount_boot(record=True):
    global mount_list

    boot_part = "/dev/disk/by-label/" + boot_label

    # We'll believe that you want it there if you mounted it manually :)
    if os.path.exists("/boot/grub"):
        return len(mount_list)

    # If we have a boot partition (with grub) mounted as "CD", bind mount that
    if os.path.exists("/cd/grub"):
        global unrw_cd
        unrw_cd = True
        sub(["mount", "-o", "remount,rw", "/cd"])
        return bind_mount("/cd", "/boot", record=record)

    if not os.path.exists(boot_part):
        sys.exit("Boot partition not found")

    return mount(boot_part, "/boot", "ext4", record=record, what="boot partition")


def overlay_mount(layers, workdir, where, record=True):
    os.makedirs(layers[0], exist_ok=True)
    os.makedirs(where, exist_ok=True)
    os.makedirs(workdir, exist_ok=True)
    lowerdir = ":".join(layers[1:])
    opts = ",".join(
        ["lowerdir=" + lowerdir, "upperdir=" + layers[0], "workdir=" + workdir]
    )
    return mount("overlay", where, "overlay", opts, record=record, what="overlayfs")


def unpack_rootfsimg_save(imgdir, files=None):
    with open(imgdir + "/ro-size") as f:
        rosize = int(f.read())
    with open(imgdir + "/rootfs.img", "rb") as f:
        cpiocmd = ["cpio", "-i", "-d"]
        if files:
            for x in files:
                cpiocmd.append(x.lstrip("/"))

        f.seek(rosize, 0)
        gunzip = subprocess.Popen("gunzip", stdin=f, stdout=subprocess.PIPE)
        cpio = subprocess.Popen(cpiocmd, stdin=gunzip.stdout)
        r1 = cpio.wait()
        r2 = gunzip.wait()
        return r1 or r2


def pack_rootfsimg_save(imgdir):
    with open(imgdir + "/ro-size") as f:
        rosize = int(f.read())
    with open(imgdir + "/rootfs.img", "r+b") as f:
        f.seek(rosize, 0)
        f.truncate()
        find = subprocess.Popen(["find", "."], stdout=subprocess.PIPE)
        sortenv = os.environ.copy()
        sortenv["LC_ALL"] = "C"
        sort = subprocess.Popen(
            "sort", stdin=find.stdout, stdout=subprocess.PIPE, env=sortenv
        )
        cpiocmd = ["cpio", "-o", "-H", "newc"]
        cpio = subprocess.Popen(cpiocmd, stdin=sort.stdout, stdout=subprocess.PIPE)
        gzip = subprocess.Popen("gzip", stdin=cpio.stdout, stdout=f)
        r1 = gzip.wait()
        r2 = cpio.wait()
        r3 = sort.wait()
        r4 = find.wait()
        return r1 or r2 or r3 or r4


def pack_savetgz(imgdir):
    tmpsavename = imgdir + "/newsave.tgz"
    savename = imgdir + "/save.tgz"
    tarcmd = ["tar", "czf", tmpsavename, "."]
    if not sub(tarcmd):
        sys.exit("creating the new save.tgz failed")
    os.replace(tmpsavename, savename)


def unlink(f):
    try:
        os.unlink(f)
    except FileNotFoundError:
        pass


def hd_save(allfmt=False, savestack=None):
    fmt_bios2ram = allfmt
    fmt_savetgz = allfmt
    if os.path.exists("/ro.sqfs"):
        fmt_bios2ram = True
    else:
        fmt_savetgz = True

    # We make a tmpfs for all of our messing around,
    # then at the end just umount everything and
    # rmdir that one directory, neat.
    mpb = "/tmp/hdsave/"
    mntbase = mount("tmpfs", mpb[:-1], "tmpfs")

    layers = [mpb + "rw", "/"]
    if savestack:
        layers.append(savestack)
    overlay_mount(layers, mpb + "wk", mpb + "savemp")
    if sub(["mountpoint", "-q", "/.o"]):
        dotolrs = [mpb + "dotorw", "/.o"]
        if savestack:
            dotolrs.append(savestack + "/.o")
        overlay_mount(dotolrs, mpb + "dotowk", mpb + "savemp/.o")

    # always use these from the savestack, to upgrade the init process correctly
    ss_special = ("/busybox", "/init")
    if savestack:
        for f in ss_special:
            if not sub(["cp", savestack + f, mpb + "savemp" + f]):
                sys.exit(f"copying {savestack + f} failed")

    # none of the save methods wants these in the root of the save image
    os.chdir(mpb + "savemp")
    undesired = ("ro.sqfs", "ro.cpio")
    for f in undesired:
        unlink(f)

    # Do not try to archive the overlayfs workdirs
    sub("rm -rf .o/*-wk", shell=True)

    savetypes = []

    if fmt_bios2ram:
        need_specials = False
        for f in ss_special:
            if not os.path.exists("." + f):
                need_specials = True
        # In case we didn't boot in the BIOS2RAM style, we need to add these files
        if need_specials:
            if unpack_rootfsimg_save("/boot/img", ss_special):
                sys.exit("Unpacking /busybox and /init from rootfs.img failed")
            for f in ss_special:
                if not os.path.exists("." + f):
                    sys.exit(f"Failed to unpack {f} from rootfs.img")
        if pack_rootfsimg_save("/boot/img"):
            sys.exit("Packing rootfs.img failed (NEXT BOOT MAY FAIL!)")
        savetypes.append("rootfs.img")

    if fmt_savetgz:
        # for savetgz, we _dont_ want the specials
        for f in ss_special:
            unlink("." + f)
        pack_savetgz("/boot/img")
        savetypes.append("save.tgz")

    os.chdir("/")
    umount_recorded(mntbase)
    os.rmdir(mpb[:-1])

    msg = " and ".join(savetypes)
    print(f"Save complete - wrote {msg}")
