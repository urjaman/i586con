#!/bin/sh
set -e
set -x
BR_V=2020.02.3
BR_N=buildroot-$BR_V.tar.bz2
wget https://buildroot.org/downloads/$BR_N
tar xf $BR_N
cp -n 0003-genisoimage-outfile-extern.patch buildroot-$BR_V/package/cdrkit/
