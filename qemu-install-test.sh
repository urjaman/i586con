#!/bin/sh
FN=inst-test-$$.qcw2
qemu-img create -f qcow2 $FN 1G
qemu-system-i386 -m 60 -hda $FN -cdrom bld/images/i586con.iso -soundhw es1370
