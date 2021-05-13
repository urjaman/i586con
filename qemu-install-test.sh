#!/bin/sh
FN=inst-test-$$.qcw2
qemu-img create -f qcow2 $FN 1G
qemu-system-i386 -m 60 -hda $FN -cdrom bld/images/i586con.iso -device ES1370 -device e1000,netdev=net0 -netdev user,id=net0,hostfwd=tcp::1586-:22
