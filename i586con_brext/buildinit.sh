#!/bin/sh
BRDIR="$(realpath buildroot-*)"
BUILDDIR="$(realpath *_build)"
EXTDIR="$(realpath *_brext)"
CONFIGNAME=i586con_defconfig
echo Buildroot dir: $BRDIR
echo Build dir: $BUILDDIR
echo BR2_External dir: $EXTDIR
echo defconfig to be used: $CONFIGNAME
echo Press enter to continue
read dummy

echo Cleaning build dir
rm -rf $BUILDDIR
mkdir -p $BUILDDIR

echo Configuring...
cd $BUILDDIR
make BR2_EXTERNAL=$EXTDIR O=$BUILDDIR -C $BRDIR $CONFIGNAME
echo Dropping you to a shell in the build dir
bash
