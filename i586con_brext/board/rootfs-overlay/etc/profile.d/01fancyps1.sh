# Hush does not provide PS1/PS2 when it is initially running the profile script,
# even during an interactive login. Thus the only way to find out if we're
# interactive is to ask tty if stdin is a tty... not a tty -> not interactive
tty -s
if [ $? -ne 0 ]; then
	# Shell is non-interactive.  Be done now!
	return
fi

use_color=false

case ${TERM} in
[aEkx]term*|rxvt*|gnome*|konsole*|screen|cons25|*color|linux) use_color=true;;
esac

if ${use_color} ; then
	if [ "`id -u`" -eq 0 ]; then
		PS1='\[\033[01;31m\]\h\[\033[01;34m\] \W \$\[\033[00m\] '
	else
		PS1='\[\033[01;32m\]\u@\h\[\033[01;34m\] \w \$\[\033[00m\] '
	fi
else
	if [ "`id -u`" -eq 0 ]; then
		# show root@ when we don't have colors
		PS1='\u@\h \W \$ '
	else
		PS1='\u@\h \w \$ '
	fi
fi
export PS1
unset use_color
