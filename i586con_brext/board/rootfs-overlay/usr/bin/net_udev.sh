#!/bin/sh
screen -XS bgscreen eval "screen -t net-$INTERFACE /usr/bin/net_screen.sh $INTERFACE"
exit 0
