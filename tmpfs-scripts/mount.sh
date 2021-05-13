#!/bin/sh
set -e
set -x
sudo mount -o size=14G -t tmpfs tmpfs bld
sudo chown urjaman:users bld
chmod 0755 bld
sudo swapon /home/urjaman/bigswap.bin
