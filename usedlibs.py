#!/usr/bin/env python3

import sys
import os
import subprocess
from subprocess import DEVNULL, PIPE, STDOUT

libs = {}
notfoundlibs = {}

def readelf(fn, add_lib=False):
    soname = None
    libnames = []
    cmd = ["readelf", "-d", fn]
    c = subprocess.run(cmd, stdout=PIPE, stderr=DEVNULL)
    if c.returncode != 0:
        return

    s = c.stdout.decode()

    for line in s.splitlines():
        if "(NEEDED)" in line:
            _,x = line.split("[")
            x,_ = x.split("]")
            libnames.append(x)
        if "(SONAME)" in line:
            _,x = line.split("[")
            x,_ = x.split("]")
            soname = x

    for lib in libnames:
        if lib in libs:
            libs[lib].append(fn)
        else:
            if lib in notfoundlibs:
                notfoundlibs[lib].append(fn)
            else:
                notfoundlibs[lib] = [fn]

    if add_lib:
        if soname is None:
            if "/" in fn:
                x = fn.split("/")
                x = x[-1]
            soname = x
        if soname in notfoundlibs:
            libs[soname] = notfoundlibs[soname]
            del notfoundlibs[soname]
        if soname not in libs:
            libs[soname] = []


os.chdir(sys.argv[1] + "/target")

findlibcmd = ["find", "usr/lib", "-maxdepth", "1", "-type", "f"]
c = subprocess.run(findlibcmd, stdout=PIPE)
if c.returncode != 0:
    sys.exit(1)

libfiles = c.stdout.decode().splitlines()

findexecmd = ["find", "-type", "f", "-executable"]
c = subprocess.run(findexecmd, stdout=PIPE)
if c.returncode != 0:
    sys.exit(1)

exefiles = c.stdout.decode().splitlines()

for file in libfiles:
    readelf(file, True)

for file in exefiles:
    file = file[2:]
    if file in libfiles:
        continue
    readelf(file, False)

for l in libs:
    users = libs[l]
    if users:
        print(l, "used by", ','.join(users))
    else:
        print(l, "UNUSED")

if len(notfoundlibs):
    for l in notfoundlibs:
        users = notfoundlibs[l]
        print(l, "NOT FOUND, NEEDED BY", ','.join(users))
