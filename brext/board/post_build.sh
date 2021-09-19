#!/bin/bash
echo "XXXXXXXXXXXXXX RUNNING POST BUILD SCRIPT XXXXXXXXXXXXXXXXXX"
cd "$1/etc/init.d"
# do not autostart sshd like this (started by the net scripts)
[ -e S50sshd ] && mv S50sshd N50sshd
# sshd starts up faster if we just use ED25519 host key... thus:
# disable but leave commented the ssh-keygen -A call
grep -q '#ssh-keygen' N50sshd || sed -i 's/ssh-keygen/#ssh-keygen/' N50sshd
# add a special call to only make an ED25519 host key
grep -q 'ed25519' N50sshd || sed -i $'13 a \t[ -e /etc/ssh/ssh_host_ed25519_key ] || ssh-keygen -q -N "" -t ed25519 -f /etc/ssh/ssh_host_ed25519_key'
# config sshd to expect just ED25519
sed -i 's|#HostKey /etc/ssh/ssh_host_ed25519_key|HostKey /etc/ssh/ssh_host_ed25519_key|' ../ssh/sshd_config

# do not auto-do the urandom stuff since we have no randomness on a CD
[ -e S20urandom ] && mv S20urandom N20urandom
# do not autostart telnetd, FFS (it exists to allow manual careful use in controlled environments, not autorunning lol)
[ -e S50telnet ] && mv S50telnet N50telnet
# no sysctls are used, thus get rid of it
rm -f S02sysctl
# do not wait to settle udev before giving a prompt, the
# login/VTs work just fine without udev too :P
grep -q children-max S10udev || sed -i 's/udevd -d/udevd --children-max=2 -d/g' S10udev
sed -i '/udevadm settle/d' S10udev
cd "$1/etc"
# Add a bunch of getty's and the log VT
grep -q tty2 inittab || sed -i '31 a tty2::respawn:/sbin/getty -L tty2 0 linux' inittab
grep -q tty3 inittab || sed -i '32 a tty3::respawn:/sbin/getty -L tty3 0 linux' inittab
grep -q tty4 inittab || sed -i '33 a tty4::respawn:/sbin/getty -L tty4 0 linux' inittab
grep -q tty5 inittab || sed -i '34 a tty5::respawn:/sbin/getty -L tty5 0 linux' inittab
grep -q tty6 inittab || sed -i '35 a tty6::respawn:/sbin/getty -L tty6 0 linux' inittab
grep -q tty7 inittab || sed -i '36 a tty7::respawn:/usr/bin/tail -f /var/log/messages' inittab
grep -q "modprobe apm" inittab || sed -i '43 a ::shutdown:/sbin/modprobe apm' inittab

# Add an empty line to the issue text if it's only one line right now :)
[ "$(cat issue | wc -l)" -lt 2 ] && echo >> issue
# Don't give me a headache when tab-completing in the dark
sed -i 's/set bell-style visible/set bell-style none/' inputrc

# Fix hush' "noninteractive" parsing of profile,
# profile.d fragments can test SHFLAGS instead of $-
grep -q "SHFLAGS" profile
if [ $? -ne 0 ]; then
	sed -i '2 a SHFLAGS="$-"' profile
	sed -i '3 a [[ "$SHFLAGS" != *i* ]] && tty -s <&1 && tty -s && SHFLAGS="i$SHFLAGS"' profile
	sed -i 's/\[ "$PS1" \]/[[ "$SHFLAGS" == *i* ]]/' profile
	echo "unset SHFLAGS" >> profile
fi
cd "$1"
# non-english mc help files? ehh...
rm -rf usr/share/mc/help/mc.hlp.*
# we only need the posix zoneinfo (if even that but i like the idea...)
rm -rf usr/share/zoneinfo/right
# these python modules are not needed for our use case
rm -rf usr/lib/python*/{ensurepip,distutils,unittest,turtle*}
# the stdcpp gdb helper thing is very not needed
rm -f usr/lib/libstdc++.so.*-gdb.py
# we only need smartctl, not the rest of smartmontools
rm -f usr/sbin/update-smart-drivedb
rm -f usr/sbin/smartd
rm -f etc/smartd_warning.sh
rm -f etc/smartd.conf
rm -rf etc/smartd_warning.d
# We wanted libglib. We got libgio. None of what we wanted actually uses it, or so it seems.
# This is something to keep an eye on and test libglib-using stuff carefully (sshfs, mc)
rm -f bin/{gapplication,gdbus,gio,gio-querymodules,gresource,gsettings}
rm -f lib/libgio-2*
# After those are gone, a couple of other libg* things are just unused. For now, again.
rm -f lib/lib{gobject,gthread,gmodule}-*
# libevent is only there to allow us to build NTP package, from which we use ntpdate,
# which does not need libevent... thus get rid of libevent. This also needs care
# so that we dont accidentally build something against libevent ........ sigh.
rm -f lib/libevent*
cd "$1/usr/share"
# In case hwdata installs pci.ids, there can be a duplicate pci.ids.gz from pciutils
# the hwdata non-gzipped one compresses better in squashfs so remove the gz and add
# a link for pciutils to understand where the hwdata one is.
[ -f pci.ids.gz ] && [ -f hwdata/pci.ids ] && (rm pci.ids.gz; ln -s hwdata/pci.ids pci.ids)
cd "$1"
# get rid of the less useful (for our only old x86 use) grub tools
rm -f usr/bin/grub-{render-label,mount,mknetdir,syslinux2cfg,fstest,menulst2cfg,glue-efi} || true
rm -f usr/sbin/grub-{macbless,sparc64-setup} || true
# these are symbol & debug stuff (why does buildroot end up with them installed?)
rm -f usr/lib/grub/i386-pc/*.module || true
rm -f usr/lib/grub/i386-pc/*.image || true
rm -f usr/lib/grub/i386-pc/{kernel.exec,gdb_grub,gmodule.pl} || true
# and this is grub prefix messup that ... i dont even know, but we dont need it
rm -rf share || true
# this grub config is useless and confusing, get rid of it
rm -fr boot/grub
# no info pages here
rm -fr share/info
# gnu tar is also prefix-confused and installs rmt (which we dont need) under /libexec
rm -fr libexec
cd "$1/usr/bin"
# give us ldd
[ -e ldd ] || ln -s ../lib/ld-musl-* ldd
# Add our own version file
cd "$1/etc"
$BR2_EXTERNAL_I586CON_PATH/util/version.sh > i586con_version
exit 0
