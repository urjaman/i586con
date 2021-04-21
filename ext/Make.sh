#!/bin/bash
BASEDIR="$(realpath .)"
cd "${BASH_SOURCE%/*}/" || exit
. ./env.sh

if [ ! -d make-4.3 ]; then
	wget http://ftp.gnu.org/gnu/make/make-4.3.tar.gz
	tar xvf make-4.3.tar.gz
	cd make-4.3
else
	cd make-4.3
	make distclean
fi

./configure --prefix=/opt/tcc   \
            --without-guile \
            --host=i586-buildroot-linux-musl \
            --build=$(build-aux/config.guess)

make
make DESTDIR=$EXTDIR install
i586-buildroot-linux-musl-strip --strip-unneeded $EXTDIR/opt/tcc/bin/make
