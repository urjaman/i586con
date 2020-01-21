#!/bin/sh
echo "XXXXXXXXXXXXXX RUNNING POST BUILD SCRIPT XXXXXXXXXXXXXXXXXX"
cd "$1/etc/init.d"
[ -e S50sshd ] && mv S50sshd N50sshd
[ -e S20urandom ] && mv S20urandom N20urandom
sed -i '/udevadm settle/d' S10udev
cd "$1/etc"
#grep -q devtmpfs inittab || sed -i '17 a ::sysinit:/bin/mount -t devtmpfs devtmpfs /dev' inittab
grep -q tty2 inittab || sed -i '31 a tty2::respawn:/sbin/getty -L tty2 0 linux' inittab
grep -q tty3 inittab || sed -i '32 a tty3::respawn:/sbin/getty -L tty3 0 linux' inittab
grep -q tty4 inittab || sed -i '33 a tty4::respawn:/sbin/getty -L tty4 0 linux' inittab
grep -q tty5 inittab || sed -i '34 a tty5::respawn:/sbin/getty -L tty5 0 linux' inittab
grep -q tty6 inittab || sed -i '35 a tty6::respawn:/sbin/getty -L tty6 0 linux' inittab
grep -q tty7 inittab || sed -i '36 a tty7::respawn:/usr/bin/tail -f /var/log/messages' inittab
cd "$1"
rm -rf usr/share/mc/help/mc.hlp.*
rm -rf usr/share/zoneinfo/right
exit 0
