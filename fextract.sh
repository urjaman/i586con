#!/bin/sh
set -e
set -x
BR_V=$(cat br-version)
BR_N=buildroot-$BR_V.tar.bz2
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
patch -Np1 < ../patches4br/0001-package-links-graphics-mode-does-not-depend-on-Direc.patch
patch -Np1 < ../patches4br/slimmer-libopenssl.patch
patch -Np1 < ../patches4br/allow-fuse-module.patch
patch -Np1 < ../patches4br/links-force-no-libevent.patch
patch -Np1 < ../patches4br/grub2-hostfixes.patch
touch ../.fextract-ok-$BR_V
