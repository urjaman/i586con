#!/bin/sh
set -e
set -x
BR_V=2021.02.2
BR_N=buildroot-$BR_V.tar.bz2
[ -e $BR_N ] || wget https://buildroot.org/downloads/$BR_N
tar xf $BR_N
(cd buildroot-$BR_V; patch -Np1 < ../patches4br/0001-package-links-graphics-mode-does-not-depend-on-Direc.patch)
(cd buildroot-$BR_V; patch -Np1 < ../patches4br/slimmer-libopenssl.patch)
(cd buildroot-$BR_V; patch -Np1 < ../patches4br/allow-fuse-module.patch)
(cd buildroot-$BR_V; patch -Np1 < ../patches4br/links-force-no-libevent.patch)
