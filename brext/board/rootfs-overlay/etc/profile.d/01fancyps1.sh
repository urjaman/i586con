if [[ "$SHFLAGS" != *i* ]]; then
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

# Change the window title of X terminals
case ${TERM} in
	[aEkx]term*|rxvt*|gnome*|konsole*|interix|tmux*)
		WINTIT='\[\033]0;\u@\h:\w\007\]'
		;;
	screen*)
		WINTIT='\[\033k\u@\h:\w\033\\\]'
		;;
	*)
		WINTIT=''
		;;
esac
PS1="$WINTIT$PS1"

export PS1
unset use_color
unset WINTIT
