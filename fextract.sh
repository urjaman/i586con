#!/bin/sh
set -e
set -x
BR_V=$(cat br-version)
BR_N=buildroot-$BR_V.tar.xz
[ -e $BR_N ] || wget https://buildroot.org/downloads/$BR_N
[ -e $BR_N.sign ] || wget https://buildroot.org/downloads/$BR_N.sign
# You'll need to have manually fetched and trusted their gpg key to use --verify
if [ "$1" == "--verify" ]; then
	# The signature they provide is an awkward signed message with SHA1 and SHA256
	# We're checking both to make sure
	gpg --output signed_sums --verify $BR_N.sign
	grep 'SHA1:' signed_sums | cut -f 2- -d ' ' | sha1sum -c
	grep 'SHA256:' signed_sums | cut -f 2- -d ' ' | sha256sum -c
	rm -f signed_sums
else
	# We check the SHA256 just for a transfer checksum
	grep 'SHA256:' $BR_N.sign | cut -f 2- -d ' ' | sha256sum -c
fi
tar xf $BR_N
mkdir -p dl
cd buildroot-$BR_V
ln -s ../dl dl
for p in ../patches4br/*; do
	patch -Np1 < $p
done
touch ../.fextract-ok-$BR_V
