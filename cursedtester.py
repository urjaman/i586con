#!/usr/bin/env python3
import os
import sys
import pty
import time
from select import select
import subprocess
from subprocess import DEVNULL, PIPE, STDOUT

# This you get with pacman -S python-pyte or similar :)
import pyte

def now():
    return time.clock_gettime(time.CLOCK_MONOTONIC)


def subc(*args, **kwargs):
    c = subprocess.run(*args, **kwargs)
    if c.returncode != 0:
        print("subprocess failed: ", args)
        print("code:", c.returncode)
        sys.exit(1)
    return c.stdout


def setwinsz(fd, rows, cols):
    from fcntl import ioctl
    from struct import pack
    from tty import TIOCSWINSZ
    winsz = pack('HHHH', rows, cols, 0, 0)
    ioctl(fd, TIOCSWINSZ, winsz)

#setwinsz(0,30,90)

def boxit(argv, rows=25, cols=80):
    e = dict(os.environ)
    e['TERM'] = 'linux' # standardize on what pyte understands well
    pid, master = pty.fork()
    if pid == 0:
        setwinsz(0, rows, cols)
        os.execvpe(argv[0], argv, e)
    setwinsz(master, rows, cols)
    return master

# Event->Action (Match-Reply?)
# Anyways, this describes how the tester does things

class EA:
    def __init__(self, match, reply, to=30.0, L=-1):
        self.match = match
        self.reply = reply
        self.line = L
        self.timeout = to

    def check_and_respond(self, screen):
        disp = screen.display
        # None = full screen scan, default/-1 = cursor line, other = specific line
        if self.line is None:
            for y in range(len(disp)):
                if self.match in disp[y]:
                    return self.reply
        elif self.line == -1:
            line = screen.cursor.y
        else:
            line = self.line
        if self.match in disp[line]:
            return self.reply
        return None


def html_esc(s):
    escapes = {
        '&': '&amp;',
        '>': '&gt;',
        '<': '&lt;'
    }
    for k in escapes:
        s = s.replace(k, escapes[k])
    return s


def htmlscreen(screen, embeddable=False):
    prefix = "" if embeddable else "<html><head></head><body>"
    suffix = "" if embeddable else "</body></html>"
    css = "div { display: inline; }\n"
    css += "pre { font-family:monospace; font-size:16px; width: 80ch; color: #AAA; background-color: #000 }\n"
    colortab = {
    'black':        '0',
    "red":          '1',
    "green":        '2',
    "brown":        '3',
    "blue":         '4',
    "magenta":      '5',
    "cyan":         '6',
    "white":        '7',
    "brightblack":  '8',
    "brightred":    '9',
    "brightgreen":  'A',
    "brightbrown":  'B',
    "brightblue":   'C',
    "brightmagenta":'D',
    "brightcyan":   'E',
    "brightwhite":  'F'
    }
    colors = [ # spot the odd ones ;P
        "#000",
        "#A00",
        "#0A0",
        "#A50",
        "#5A26FF",
        "#A0A",
        "#0AA",
        "#AAA",
        # bright ones
        "#555", #brightblack. black light. intense darkness... *eyeroll*
        "#F55",
        "#5F5",
        "#FF5",
        "#9191D8",
        "#F5F",
        "#5FF",
        "#FFF"
    ]
    seq = "0123456789ABCDEF"
    colorcss = [ ]

    for i in range(16):
        c = seq[i]
        colorcss.append(f".F{c} {{ color: {colors[i]}; }}")

    for i in range(16):
        c = seq[i]
        colorcss.append(f".B{c} {{ background-color: {colors[i]}; }}")

    usedcol = []
    outhtml = "<pre>"
    indiv = False
    for y in range(screen.lines):
        format = ('default', 'default')
        os = ''
        line = screen.buffer[y]
        for x in range(screen.columns):
            fmnew = (line[x].fg, line[x].bg)
            if line[x].bold and not line[x].fg.startswith("bright"):
                fmnew = ("bright" + fmnew[0], fmnew[1])
            if fmnew != format:
                e = '</div>' if indiv else ''
                outhtml += html_esc(os) + e
                indiv = False
                if fmnew != ('default', 'default'):
                    clrclass = []
                    if fmnew[0] != 'default':
                        v = 'F' + colortab[fmnew[0]]
                        clrclass.append(v)
                    if fmnew[1] != 'default':
                        v = 'B' + colortab[fmnew[1]]
                        clrclass.append(v)
                    for c in clrclass:
                        if c not in usedcol:
                            usedcol.append(c)
                    outhtml += '<div class="' + ' '.join(clrclass) + '">'
                    indiv = True
                os = line[x].data
                format = fmnew
            else:
                os += line[x].data
        outhtml += html_esc(os)
        if indiv:
            outhtml += '</div>'
            indiv = False
        outhtml += "\n"
    outhtml += "</pre>"
    usedcolorcss = []
    for cv in colorcss:
        for v in usedcol:
            if cv[1:3] == v:
                usedcolorcss.append(cv)
                break
    style = "<style>\n" + css + '\n'.join(usedcolorcss) + '\n</style>'
    return prefix + style + outhtml + suffix


