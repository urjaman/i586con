#!/bin/sh
echo "net_screen.sh for interface $1 (waiting for sequencing lock)"
NETUP_FLAG=/tmp/.net-up
NETUP_LOCK=/tmp/.net-up-lock
(
	flock 9
	if [ -e "$NETUP_FLAG" ]; then
		echo "Net already up, will not try to dhcp a second interface"
	else
		echo "Attempting DHCP..."
		if udhcpc -i $1 -n -S -x "hostname:$(hostname)"; then
			echo "Received IP, marking net as up and starting sshd"
			touch $NETUP_FLAG
			/etc/init.d/N50sshd start
			echo "Net up complete"
		else
			echo "No IP received :("
		fi
	fi
	flock -u 9
) 9>>$NETUP_LOCK
echo "(Press enter to close this screen)"
read dummy
exit 0
