#!/usr/bin/python3

import sys
import struct

# Okay so, injecting data into a squashfs initrd in a way where the kernel
# loads said data into the ramdisk (for later extraction via dd) was kinda
# hard (needed to fugde bytes_used) in kernel 5.4... kernel 5.10 made it
# ... kinda silly hard, but since I started it, I'm gonna do it.
# And yeah, this code creates a space in the "middle" of a squashfs image
# for the injected data, and mangles the absolute positions in the tables.
# Luckily (or maybe by design?) this seems to be possible without recompressing
# anything (exception being XATTR, but we dont use XATTR so it's ok).


def roundk(x, k):
    return (x + k - 1) & ~(k - 1)


def roundkd(x, k):
    return roundk(x, k) // k


class SBF:
    MAGIC = 0
    INODE_COUNT = 1
    MODIFICATION_TIME = 2
    BLOCK_SIZE = 3
    FRAGMENT_ENTRY_COUNT = 4
    COMPRESSION_ID = 5
    BLOCK_LOG = 6
    FLAGS = 7
    ID_COUNT = 8
    VERSION_MAJOR = 9
    VERSION_MINOR = 10
    ROOT_INODE_REF = 11
    BYTES_USED = 12
    ID_TABLE_START = 13
    XATTR_ID_TABLE_START = 14
    INODE_TABLE_START = 15
    DIRECTORY_TABLE_START = 16
    FRAGMENT_TABLE_START = 17
    EXPORT_TABLE_START = 18


class SQSB:
    struct_fmt = "<5L6H8Q"
    sb_len = struct.calcsize(struct_fmt)

    def __init__(s, f):
        s.dirty = False
        s.f = f
        f.seek(0, 0)
        s.sb = list(struct.unpack(s.struct_fmt, f.read(s.sb_len)))
        if s.sb[SBF.MAGIC] != 0x73717368:
            raise Exception("Not a SquashFS")

    def bytes_used(s):
        return s.sb[SBF.BYTES_USED]

    def datablocks_end(s):
        return s.sb[SBF.INODE_TABLE_START]

    def adj(s, id, amt):
        if s.sb[id] == 2 ** 64 - 1:
            return
        s.sb[id] += amt
        s.dirty = True

    def adj_list(s, id, cnt, amt):
        fmt = "<" + str(cnt) + "Q"
        ll = struct.calcsize(fmt)
        st = s.sb[id]
        if st == 2 ** 64 - 1:
            return

        s.adj(id, amt)

        s.f.seek(st, 0)
        vlist = list(struct.unpack(fmt, s.f.read(ll)))
        for i in range(cnt):
            vlist[i] += amt
        s.f.seek(st, 0)
        s.f.write(struct.pack(fmt, *vlist))

    def shuffle_tables(s, new_start):
        old_start = s.sb[SBF.INODE_TABLE_START]
        old_end = s.sb[SBF.BYTES_USED]
        amt = new_start - old_start
        if amt == 0:
            return

        if s.sb[SBF.XATTR_ID_TABLE_START] != 2 ** 64 - 1:
            raise Exception("XATTR not supported")

        s.adj_list(SBF.ID_TABLE_START, roundkd(s.sb[SBF.ID_COUNT], 2048), amt)
        s.adj_list(
            SBF.FRAGMENT_TABLE_START, roundkd(s.sb[SBF.FRAGMENT_ENTRY_COUNT], 512), amt
        )
        s.adj_list(SBF.EXPORT_TABLE_START, roundkd(s.sb[SBF.INODE_COUNT], 1024), amt)
        s.adj(SBF.INODE_TABLE_START, amt)
        s.adj(SBF.XATTR_ID_TABLE_START, amt)
        s.adj(SBF.DIRECTORY_TABLE_START, amt)
        s.adj(SBF.BYTES_USED, amt)
        bs = 64 * 1024
        if amt >= 0:  # increasing size? copy in reverse...
            rp = old_end
            while True:
                rem = rp - old_start
                if rem > bs:
                    rem = bs
                if not rem:
                    break
                rp -= rem
                s.f.seek(rp, 0)
                block = s.f.read(rem)
                s.f.seek(rp + amt, 0)
                s.f.write(block)
        else:
            rp = old_start
            while True:
                rem = old_end - rp
                if rem > bs:
                    rem = bs
                if not rem:
                    break
                s.f.seek(rp, 0)
                block = s.f.read(rem)
                s.f.seek(rp + amt, 0)
                s.f.write(block)
                rp += rem
            # decreasing size ? truncate
            s.f.truncate(s.bytes_used())

    def close(s):
        if s.dirty:
            s.f.seek(0, 0)
            s.f.write(struct.pack(s.struct_fmt, *tuple(s.sb)))
            s.dirty = False
        s.f.close()


