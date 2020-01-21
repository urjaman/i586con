if [ -z "${BASH_VERSION-}" ] ; then
	# Shell is not bash, get out.
	return
fi

. /etc/bash/bashrc
