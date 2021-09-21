#!/usr/bin/python3

import os
import sys
import subprocess

# This is only backwards compat now; main source is fstab
boot_label = "I586CON_BOOT"

cfgdir = "/etc/i586con/"


def sub(*args, **kwargs):
    p = subprocess.run(*args, **kwargs)
    if p.returncode != 0:
        return False
    if p.stdout is not None:
        return p.stdout
    return True


unrw_cd = False
mount_list = []


def mount(frm_or_to, to=None, fs=None, opts=None, record=True, what=None):
    global mount_list
    if to is None:
        to = frm_or_to
        frm_opt = []
    else:
        frm_opt = [frm_or_to]

    os.makedirs(to, exist_ok=True)
    cmd_fs = ["-t", fs] if fs else []
    cmd_opts = ["-o", opts] if opts else []
    if what is None:
        what = to
    mnt_cmd = ["mount"] + cmd_fs + cmd_opts + frm_opt + [to]
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

    fstab_boot = False
    with open("/etc/fstab") as ft:
        for L in ft:
            if L.strip()[0] == "#":
                continue
            T = L.split()
            if T[1] == "/boot":
                fstab_boot = True

    if fstab_boot:
        return mount("/boot", record=record, what="boot partition")

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
    undesired = ("ro.sqfs", ".o/Z/ro.cpio")
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


def updinst_prepare(src, dst, dstfs=None, upgrade=False):
    files = [
        (("boot/bzImage",), ""),
        (("img/ro-size",), "img/"),
        (("img/rootfs.img",), "img/"),
    ]
    ramdisks = []
    fsmods = []
    with os.scandir(src + "/rdparts") as it:
        for e in it:
            if e.is_file():
                if ".cpio" in e.name:
                    s, _ = e.name.split(".", maxsplit=1)
                    fsmods += [(s, e.name)]
                if e.name.endswith(".img"):
                    ramdisks += [e.name]

                files += [(("rdparts/" + e.name,), "rdparts/")]

    # figure out the destination filesystem; for which fsmod to use
    if dstfs is None:
        with open("/proc/mounts") as f:
            for L in f:
                M = L.split()
                if M[1] == dst:
                    dstfs = M[2]
        if dstfs is None:
            sys.exit("Unable to determine dst FS type")

    fsmod = None
    for fs, fn in fsmods:
        if fs == dstfs:
            fsmod = fn
    if fsmod is None:
        sys.exit("Missing fsmod .cpio for dst FS")

    for rd in ramdisks:
        files += [(("rdparts/" + rd, "rdparts/" + fsmod), "rd/")]

    updsz = 0
    dstsz = 0
    overwrites = []
    for fl, dstdir in files:
        dstname = dst + os.path.sep + dstdir + os.path.basename(fl[0])
        try:
            s = os.stat(dstname)
            dstsz += s.st_blocks / 2
            overwrites += [dstname]
        except FileNotFoundError:
            pass

        for f in fl:
            try:
                s = os.stat(src + os.path.sep + f)
                updsz += s.st_blocks / 2
            except FileNotFoundError:
                sys.exit("Missing file: " + f)

    fss = os.statvfs(dst)
    fs_space = (fss.f_frsize * fss.f_bavail) / 1024

    usemoves = False
    if overwrites:
        usemoves = True

    spacetol = 1024
    if (updsz + spacetol) > fs_space:
        usemoves = False
        dstwipesz = dstsz
        if upgrade and overwrites:
            if not os.path.exists("/.o/Z/ro.cpio") and not os.path.exists("/ro.sqfs"):
                for f in overwrites:
                    if "rootfs.img" in f:
                        s = os.stat(f)
                        dstwipesz -= s.st_blocks / 2

        nonmovesz = updsz - dstwipesz
        if (nonmovesz + spacetol) > fs_space:
            sys.exit("Insufficient target disk space")

    if upgrade and not overwrites:
        print("Warning: none of target files exist - is this an upgrade at all?")

    dirs = []
    if not upgrade:
        dirs = ["grub", "img", "rd", "rdparts"]
        if dstfs == "ext4":
            dirs += ["root"]

    return {
        "files": files,
        "usemoves": usemoves,
        "overwrites": overwrites,
        "dirs": dirs,
    }


