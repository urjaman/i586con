#!/bin/sh
set -e
set -x
BR_V=2019.11.1
BR_N=buildroot-$BR_V.tar.bz2
wget https://buildroot.org/downloads/$BR_N
tar xf $BR_N
