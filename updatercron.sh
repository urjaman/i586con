#!/bin/sh
export PATH="/usr/local/sbin:/usr/local/bin:/usr/bin:/usr/lib/jvm/default/bin:/usr/bin/site_perl:/usr/bin/vendor_perl:/usr/bin/core_perl"
mkdir -p logs
screen -h 1000 -L -Logfile "logs/$(date +%y%m%d)-$$.log" -dmS i586con-autoupdater -t i586con-bb flock -n updatercron.lock ./autoupdater.py --email
