#!/bin/bash
set -e

# This silly slow script asks the question:
# How much smaller would the squashfs be if file/dir X wasnt included?
# in a very brute-force way. To make it slightly less silly slow,
# we only analyse directories and "big" (heuristically 64k now) files.

# N.B. For smaller files the answer to that question can actually be negative,
# that is the file was very beneficial for the compression of other files...

# Usually my usage is to redirect the output to a file, and sort -n it later.

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <build-dir>"
	exit 1
fi

cd $1

# For proper operation match these to your settings :)
SQP="-comp zstd -b 256K"
TF=/tmp/tst-$$.sqfs

TFN="rm -f $TF"
# nopad only for the analysis to help in accuracy
# (OTOH, such accuracy not really necessary when the output is padded so idk ...)
SQC="mksquashfs target $TF -nopad $SQP"

$SQC >/dev/null
FULL_SIZE="$(stat --printf=%s $TF)"
FULL_SIZE=$((FULL_SIZE / 1024))
printf "%d\t.\n" $FULL_SIZE
$TFN

while read line; do
	if [ -n "$line" ]; then
		$SQC -e $line >/dev/null
		TEST_SIZE="$(stat --printf=%s $TF)"
		TEST_SIZE=$((TEST_SIZE / 1024))
		DELTA=$((FULL_SIZE - TEST_SIZE))
		printf "%d\t$line\n" $DELTA
		$TFN
	fi
done < <(cd target; find -type d -o \( -type f -a -size +65536c \) | cut -b 3-)
