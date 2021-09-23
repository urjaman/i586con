#!/usr/bin/env python3
import os
import sys
import pty
import time
import json
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
    def __init__(self, descr, match, reply, to=30.0, L=-1):
        self.desc = descr
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
        elif self.line < 0:
            line = screen.cursor.y + (self.line+1)
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

def link(tgt, text):
    return f'<a href="{tgt}">{html_esc(text)}</a>'

def htmlfinalize(usedcol, htmls, summary=None, embeddable=False):
    prefix = '<!DOCTYPE html>\n<html><head><meta charset="utf-8"/></head><body>'
    suffix = '</body></html>'
    if embeddable:
        prefix = ""
        suffix = ""

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

    # This is the most artsy part of the CSS
    stylecss = """
a:link, a:visited {
  color: #d70;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

h3 {
    margin: 0.1em;
}

body {
  font: 20px Helvetica,arial,freesans,clean,sans-serif;
  background-color: #1E1E1E;
  color: #C0C0C0;
}
"""

    # This onwards is CSS that relates technically to the terminal displays etc
    presettings = [
            "font-family: monospace",
            "font-size: 16px",
            "width: 80ch",
            f"color: {colors[7]}",
            f"background-color: {colors[0]}"
            ]
    css  = stylecss + "#spacer { height: calc(100vh - 400px) }\n"
    css += ".term { " + '; '.join(presettings) + "; }\n"

    fullout = ''
    off = 0
    spacerhtml = '\n<div id="spacer"><br/><br/></div>\n'

    for name, html in htmls:
        out = f"<h3 id=\"t{off}\">" + html_esc(name) + "</h3>\n"
        out += html
        if len(htmls) > 1:
            linklist = [("#t0", "<<FIRST<<"), (f"#t{off-1}", "<PREV<"),
                        (f"#t{off+1}", ">NEXT>"), (f"#t{len(htmls)-1}", ">>LAST>>")]
            links = []
            if off == 0:
                links.append(html_esc(linklist[0][1]))
                links.append(html_esc(linklist[1][1]))
            else:
                links.append(link(*linklist[0]))
                links.append(link(*linklist[1]))
            if off == len(htmls)-1:
                links.append(html_esc(linklist[2][1]))
                links.append(html_esc(linklist[3][1]))
            else:
                links.append(link(*linklist[2]))
                links.append(link(*linklist[3]))
            out += ' | '.join(links)

        off += 1
        if off < len(htmls):
            out += spacerhtml
        fullout += out

    usedcolorcss = []
    for cv in colorcss:
        for v in usedcol:
            if cv[1:3] == v:
                usedcolorcss.append(cv)
                break
    style = "<style>" + css + '\n'.join(usedcolorcss) + '\n</style>'
    if summary:
        fullout += "<pre>" + html_esc(summary) + "</pre>"
    fullout += spacerhtml
    return prefix + style + fullout + suffix

def htmlscreen(screen, usedcol = None):
    if usedcol is None:
        usedcol = []
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

    outhtml = '<pre class="term">'
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
    return outhtml

def summarytxt(gr, totaltime, finalevent):
    t = [
        f"=== SUMMARY for {gr['testname']} ===",
        " total time | wait time | event "
        ]
      # " 123456789s | 12345678s | blah "
    for desc, nt, wt in gr['history']:
        t.append(f" {nt:9.1f}s | {wt:8.1f}s | {desc}")
    t.append(f" {totaltime:9.1f}s |           | {finalevent}")
    return '\n'.join(t) + '\n'

def screenprint(screen, gr=None, desc=None, finalevt=False):
    nt = now() - gr['basetime']
    disp = screen.display
    for y in range(len(disp)):
        print(f"{y:02d} {disp[y]}")
    if gr and desc:
        h = htmlscreen(screen, gr['usedcol'])
        gr['htmls'].append((f"{desc} @ {nt:.1f}s" , h))
    if finalevt:
        summary = summarytxt(gr, nt, finalevt)
        print(summary, end='', flush=True)
        fn = f"test-{gr['testname']}.html"
        with open(fn, "w") as f:
            f.write(htmlfinalize(gr['usedcol'], gr['htmls'], summary))
        print(f"=== HTML: {fn}")


events_simple = [
    EA("bootloader", "Automatic boot in", "\r", to=10, L=19),
    EA("login prompt", "i586con login:", "root\r", to=100),
    EA("logged in", 'i586con ~ #', "poweroff\r", to=20),
    ]

events_ssh = [
    EA("bootloader", "Automatic boot in", "\r", to=10, L=19),
    EA("login prompt", "i586con login:", "user\r", to=100),
    EA("logged in", 'user@i586con ~ $',
        "mkdir -p .ssh\recho 'SSH-KEY' > .ssh/authorized_keys\rcd .ssh\r", to=20),
    EA("ssh key entered", 'user@i586con ~/.ssh $', "while ! pidof sshd; do sleep 1; done; sleep 5; cd /\r", to=10),
    EA("sshd started", 'user@i586con / $', ["ssh", "qemu-i586con", "exit"], to=400),
    EA("ssh test complete", '', "su -c poweroff\r"),
    ]

