#!/bin/sh
set -e
FN=cursed.qcow
rm -f $FN
./cursedtester.py -S -Nnetwork-ssh qemu-system-i386 -curses -m 60 -cdrom "$1" -device e1000,netdev=net0 -netdev user,id=net0,hostfwd=tcp::1586-:22
./cursedtester.py -2 -Nlowram-usb qemu-system-i386 -curses -m 16 -drive "if=none,id=stick,format=raw,file=$1" -usb -device usb-storage,drive=stick -nic none
qemu-img create -f qcow2 $FN 1G
./cursedtester.py -I4 -Ninstall-b2r qemu-system-i386 -curses -m 48 -hda $FN -cdrom "$1" -nic none
./cursedtester.py -G1 -Nhdboot qemu-system-i386 -curses -m 48 -hda $FN
