#!/bin/sh
echo "XXXXXXXXXXXXXX RUNNING POST BUILD SCRIPT XXXXXXXXXXXXXXXXXX"
cd "$1/etc/init.d"
# do not autostart sshd like this (started by the net scripts)
[ -e S50sshd ] && mv S50sshd N50sshd
# do not auto-do the urandom stuff since we have no randomness on a CD
[ -e S20urandom ] && mv S20urandom N20urandom
# do not autostart telnetd, FFS (it exists to allow manual careful use in controlled environments, not autorunning lol)
[ -e S50telnet ] && mv S50telnet N50telnet
# no sysctls are used, thus get rid of it
rm -f S02sysctl
# do not wait to settle udev before giving a prompt, the
# login/VTs work just fine without udev too :P
sed -i '/udevadm settle/d' S10udev
cd "$1/etc"
# Add a bunch of getty's and the log VT
grep -q tty2 inittab || sed -i '31 a tty2::respawn:/sbin/getty -L tty2 0 linux' inittab
grep -q tty3 inittab || sed -i '32 a tty3::respawn:/sbin/getty -L tty3 0 linux' inittab
grep -q tty4 inittab || sed -i '33 a tty4::respawn:/sbin/getty -L tty4 0 linux' inittab
grep -q tty5 inittab || sed -i '34 a tty5::respawn:/sbin/getty -L tty5 0 linux' inittab
grep -q tty6 inittab || sed -i '35 a tty6::respawn:/sbin/getty -L tty6 0 linux' inittab
grep -q tty7 inittab || sed -i '36 a tty7::respawn:/usr/bin/tail -f /var/log/messages' inittab
# Add an empty line to the issue text if it's only one line right now :)
[ "$(cat issue | wc -l)" -lt 2 ] && echo >> issue
cd "$1"
# non-english mc help files? ehh...
rm -rf usr/share/mc/help/mc.hlp.*
# we only need the posix zoneinfo (if even that but i like the idea...)
rm -rf usr/share/zoneinfo/right
# these python modules are not needed for our use case (of mostly a calculator), really...
rm -rf usr/lib/python*/{ensurepip,distutils,unittest,email,turtle*}
# the stdcpp gdb helper thing is very not needed
rm -f usr/lib/libstdc++.so.*-gdb.py
# we only need smartctl, not the rest of smartmontools
rm -f usr/sbin/update-smart-drivedb
rm -f usr/sbin/smartd
rm -f etc/smartd_warning.sh
rm -f etc/smartd.conf
rm -rf etc/smartd_warning.d
cd "$1/usr/share"
# In case hwdata installs pci.ids, there can be a duplicate pci.ids.gz from pciutils
# the hwdata non-gzipped one compresses better in squashfs so remove the gz and add
# a link for pciutils to understand where the hwdata one is.
[ -f pci.ids.gz ] && [ -f hwdata/pci.ids ] && (rm pci.ids.gz; ln -s hwdata/pci.ids pci.ids)
exit 0
