#!/bin/sh
if [ "$#" -ne 2 ]; then
	echo "Usage: $0 <buildroot-dir> <build-dir>"
	exit 1
fi
BRDIR="$(realpath $1)"
BUILDDIR="$(realpath $2)"
EXTDIR="$(realpath brext)"
CONFIGNAME=i586con_defconfig
echo Buildroot dir: $BRDIR
echo Build dir: $BUILDDIR
echo BR2_External dir: $EXTDIR
echo defconfig to be used: $CONFIGNAME
echo Press enter to continue
read dummy

mkdir -p $BUILDDIR
set -x
echo Configuring...
cd $BUILDDIR
make BR2_EXTERNAL=$EXTDIR O=$BUILDDIR -C $BRDIR help
make BR2_EXTERNAL=$EXTDIR O=$BUILDDIR -C $BRDIR $CONFIGNAME
echo Dropping you to a shell in the build dir
bash
