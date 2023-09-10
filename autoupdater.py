#!/usr/bin/env python3
import os
import sys
import urllib.request
import json
import subprocess
from subprocess import DEVNULL, PIPE, STDOUT
from email.message import EmailMessage


# These are slightly... split apart, to make them not attract bots searching for addresses.
emhost =  '\x40' + 'tea.urja' + '.dev'
whoami = 'i586con-BB <kbb' + emhost + '>'
toaddr = 'urja' + emhost
emailproc = ['ssh', 'kbb' + emhost, 'sendmail', '-t']

version_file = "br-version"
prev_version_file = "br-version.old"

webhost = "https://urja.dev/"
webpath = 'i586con_autobuilds/'

s = {
    'email': False,
    'cont': False,
    'rebuild': False,
}


def html_esc(s):
    escapes = {
        '&': '&amp;',
        '>': '&gt;',
        '<': '&lt;',
        '"': '&quot;'
    }
    for k in escapes:
        s = s.replace(k, escapes[k])
    return s

def html(body):
    prefix = '<html><head></head><body>'
    suffix = '</pre></body></html>\n'
    return prefix + body + suffix

def pre(s):
    return '<pre>' + html_esc(s) + '</pre>'

def htmlize(s):
    return html(pre(s))

def html_link(link, text=None):
    if text is None:
        text = link
    prefix = '<a href="'
    mid = '">'
    suffix = '</a>'
    lnk = prefix + html_esc(link) + mid + html_esc(text) + suffix
    return lnk


def mail(subj, logfn = None, log = None, texthtml=None):
    if logfn:
        with open(logfn) as f:
            log = f.read()

    msg = EmailMessage()
    msg['Subject'] = '[i586con-BB] ' + subj
    msg['From'] = whoami
    msg['To'] = toaddr

    if texthtml:
        msg.set_content(texthtml[0])
        msg.add_alternative(texthtml[1], subtype='html')
    elif log:
        snip_threshold = 100
        if log.count('\n') > snip_threshold:
            log = log.splitlines()
            log = log[-snip_threshold:]
            log = '<snip>\n' + '\n'.join(log) + '\n'

        msg.set_content(log)
        msg.add_alternative(htmlize(log), subtype='html')
    else:
        msg.set_content("\n")

    #print(msg)
    if s['email']:
        subprocess.run(emailproc, input=msg.as_bytes())

def subc(*args, **kwargs):
    c = subprocess.run(*args, **kwargs)
    if c.returncode != 0:
        print("subprocess failed: ", args)
        print("code:", c.returncode)
        sys.exit(1)
    return c.stdout

def sub(*args, **kwargs):
    c = subprocess.run(*args, **kwargs)
    if c.returncode != 0:
        return False
    if c.stdout:
        return c.stdout
    return True

def subtea(cmds, log, error_subj):
    if not isinstance(cmds[0], list):
        cmds = [cmds]
    teecmd = ["tee", log ]
    for cmd in cmds:
        proc = subprocess.Popen(cmd, stdin=DEVNULL, stderr=STDOUT, stdout=PIPE)
        tee = subprocess.Popen(teecmd, stdin=proc.stdout)
        r1 = proc.wait()
        tee.wait()
        if r1:
            mail(error_subj, log)
            sys.exit(1)
        teecmd = ["tee", "-a", log ]


def latest_lts():
    # Gotta love this for an "API"
    url = "https://buildroot.org/download.html"
    r = urllib.request.urlopen(url, timeout=30)
    lines = r.readlines()
    search = b' long term support release:'

    for L in lines:
        if search in L:
            _,verpart = L.split(search,maxsplit=1)
            btag = b'<b>'
            ebtag = b'</b>'
            if btag not in verpart:
                sys.exit("btag not in verpart - vedä siitä sit")
            _,verstart = verpart.split(btag,maxsplit=1)
            if ebtag not in verstart:
                sys.exit("ebtag not in verstart")
            version,_ = verstart.split(ebtag,maxsplit=1)
            return version.decode()
    sys.exit("Couldnt find what i was looking for in " + url)

def run_fextract(v):
    log = ".fextract-log"
    cmd = [ "./fextract.sh", "--verify" ]
    subtea(cmd, log, '[' + v + '] problem fetching/patching buildroot')

