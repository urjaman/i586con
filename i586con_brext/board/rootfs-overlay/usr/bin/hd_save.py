#!/usr/bin/python3

import os
import sys
import subprocess
import sqfs_embed


def sub(*args, **kwargs):
    return subprocess.run(*args, **kwargs).returncode == 0


def splice_par(l, par, val):
    cut = l.find(par)
    pre = l[:cut]
    (dummy, post) = l[cut:].split(" ", 1)
    return pre + par + val + " " + post


def mount_boot():
    boot_part = "/dev/disk/by-label/I586CON_BOOT"

    if os.path.exists(boot_part) is False:
        sys.exit("Boot partition not found")

    if sub(["mountpoint", "-q", "/boot"]):
        sub(["umount", "/boot"])

    if sub(["mount", "-t", "ext4", boot_part, "/boot"]) is False:
        sys.exit("Mounting boot partition failed")


def hd_save():
    save_tmp = "/boot/save.cpio.gz"
    save_cmd = "cpio -omH newc < /etc/saved_files | gzip -9 > " + save_tmp

    if not sub(save_cmd, shell=True):
        sys.exit("Creation of the save archive failed")

    e = sqfs_embed.SQFS_Embed(open("/boot/initrd.sqf", "r+b"))
    with open(save_tmp, "rb") as fi:
        k = 1024
        e.embed(fi, k)
        e.fs.f.seek(0, 2)
        rd_size = e.fs.f.tell() // k
        off_k = (e.start + e.align_off) // k
        size_k = sqfs_embed.roundkd(e.len, k)
    e.close()
    os.unlink(save_tmp)

    # Re-adjust the sizes & offsets in grub.cfg
    # (Offset should be static after the first hd_save, but easier to just be able to edit it all)

    grub_cfg = "/boot/grub/grub.cfg"
    grub_cfg_new = grub_cfg + ".new"

    rd_size_s = "brd.rd_size="
    offset_s = "i586con.offset="
    size_s = "i586con.size="

    with open(grub_cfg_new, "w") as fout:
        with open(grub_cfg, "r") as fin:
            for l in fin:
                if rd_size_s in l:
                    l = splice_par(l, rd_size_s, str(rd_size))
                    if offset_s in l:
                        l = splice_par(l, offset_s, str(off_k))
                    else:
                        l = l[:-1] + " " + offset_s + str(off_k) + "\n"
                    if size_s in l:
                        l = splice_par(l, size_s, str(size_k))
                    else:
                        l = l[:-1] + " " + size_s + str(size_k) + "\n"
                fout.write(l)

    os.replace(grub_cfg_new, grub_cfg)
    print("Save complete")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(sys.argv[0] + " takes no parameters")

    mount_boot()

    hd_save()

    sub(["umount", "/boot"])
