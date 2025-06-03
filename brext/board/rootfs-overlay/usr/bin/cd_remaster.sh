#!/bin/bash
# A script to make a modified version of i586con.iso, while needing only the space for the
# modified files and the new .iso file (and the old .iso, but that can mounted from the previous CD.)
if [ "$#" -lt 2 ]; then
	# Old-dir is a mounted CD (eg. /cd) or for example loopback-mounted i586con.iso from the internet.
	# (mount -o loop,ro -t iso9660 new-i586con.iso /somewhere)
	echo "usage: $0 <old-dir> <new.iso> [tmpdir]"
	exit 1
fi
set -e
TDIR="${3:-/tmp/cd_remaster}"
TDIR=$(realpath "$TDIR")
NEWISO=$(realpath `dirname "$2"`)/$(basename "$2")
mkdir -p $TDIR/{rw,wk,isofs.tmp}
mount -t overlay overlay -o index=off,metacopy=off,lowerdir=$1,upperdir=$TDIR/rw,workdir=$TDIR/wk $TDIR/isofs.tmp
cd $TDIR/isofs.tmp
echo "Now, add/modify files as desired in this directory ($(pwd)). Exit when ready to create $NEWISO."
set +e
bash
set -e
cd $TDIR
genisoimage -V I586CON -J -r -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -o "$NEWISO" isofs.tmp
isohybrid -t 0x96 "$NEWISO"
umount -l $TDIR/isofs.tmp
echo "New .iso image ($NEWISO) made. Now you're ready to burn it, if you want to. For example:"
echo "wodim blank=fast dev=/dev/sr0 -multi $NEWISO"
echo "Remove blank if youre burning a CD-R, remove -multi if you want a finished CD (no cd_save)."
