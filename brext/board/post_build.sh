#!/bin/bash
echo "XXXXXXXXXXXXXX RUNNING POST BUILD SCRIPT XXXXXXXXXXXXXXXXXX"
cd "$1/etc/init.d"
# do not autostart sshd like this (started by the net scripts)
[ -e S50sshd ] && mv S50sshd N50sshd
# sshd starts up faster if we just use ED25519 host key... thus:
# disable but leave commented the ssh-keygen -A call
grep -q '#/usr/bin/ssh-keygen' N50sshd || sed -i '16 s|/usr/bin/ssh-keygen|#/usr/bin/ssh-keygen|' N50sshd
# add a special call to only make an ED25519 host key
grep -q 'ed25519' N50sshd || sed -i $'16 a \\\t[ -e /etc/ssh/ssh_host_ed25519_key ] || /usr/bin/ssh-keygen -q -N "" -t ed25519 -f /etc/ssh/ssh_host_ed25519_key' N50sshd
# config sshd to expect just ED25519
sed -i 's|#HostKey /etc/ssh/ssh_host_ed25519_key|HostKey /etc/ssh/ssh_host_ed25519_key|' ../ssh/sshd_config
# do not auto-do the urandom stuff since we have no randomness on a CD
[ -e S20urandom ] && mv S20urandom N20urandom
[ -e S20seedrng ] && mv S20seedrng N20seedrng
# do not autostart telnetd, FFS (it exists to allow manual careful use in controlled environments, not autorunning lol)
[ -e S50telnet ] && mv S50telnet N50telnet
# no sysctls are used, thus get rid of it
rm -f S02sysctl
# do not wait to settle udev before giving a prompt, the
# login/VTs work just fine without udev too :P
grep -q children-max S10udev || sed -i 's/UDEVD_ARGS="-d"/UDEVD_ARGS="--children-max=2 -d"/g' S10udev
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
rm -rf usr/lib/python*/{ensurepip,distutils,unittest,turtle*,multiprocessing}
# this "leaking" is a python3.mk bug
rm -f usr/bin/smtpd.py.*
# these modules are deprecated and not needed for us
rm -rf usr/lib/python*/{aifc,chunk,nntplib,pipes,sunau,xdrlib}.py*
# these modules arent needed by us
rm -rf usr/lib/python*/{doctest,mailbox,poplib}.py*
# the python config-*/ dir seems to be unnecessary on a target without C compiler, i think?
rm -rf usr/lib/python*/config-3.*

# the stdcpp gdb helper thing is very not needed
rm -f usr/lib/libstdc++.so.*-gdb.py
# we only need smartctl, not the rest of smartmontools
rm -f usr/sbin/update-smart-drivedb
rm -f usr/sbin/smartd
rm -f etc/smartd_warning.sh
rm -f etc/smartd.conf
rm -rf etc/smartd_warning.d
rm -rf usr/share/smartmontools
# We wanted libglib. We got libgio. None of what we wanted actually uses it, or so it seems.
# This is something to keep an eye on and test libglib-using stuff carefully (sshfs, mc)
rm -f bin/{gapplication,gdbus,gio,gio-querymodules,gresource,gsettings,gi-compile-repository,gi-*-typelib}
rm -f lib/libgio-2*
rm -f lib/libgirepository*
rm -rf usr/lib/gio
# After those are gone, a couple of other libg* things are just unused. For now, again.
rm -f lib/lib{gobject,gthread,gmodule}-*
# libevent is only there to allow us to build NTP package, from which we use ntpdate,
# which does not need libevent... thus get rid of libevent. This also needs care
# so that we dont accidentally build something against libevent ........ sigh.
rm -f lib/libevent*
rm -f usr/bin/event_rpcgen.py
# glib needs pcre2, but we dont need their test program(s) (?)
rm -f usr/bin/pcre2*
# The PCRE2 POSIX API is unused
rm -f usr/lib/libpcre2-posix.so.*

# e2fsprogs "debugfs" would use this, but we dont ship that
rm -f usr/lib/libss.so.*
rm -rf usr/share/et

# Nobody links to the C++ FLAC interface
rm -f usr/lib/libFLAC++.so.*

# Nobody uses the Stable ABI interface for python
rm -f usr/lib/libpython3.so

# Nobody uses libpsx (psx_syscall.h) provided by libcap
rm -f usr/lib/libpsx.so.*

# Sorry, no fancy key stuff with ssh for you
rm -f usr/bin/ssh-{add,agent,keyscan}
rm -f usr/libexec/ssh-pkcs11-helper
rm -f usr/libexec/ssh-keysign

# ALSA libatopology is not used by any of the tools we include
rm -rf usr/lib/libatopology.so*

# aserver is not necessary (?)
rm -f usr/bin/aserver

# libflashrom is not used by anything (even flashrom...)
rm -f usr/lib/libflashrom.so*

# more utils than we needed
rm -f usr/bin/{choom,colcrt,compile_et,devdump,enosys,fincore,mapscrn,metaflac,pcilmr,usbhid-dump}

# This is a hard one, but only one NTFS driver, please.
rm -f usr/bin/lowntfs-3g

# madplay provides A-B-X-testing ... we dont need that
rm -f usr/bin/abxtest

# more utils than we needed, sbin version
rm -f usr/sbin/{blkpr,blkzone,chcpu,fsfreeze,netscsid}

# udev has more *_id than we need
cd "$1/usr/lib/udev"
rm -f dmi_memory_id rules.d/70-memory.rules
rm -f fido_id rules.d/60-fido-id.rules
rm -f mtd_probe rules.d/75-probe_mtd.rules
rm -f v4l_id rules.d/60-persistent-v4l.rules

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
# Move memtest86+ to the images dir; we want it on the ISO, not in the filesystem
#mv boot/memtest* $BINARIES_DIR/ || true

# no info pages here
rm -fr share/info
# gnu tar is also prefix-confused and installs rmt (which we dont need) under /libexec
rm -fr libexec
cd "$1/usr/bin"
# give us ldd
if [ ! -e ldd ]; then
	cat <<- "EOF" > ldd
	#!/bin/sh
	exec /lib/ld-musl-i386.so.1 --list -- "$@"
	EOF
	chmod +x ldd
fi
# Add our own version file
cd "$1/etc"
$BR2_EXTERNAL_I586CON_PATH/util/version.sh > i586con/version
exit 0