events_install = [
    EA("bootloader", "Automatic boot in", "\r", to=10, L=19),
    EA("login prompt", "i586con login:", "root\r", to=100),
    EA("logged in", 'i586con ~ #', "printf 'n\\n\\n\\n\\n\\nw\\n' | fdisk /dev/sda\r", to=20),
    EA("fdisk complete", 'Syncing disks.', "printf 'e\\n\\nyes\\n' | hdinstall /dev/sda1 /dev/sda\r", L=-3),
    EA("install complete", 'Installation complete', "poweroff\r", to=60, L=-2),
]

class AsciiCaster:
    def __init__(self, filename, width, height, term="linux"):
        import codecs

        self.file = open(filename,"w")
        initial = {
            'version': 2,
            'width': width,
            'height': height,
            'timestamp': int(time.time()),
            'env': { 'TERM': term },
        }
        j = json.dumps(initial)
        self.file.write(j + '\n')
        self.utf8_decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.tb = now()

    def close(self):
        self.file.close()
        self.file = None

    def cast(self, b):
        t = now() - self.tb
        s = self.utf8_decoder.decode(b)
        event = [ round(t,6), "o", s ]
        j = json.dumps(event)
        if self.file:
            self.file.write(j + '\n')

def streamfeed(gs, timeout=1.0):
    chunk = 1024
    while True:
        sr = select([gs['mstr']], [], [], timeout)
        if sr[0]:
            d = os.read(gs['mstr'], chunk)
            if not d:
                break
            gs['stream'].feed(d)
            gs['acast'].cast(d)
            if len(d) >= chunk:
                continue
        else:
            break
    return

def humanlytype(gs, text):
    if 'SSH-KEY' in text:
        with open(os.environ['HOME'] + '/.ssh/id_rsa.pub') as kf:
            k = kf.read().strip()
        text = text.replace('SSH-KEY', k)

    def writekeys(b):
        B = b.encode()
        wo = 0
        time.sleep(0.025)
        streamfeed(gs, 0.0)
        while wo < len(B):
            wo += os.write(gs['mstr'], B[wo:])
        time.sleep(0.05)
        streamfeed(gs, 0.0)
        return

    o = 0
    while o < len(text):
        # We only use 3-length escape keyed keys (arrows) for now
        if text[o] == "\x1B":
            b = text[o:o+3]
            o += 3
            writekeys(b)
            continue
        b = text[o]
        o += 1
        writekeys(b)

def timeoutcheck(t, timeout, screen, gr, descr):
    n = now() - t
    if n > timeout:
        print(f"{descr} Timeout {timeout}:")
        screenprint(screen, gr, "{descr} timeout", finalevt=f"{descr} - timeout")
        sys.exit(1)


def main():
    events = events_simple
    argn = 1
    bootentry = 0
    testname = 'cursed'
    debug_refresh = None

    for ai in range(1, len(sys.argv)):
        arg = sys.argv[ai]
        if arg[0] != '-':
            argn = ai
            break
        for ci in range(1, len(arg)):
            c = arg[ci]
            if c == 'S':
                events = events_ssh
            elif c == 'I':
                events = events_install
            elif c == 'G':
                events[0] = EA("GRUB", "The highlighted entry will be executed automatically in", "\r", to=20, L=22)
            elif c == 'N':
                testname = arg[ci+1:]
                break
            elif c == 'R':
                debug_refresh = float(arg[ci+1:])
                break
            elif c.isnumeric():
                bootentry = int(c)
            else:
                print("Umm... ?")
                sys.exit(1)
        argn = ai + 1

    screen = pyte.Screen(80,25)
    stream = pyte.ByteStream(screen)
    mstr = boxit(sys.argv[argn:], screen.lines, screen.columns)
    caster = AsciiCaster(f"test-{testname}.cast", screen.columns, screen.lines)

    t = basetime = now()
    if bootentry:
        print(f"Bootentry: {bootentry}")
        events[0].reply = ("\x1b\x5b\x42" * bootentry) + '\r'

    # Globals for Report-generation
    gr = {
        'testname': testname,
        'basetime': basetime,
        'usedcol': [],
        'htmls': [],
        'history': []
    }

    # globals for stream(feed)
    gs = {
        'stream': stream,
        'mstr': mstr,
        'acast': caster,
    }

    ei = 0
    drtb = t # debug refresh time base
    to = 0.0
    try:
        while True:
            try:
                streamfeed(gs)
            except KeyboardInterrupt:
                break
            if ei < len(events):
                e = events[ei]
                to = e.timeout
                r = e.check_and_respond(screen)
                if r:
                    tt = now() - t
                    nt = now() - basetime
                    gr['history'].append((e.desc, nt, tt))
                    print(f"Event {e.desc} {tt:.3f}/{to}:")
                    screenprint(screen, gr, e.desc)
                    if isinstance(r, list):
                        subc(r)
                    else:
                        humanlytype(gs, r)
                    ei += 1
                    drtb = t = now()
                    continue
                timeoutcheck(t, to, screen, gr, e.desc)
            else:
                to = 80.0
                timeoutcheck(t, to, screen, gr, "Shutdown")

            if debug_refresh and (now() - drtb) > debug_refresh:
                drtb = now()
                print("Debug Refresh:")
                screenprint(screen, gr)

    except OSError:
        pass

    os.close(mstr)
    caster.close()
    desc = "Shutdown"
    if ei < len(events):
        desc += " (Early)"
    print(f"{desc} {now() - t:.3f}/{to}:")
    screenprint(screen, gr, desc, finalevt=desc)

    if ei < len(events):
        sys.exit(1)

main()
