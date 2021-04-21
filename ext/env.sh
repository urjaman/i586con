if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <build-dir>"
	exit 1
fi
BUILDDIR="$(realpath $BASEDIR/$1)"
export PATH=$BUILDDIR/host/bin:$PATH
EXTDIR=$BASEDIR/extdir
set -e
cd $BASEDIR