def build(brpath, buildpath, fullv):
    rt = os.path.realpath('.')
    buildroot_dir = os.path.realpath(brpath)
    build_dir = os.path.realpath(buildpath)
    ext_dir = os.path.realpath('brext')
    imagepath = build_dir + '/images/i586con.iso'
    os.makedirs(build_dir, exist_ok=True)
    if os.path.exists(imagepath):
        return imagepath

    os.chdir(build_dir)
    vb = '[' + fullv + '] '

    cmd = [ 'make', 'BR2_EXTERNAL=' + ext_dir, 'O=' + build_dir, '-C', buildroot_dir ]
    cmds = [
        cmd + ['i586con_defconfig'],
        cmd
        ]

    subtea(cmds, "build-log", vb + "build failed")
    os.chdir(rt)
    return imagepath

def gitcommit(v):
    cmds = [
        ['git', 'add', version_file ],
        ['git', 'commit', '-m', 'Automatic update to buildroot ' + v ],
    ]
    subtea(cmds, ".gitops-log", "git failed")

def version():
    return subc(["./version.sh"], stdout=PIPE).decode().strip()


def testsuite(fullv, image):
    testweb_path = f"testresults/{fullv}"
    test_path = f"releases/testresults"
    test_path_full = test_path + '/' + fullv
    os.makedirs(test_path_full, exist_ok=True)
    logfn = test_path_full + "/cursed_output.txt"

    cmd = [ "./cursedtester.py", image, test_path, fullv ]
    print("Running the test suite ", cmd)

    with open(logfn, "w") as lf:
        r = sub(cmd, stdin=DEVNULL, stderr=STDOUT, stdout=lf)

    # Send the reports to the webserver first and foremost
    subc([ "scp", "-r", test_path_full, "urja.dev:srv/" + webpath + "testresults" ])

    # Collect all summaries and HTML names
    summaries = []
    htmls = []
    pretext = [[]]
    insum = False
    with open(logfn) as lf:
        for L in lf:
            L = L.rstrip("\n")
            if insum:
                if L.startswith('=== HTML: '):
                    insum = False
                    _,h = L.strip().split(sep=': ',maxsplit=1)
                    htmls.append(h)
                else:
                    summaries[-1].append(L)
            else:
                if L.startswith('=== SUMMARY '):
                    summaries.append([L])
                    pretext.append([])
                    insum = True
                else:
                    pretext[-1].append(L)

    castpath = webhost + "castplayer/?u=" + fullv + "/"

    if r:
        tl = []
        hl = [ "<pre>" ]
        i = 0
        while i < len(summaries):
            s = summaries[i]
            tl.append(s[0])

            testname = htmls[i][:-5]
            linkline = html_link(webhost + webpath + testweb_path + '/' + htmls[i], s[0])
            linkline += ' '
            linkline += html_link(castpath + testname, "== AsciiCast ==")
            hl.append(linkline)

            for e in s[1:]:
                tl.append(e)
                hl.append(html_esc(e))
            i += 1
        hl.append("</pre>")
        return ('\n'.join(tl) + '\n', '\n'.join(hl) + '\n')
    else:
        if not summaries:
            tx = '\n'.join(pretext[0]) + '\n'
            ht = htmlize(text)
        else:
            i = len(summaries) - 1
            tl = pretext[i] + summaries[i]
            tx = '\n'.join(tl) + '\n'
            with open(test_path + '/' + htmls[i]) as hf:
                ht = hf.read()
        mail(f"[{fullv}] testsuite failure {htmls[i][:-5]}", texthtml=(tx, ht))
        sys.exit(1)


