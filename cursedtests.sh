#!/bin/sh
set -e
basedir="$(pwd)"
iso="$basedir/$1"
mkdir -p "$2"
cd "$2"
FN=cursed.qcow
$basedir/cursedtester.py -S -Nnetwork-ssh qemu-system-i386 -curses -m 60 -cdrom "$iso" -device e1000,netdev=net0 -netdev user,id=net0,hostfwd=tcp::1586-:22
$basedir/cursedtester.py -2 -Nlowram-usb qemu-system-i386 -curses -m 16 -drive "if=none,id=stick,format=raw,file=$iso" -usb -device usb-storage,drive=stick -nic none
qemu-img create -f qcow2 $FN 1G
$basedir/cursedtester.py -I4 -Ninstall-b2r qemu-system-i386 -curses -m 48 -hda $FN -cdrom "$iso" -nic none
$basedir/cursedtester.py -G1 -Nhdboot qemu-system-i386 -curses -m 48 -hda $FN
rm -f $FN