def screenprint(screen, filename=None):
    disp = screen.display
    for y in range(len(disp)):
        print(f"{y:02d} {disp[y]}")
    if filename:
        with open(filename, "w") as f:
            f.write(htmlscreen(screen))


events_simple = [
    EA("Automatic boot in", "\r", to=10, L=19),
    EA("i586con login:", "root\r", to=60),
    EA('i586con ~ #', "poweroff\r", to=20),
    ]

events_ssh = [
    EA("Automatic boot in", "\r", to=10, L=19),
    EA("i586con login:", "user\r", to=60),
    EA('user@i586con ~ $',
        "mkdir -p .ssh\recho 'SSH-KEY' > .ssh/authorized_keys\rcd .ssh\r", to=10),
    EA('user@i586con ~/.ssh $', "while ! pidof sshd; do sleep 1; done; cd /\r", to=10),
    EA('user@i586con / $', ["ssh", "qemu-i586con", "exit"], to=120),
    EA('', "su -c poweroff\r", to=10),
    ]

def streamfeed(mstr, stream, timeout=1.0):
    size = 0
    chunk = 1024
    while True:
        sr = select([mstr], [], [], timeout)
        if sr[0]:
            d = os.read(mstr, chunk)
            if not d:
                break
            size += len(d)
            stream.feed(d)
            if len(d) >= chunk:
                continue
        else:
            break
    return size

def humanlytype(mstr, stream, text):
    # This is "360 wpm" (world record stenotypers according to wiki, so at max "human" :P)
    # That is 360*5 / 60 = 30 chars/sec; bursted at 3 keys every 0.1s
    if 'SSH-KEY' in text:
        with open(os.environ['HOME'] + '/.ssh/id_rsa.pub') as kf:
            k = kf.read().strip()
        text = text.replace('SSH-KEY', k)

    def writekeys(b, k):
        B = b.encode()
        wo = 0
        while wo < len(B):
            wo += os.write(mstr, B[wo:])
        time.sleep(0.1)
        streamfeed(mstr, stream, 0.0)
        return '', 0

    b = ''
    k = 0
    o = 0
    while o < len(text):
        # We only use 3-length escape keyed keys (arrows) for now
        if text[o] == "\x1B":
            b += text[o:o+3]
            o += 3
        else:
            b += text[o]
            o += 1
        k += 1
        if k >= 3:
            b,k = writekeys(b, k)
    if k:
        writekeys(b, k)

def main():
    events = events_simple
    argn = 1
    if sys.argv[argn][0] == '-':
        if sys.argv[argn][1] == 'S':
            events = events_ssh
            bootentry = 0
            argn = 2
        else:
            try:
                bootentry = int(sys.argv[argn][1:])
                argn = 2
            except Exception:
                bootentry = 0
    else:
        bootentry = 0
    screen = pyte.Screen(80,25)
    stream = pyte.ByteStream(screen)
    mstr = boxit(sys.argv[argn:])
    t = now()
    if bootentry:
        events[0].reply = ("\x1b\x5b\x42" * bootentry) + '\r'

    counter = 0
    eventi = 0

    try:
        while True:
            try:
                counter += streamfeed(mstr, stream)
            except KeyboardInterrupt:
                break
            if eventi < len(events):
                r = events[eventi].check_and_respond(screen)
                if r:
                    print("Event Tripped - screen:")
                    screenprint(screen, f"cursed-event{eventi}.html")
                    if isinstance(r, list):
                        subc(r)
                    else:
                        humanlytype(mstr,stream, r)
                    eventi += 1
                    counter = 0
                    t = now()
                    continue
                n = now() - t
                if n > events[eventi].timeout:
                    print(f"Event '{events[eventi].match}'({eventi}) Timeout - screen:")
                    screenprint(screen, "cursed-timeout.html")
                    sys.exit(1)
            else:
                if (now() - t) > 80.0:
                    print("Shutdown Timeout - screen:")
                    screenprint(screen, "cursed-timeout.html")
                    sys.exit(1)

            if counter >= 10:
                #print("Screen:")
                #screenprint(screen)
                counter = 0
    except OSError:
        pass

    os.close(mstr)
    print("Final Screen:")
    screenprint(screen, "cursed-finish.html")

    if eventi < len(events):
        print("Premature Shutdown.")
        sys.exit(1)

main()