def publish(fullv, image, testsums):
    rt = os.path.realpath('.')
    cmds = [
        [ 'git', 'push' ]
    ]
    isoname = 'i586con-' + fullv + '.iso'
    targetpath = webpath
    if s['email']: # Misnomer but ... maintainer mode-ish
        reldir = os.path.realpath('releases')
        os.makedirs(reldir, exist_ok=True)
        os.chdir(reldir)

        info = { 'filename': isoname, 'version': fullv }
        jsf = "latest.json"
        jsfasc = jsf + ".asc"
        jsfnew = jsfasc + ".new"
        with open(jsf,"w") as f:
            json.dump(info,f)
        cmds.append([ "cp", image, isoname ])
        gpg = [ "gpg", "-u", "urja+i586con\x40urja.dev" ]
        cmds.append( gpg + [ "-a", "-b", isoname ])
        cmds.append( gpg + [ "--clear-sign", jsf ])
        cmds.append([ "mv", jsfasc, jsfnew ])
        cmds.append([ "scp", isoname, isoname + ".asc", jsfnew, "urja.dev:srv/" + targetpath ])
        cmds.append([ "ssh","urja.dev","cd", 'srv/' + targetpath, "&&", "mv", jsfnew, jsfasc ])
        cmds.append([ "rm", "-f", jsf, jsfnew ]) # cleanup
    subtea(cmds, rt + "/.publish-log", "publish failed")
    os.chdir(rt)

    link = webhost + webpath + isoname
    tx = link + '\n\n' + testsums[0]
    ht = html(html_link(link) + '<p>\n' + testsums[1])
    mail(f"[{fullv}] success", texthtml=(tx,ht))


updatemode = True
if len(sys.argv) >= 2:
    for e in sys.argv[1:]:
        if e == '--email':
            s['email'] = True
        elif e == '--rebuild':
            s['rebuild'] = True
            updatemode = False
        elif e == '--continue':
            s['cont'] = True
            updatemode = False
        else:
            print(f"usage: {sys.argv[0]} [--email|--rebuild|--continue]")
            sys.exit(1)

rb_once_f = ".rebuild-once"
try:
    with open(rb_once_f) as f:
        rebuild_once = f.read().strip()
    if not rebuild_once:
        rebuild_once = "Unspecified reason"
    os.unlink(rb_once_f)
except Exception:
    rebuild_once = False


if updatemode:
    # Update
    with open(version_file) as f:
        prev_brversion = f.read().strip()
    full_prev_version = version()

    cur_brversion = latest_lts()

    # Run a pull in case I've updated stuff elsewhere in the meantime
    sub(['git','pull','--rebase'])

    if cur_brversion != prev_brversion:
        os.rename(version_file, prev_version_file)
        with open(version_file, 'w') as f:
            f.write(cur_brversion + '\n')
        gitcommit(cur_brversion)

    full_version = version()

    if full_version == full_prev_version and not os.path.exists(prev_version_file):
        if rebuild_once:
            s['rebuild'] = True
            print(f"Rebuilding for '{rebuild_once}'")
        else:
            print("Nothing to update.")
            sys.exit(0)
else:
    # Rebuild / Continue
    with open(version_file) as f:
        cur_brversion = f.read().strip()

    full_version = version()


fextract_ok_f = '.fextract-ok-' + cur_brversion
brpath = "buildroot-" + cur_brversion
buildpath = "Build-" + full_version

if s['rebuild']:
    subc(['rm', '-rf', brpath, buildpath, fextract_ok_f])
elif updatemode:
    if full_version != full_prev_version and cur_brversion == prev_brversion:
        if os.path.exists(brpath):
            subc(['rm','-rf', brpath, fextract_ok_f])

if not os.path.exists(fextract_ok_f):
    run_fextract(cur_brversion)

imagefile = build(brpath, buildpath, full_version)
testsums = testsuite(full_version, imagefile)
publish(full_version, imagefile, testsums)
try:
    os.unlink(prev_version_file)
except Exception:
    pass

# Cleanup processes (these failing is safe-ish, no need to panicmail :P)

# Clean out the oldest builds & buildroots
build_count = 2
build_list = [ ]
rmlist = []
with os.scandir('.') as entries:
    for entry in entries:
        # Include the "2" from the year number so that we dont accidentally
        # wipe out stuff if you name it buildroot-things-that-i-like or whatever
        if entry.name.startswith("buildroot-2"):
            if entry.name.startswith("buildroot-" + cur_brversion):
                continue
            rmlist.append(entry.path)

        if entry.name.startswith("Build-"):
            build_list.append([entry.stat().st_mtime, entry.path])


build_list.sort(reverse=True, key=lambda e: e[0]) # sort by mtime
#print(len(build_list))
#print(build_list)
for e in build_list[build_count:]:
        rmlist.append(e[1])

if rmlist:
    print("Removing these:")
    print(rmlist)
    sub(["rm", "-rf" ] + rmlist)
