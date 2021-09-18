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
    prefix = '<!DOCTYPE html>\n<html><head><meta charset="utf-8"/></head><body>'
    suffix = '</body></html>'
    if embeddable:
        prefix = ""
        suffix = ""

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

    presettings = [
            "font-family: monospace",
            "font-size: 16px",
            "display: table",
            f"color: {colors[7]}",
            f"background-color: {colors[0]}"
            ]
    css = "pre { " + '; '.join(presettings) + "; }\n"


    usedcol = []
    outhtml = "<pre>"
    infmt = False
    for y in range(screen.lines):
        format = ('default', 'default')
        os = ''
        line = screen.buffer[y]
        for x in range(screen.columns):
            crsr = False
            if not screen.cursor.hidden:
                if screen.cursor.x == x and screen.cursor.y == y:
                    outhtml += html_esc(os)
                    os = ''
                    crsr = True
            fmnew = (line[x].fg, line[x].bg)
            if line[x].bold or line[x].reverse: # undefault
                if fmnew[0] == 'default':
                    fmnew = ("white", fmnew[1])
                if fmnew[1] == 'default':
                    fmnew = (fmnew[0], "black")
            if line[x].bold and not fmnew[0].startswith("bright"):
                fmnew = ("bright" + fmnew[0], fmnew[1])
            if line[x].reverse:
                fmnew = (fmnew[1], fmnew[0])
            # re-default :P (this simplifies the output HTML)
            if fmnew[0] == 'white':
                fmnew = ('default', fmnew[1])
            if fmnew[1] == 'black':
                fmnew = (fmnew[0], 'default')
            if fmnew != format:
                e = '</span>' if infmt else ''
                outhtml += html_esc(os) + e
                infmt = False
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
                    outhtml += '<span class="' + ' '.join(clrclass) + '">'
                    infmt = True
                os = line[x].data
                format = fmnew
            else:
                os += line[x].data
            if crsr:
                outhtml += '<u>' + html_esc(os) + '</u>'
                os = ''
        outhtml += html_esc(os)
        if infmt:
            outhtml += '</span>'
            infmt = False
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
    EA("i586con login:", "root\r", to=100),
    EA('i586con ~ #', "poweroff\r", to=20),
    ]

events_ssh = [
    EA("Automatic boot in", "\r", to=10, L=19),
    EA("i586con login:", "user\r", to=100),
    EA('user@i586con ~ $',
        "mkdir -p .ssh\recho 'SSH-KEY' > .ssh/authorized_keys\rcd .ssh\r", to=20),
    EA('user@i586con ~/.ssh $', "while ! pidof sshd; do sleep 1; done; sleep 5; cd /\r", to=10),
    EA('user@i586con / $', ["ssh", "qemu-i586con", "exit"], to=400),
    EA('', "su -c poweroff\r", to=20),
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

def timeoutcheck(t, timeout, screen, descr):
    n = now() - t
    if n > timeout:
        print(f"{descr} Timeout {timeout}:")
        screenprint(screen, "cursed-timeout.html")
        sys.exit(1)


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
                to = events[eventi].timeout
                r = events[eventi].check_and_respond(screen)
                if r:
                    print(f"Event {eventi} Tripped {now() - t:.3f}/{to}:")
                    screenprint(screen, f"cursed-event{eventi}.html")
                    if isinstance(r, list):
                        subc(r)
                    else:
                        humanlytype(mstr,stream, r)
                    eventi += 1
                    counter = 0
                    t = now()
                    continue
                timeoutcheck(t, to, screen, f"Event '{events[eventi].match}'({eventi})")
            else:
                to = 80.0
                timeoutcheck(t, to, screen, "Shutdown")

            if counter >= 10:
                #print("Screen:")
                #screenprint(screen)
                counter = 0
    except OSError:
        pass

    os.close(mstr)
    print(f"Final Screen {now() - t:.3f}/{to}:")
    screenprint(screen, "cursed-finish.html")

    if eventi < len(events):
        print("Premature Shutdown.")
        sys.exit(1)

main()