def updinst_exec(src, dst, pd):
    usemoves = pd["usemoves"]
    files = pd["files"]

    for d in pd["dirs"]:
        os.makedirs(dst + os.path.sep + d, exist_ok=True)

    os.chdir(src)
    moves = []
    for fl, td in files:
        fn = dst + os.path.sep + td + os.path.basename(fl[0])
        fnn = fn + ".new" if usemoves else fn
        if usemoves:
            moves.append((fnn, fn))
        if os.path.exists(fnn):
            os.unlink(fnn)
        if len(fl) > 1:
            with open(fnn, "wb") as tf:
                if not sub(["cat"] + list(fl), stdout=tf):
                    sys.exit(f"Writing uprade file {fnn} failed")
        else:
            if not sub(["cp", fl[0], fnn]):
                sys.exit(f"Copying upgrade file {fl[0]} failed")

    for frm, to in moves:
        os.replace(frm, to)

    os.chdir("/")


def desc_moves(pd):
    if pd["usemoves"]:
        print("Will write new files as filename.new and rename to filename")
    else:
        print("Upgrade will write directly over previous files (low disk space).")


def fetch_check_iso(filename=None, version=None):
    import urllib.request
    import shutil

    if version:
        if not filename:
            filename = f"i586con-{version}.iso"
    if not filename:
        return None

    with open(cfgdir + "upstreamurl") as f:
        urlbase = f.read().strip()

    r = urllib.request.urlopen(urlbase + filename, timeout=30)
    rlen = int(r.headers["Content-Length"])
    print(f"Downloading {rlen/1024.:.1f} KiB")
    with open(filename, "w+b") as tgt:
        l = 0
        p = 0
        while True:
            d = r.read(32 * 1024)
            if not d:
                break
            tgt.write(d)
            l += len(d)
            np = (l * 100) // rlen
            if np > p:
                inc = np - p
                print("." * inc, end="", flush=True)
                p = np  # lmao

    print("")

    asc = filename + ".asc"
    print("Fetching signature...")
    r = urllib.request.urlopen(urlbase + asc, timeout=30)
    with open(asc, "w+b") as tgt:
        shutil.copyfileobj(r, tgt)

    print("Verifying signature...")
    cmd = ["gpgv", "--keyring", cfgdir + "pubkey.gpg", asc, filename]
    if not sub(cmd):
        print("Verification failed :(")
        print(
            "This means the .iso could've been tampered with - or just a bad download."
        )
        print("Bailing out for you to check out the wreckage...")
        sys.exit(1)

    # Cleanup the sig file (we've already verified it, and the calling code doesnt care about it)
    unlink(asc)
    print("Download and verify complete - continuing...")
    return filename


def get_latest_iso_version():
    import urllib.request
    import json

    with open(cfgdir + "upstreamurl") as f:
        urlbase = f.read().strip()

    r = urllib.request.urlopen(urlbase + "latest.json.asc", timeout=30)
    # The old gnupg we shipped makes this a whopper of a command...
    cmd = [
        "gpg",
        "--no-default-keyring",
        "--keyring",
        cfgdir + "pubkey.gpg",
        "--trust-model",
        "always",
        "--decrypt",
        "-o",
        "-",
        "-",
    ]
    blob = r.read()
    jsonb = sub(cmd, input=blob, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if not jsonb:
        print("Fetching and verifying latest.json.asc failed :(")
        sys.exit(1)

    return json.loads(jsonb.decode())


def my_version():
    with open(cfgdir + "version") as f:
        return f.read().strip()
