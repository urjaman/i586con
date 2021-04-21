#!/bin/bash
BASEDIR="$(realpath .)"
cd "${BASH_SOURCE%/*}/" || exit
. ./env.sh

if [ ! -d tinycc ]; then
	#rm -rf tinycc.old
	#mv tinycc tinycc.old
	git clone https://repo.or.cz/tinycc.git -b mob
	cd tinycc
	# because mob can be committed to by _anyone_, pick a known commit (newest as of script writing time)
	# recommendation: clone tinycc, check the head for anything nasty, update the hash here if you like what you see :)
	# (just removing this line when mob "looks okay" can still have a race between your check and someone committing something)
	git checkout 58be11f701f44d1f4e06fb66d57527d82ca48296
else
	cd tinycc
	make clean distclean
fi
./configure --config-musl --cpu=i386 --cross-prefix=i586-buildroot-linux-musl- --prefix=/opt/tcc --crtprefix=/opt/tcc/lib --sysincludepaths=/opt/tcc/lib/tcc/include:/usr/local/include:/usr/include:/opt/tcc/include
make i386-libtcc1-usegcc=yes
DESTDIR=$EXTDIR make install
# The system as shipped by buildroot will not include any includes or other files needed for compilation & linking,
# so we need to pull them out of buildroot and "ship" them with our TCC extension :)

cp -va $BUILDDIR/host/i586-buildroot-linux-musl/sysroot/usr/include/* $EXTDIR/opt/tcc/include
cp -va $BUILDDIR/host/i586-buildroot-linux-musl/sysroot/usr/lib/crt{1,i,n}.o $EXTDIR/opt/tcc/lib

# TCC stdarg and musl stdarg (defined in bits/alltypes.h and also included from not-stdarg.h) are basically identical
# but clash in how they get defined, so remove the TCC stdarg and patch musl stdarg to apply the correct version to TINYC.
# Not exactly sure how this should be fixed in upstream TCC ...
rm -f $EXTDIR/opt/tcc/lib/tcc/include/stdarg.h
grep -q __TINYC__ $EXTDIR/opt/tcc/include/bits/alltypes.h || sed -i 's/__GNUC__ >= 3/__GNUC__ >= 3 || __TINYC__ >= 900/' $EXTDIR/opt/tcc/include/bits/alltypes.h
