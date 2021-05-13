#!/bin/sh
# Nothing should end up there, but in case
# something goes wrong... (or debug "echo"'s)
NETDBG=/tmp/netdaemon-dbg-out
exec >>$NETDBG 2>>$NETDBG </dev/null
LOG="logger -t net_daemon -p daemon.info"
NETPIPE=/tmp/.netdaemon-pipe
NETUP_FLAG=/tmp/.net-up
rm -f $NETPIPE
mkfifo -m 0600 $NETPIPE
echo $$ > /tmp/netdaemon-pid
while true; do
	while read cmd params; do
		if [ "$cmd" != "netup" ]; then
			$LOG "Unknown cmd: $cmd $params"
			continue
		fi
		if [ -e "$NETUP_FLAG" ]; then
			$LOG "Network already up, interface $params ignored"
			continue
		fi
		if udhcpc -i $params -n -S -x "hostname:$(hostname)"; then
			touch $NETUP_FLAG
			$LOG "Received IP from $params: net is up, doing ntpdate+sshd"
			N=$(dd if=/dev/urandom bs=1 count=1 status=none | od -An -to1 | tail -c 2)
			## Note: pls change to your local preferred NTP server
			ntpdate -bs $((N & 3)).pool.ntp.org
			## ^ More notes on that:
			## I wish i had an ntp pool for the project but no way am i gonna ask for
			## one for a toy project with basically no users... so best i can do is
			## this: we ask a random main pool server for time once on boot - and
			## based on the use case the boot was likely by an actual user...
			/etc/init.d/N50sshd start
		else
			$LOG "No IP from interface $params"
		fi
	done < $NETPIPE
done
