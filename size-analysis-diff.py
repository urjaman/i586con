#!/usr/bin/env python3

import os
import sys

(oldfn, newfn) = sys.argv[1:]


#print(oldfn,newfn)

#file-lines :P
fl = {}

numtrans = str.maketrans("0123456789", "N" * 10)

with open(oldfn) as f:
    for line in f:
        sz, name = line.strip().split()
        szi = int(sz)
        fl[name] = [szi, None]

with open(newfn) as f:
    for line in f:
        sz, name = line.strip().split()
        szi = int(sz)
        if name in fl:
            fl[name][1] = szi
        else:
            nameN = name.translate(numtrans)
            for exname in fl:
                exN = exname.translate(numtrans)
                if nameN == exN:
                    exE = fl[exname]
                    del fl[exname]
                    fl[nameN] = exE
                    fl[nameN][1] = szi
                    break
            else:
                fl[name] = [None, szi]

new = {}
lost = {}

for k in fl:
    e = fl[k]
    if e[0] is None:
        new[k] = e
        continue
    if e[1] is None:
        lost[k] = e
        continue
    print(e[1] - e[0], "\t" + k)

if len(new):
    #print("New entries:")
    for k in new:
        e = new[k]
        print(e[1], "\tNew:" + k)


if len(lost):
    #print("Lost entries:")
    for k in lost:
        e = lost[k]
        print(-e[0], "\tLost:" + k)