class SQFS_Embed:
    # start (Q), len (L), align-offset (H), header checksum (H), magic (H)
    eh_fmt = "<QL3H"
    eh_magic = 0x8845
    eh_len = struct.calcsize(eh_fmt)
    cs_fmt = "<" + str(eh_len // 2) + "H"
    size_tol = 4096

    def checksum(s, ehb):
        csl = list(struct.unpack(s.cs_fmt, ehb))
        csl[-2] = 0
        cs = 0
        for i in csl:
            cs += i
        return cs & 0xFFFF

    def __init__(s, f):
        s.fs = SQSB(f)
        s.start = s.fs.datablocks_end()
        s.len = 0
        s.space = 0
        s.align_off = 0

        s.eh_off = s.fs.datablocks_end() - s.eh_len
        s.fs.f.seek(s.eh_off, 0)
        ehb = s.fs.f.read(s.eh_len)
        eh = struct.unpack(s.eh_fmt, ehb)
        if eh[-1] != s.eh_magic:
            # Nothing embedded
            return

        cs = s.checksum(ehb)
        if eh[-2] != cs:
            sys.stderr.write(
                "Embed Header checksum failure: "
                + hex(eh[-2])
                + " (expected) vs "
                + hex(cs)
                + " (computed)\n"
            )
            return

        if (eh[0] + eh[1] + eh[2]) > s.eh_off or eh[0] < s.fs.sb_len:
            sys.stderr.write("Embed Header consistency check failure\n")
            return

        s.start = eh[0]
        s.len = eh[1]
        s.align_off = eh[2]
        s.space = s.eh_off - s.start
        return

    def padend(s):
        bu = s.fs.bytes_used()
        bp = roundk(bu, 4096)
        if bp - bu:
            s.fs.f.seek(bu, 0)
            s.fs.f.write(bytes(bp - bu))
        s.fs.f.truncate(bp)

    def chunkcopy(s, fr, fw, len):
        bs = 64 * 1024
        done = 0
        while len > done:
            rl = bs if bs < (len - done) else len - done
            block = fr.read(rl)
            fw.write(block)
            done += rl

    def embed(s, fi, align):
        fi.seek(0, 2)
        size = fi.tell()
        fi.seek(0, 0)
        estart = roundk(s.start, align)
        esize = roundk(size, align)
        s.align_off = estart - s.start
        espace = s.space - s.align_off

        if not size:
            # Take embedding a zero-sized file as a special request to restore original squashfs;
            # Remove everything, incl. our header.
            if s.space:
                s.fs.shuffle_tables(s.start)
                s.padend()
                s.space = 0
                s.len = 0
                return
        elif (espace < esize) or (espace > (esize + s.size_tol)):
            s.space = s.align_off + esize + s.size_tol // 2
            s.eh_off = s.start + s.space
            newend = s.eh_off + s.eh_len
            s.fs.shuffle_tables(newend)

        s.len = size

        if s.align_off:
            s.fs.f.seek(s.start, 0)
            s.fs.f.write(bytes(s.align_off))

        s.fs.f.seek(s.start + s.align_off, 0)
        s.chunkcopy(fi, s.fs.f, s.len)
        free = s.eh_off - s.fs.f.tell()
        if free:
            s.fs.f.write(bytes(free))
        cs = s.checksum(
            struct.pack(s.eh_fmt, s.start, s.len, s.align_off, 0, s.eh_magic)
        )
        s.fs.f.write(struct.pack(s.eh_fmt, s.start, s.len, s.align_off, cs, s.eh_magic))
        s.padend()

    def read(s, fo):
        if s.len:
            s.fs.f.seek(s.start + s.align_off, 0)
            s.chunkcopy(s.fs.f, fo, s.len)

    def close(s):
        s.fs.close()


if __name__ == "__main__":
    dashd = False
    things = []
    align = 1024
    for a in sys.argv[1:]:
        if a == "-d":
            dashd = True
            continue
        elif a[0] != "-":
            things.append(a)
            if len(things) == 3:
                if a.isascii() and a.isdigit():
                    align = int(a)
                    if align & (align - 1) or align == 0:
                        sys.exit("Align not a Power of 2")
                else:
                    sys.exit("Invalid alignment param " + a)
            if len(things) > 3:
                sys.exit("Too many parameters")
        else:
            print("usage: " + sys.argv[0] + " [-d] <file.sqfs> [embedded.bin] [align]")
            sys.exit()

    if not things:
        sys.exit("SquashFS file is a required parameter")

    embedfile = things[1] if len(things) >= 2 else None

    mode = "rb" if dashd or not embedfile else "r+b"
    e = SQFS_Embed(open(things[0], mode))

    if dashd:
        if e.len:
            if embedfile:
                out = open(embedfile, "wb")
            else:
                out = sys.stdout.buffer
            e.read(out)
            out.flush()
            if embedfile:
                out.close()

    elif embedfile:
        fi = open(embedfile, "rb")
        e.embed(fi, align)
        e.fs.f.seek(0, 2)
        print("rd_size=" + str(e.fs.f.tell() // align))
        print("offset=" + str((e.start + e.align_off) // align))
        print("size=" + str(roundkd(e.len, align)))
    else:
        if not e.space:
            print("No embedded data detected")
        else:
            print("Embed Info:")
            print("Start:  " + str(e.start))
            print("Align:  " + str(e.align_off))
            print("Length: " + str(e.len))
            print("Space:  " + str(e.space))

    e.close()
