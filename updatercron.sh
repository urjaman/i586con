#!/bin/sh
mkdir -p logs
screen -h 1000 -L -Logfile "logs/$(date +%y%m%d)-$$.log" -dmS i586con-autoupdater -t i586con-bb flock -n updatercron.lock ./autoupdater.py --email
