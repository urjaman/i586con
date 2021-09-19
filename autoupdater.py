#!/usr/bin/env python3
import os
import sys
import urllib.request
import json
import subprocess
from subprocess import DEVNULL, PIPE, STDOUT
from email.message import EmailMessage


# These are slightly... split apart, to make them not attract bots searching for addresses.
emhost =  '\x40' + 'urja' + '.dev'
whoami = 'i586con-BB <kbb' + emhost + '>'
toaddr = 'urja' + emhost
emailproc = ['ssh', 'kbb' + emhost, 'sendmail', '-t']
email_enabled = False

version_file = "br-version"
prev_version_file = "br-version.old"

def htmlize(s):
    escapes = {
        '&': '&amp;',
        '>': '&gt;',
        '<': '&lt;'
    }
    prefix = '<html><head></head><body><pre>\n'
    suffix = '</pre></body></html>\n'
    for k in escapes:
        s = s.replace(k, escapes[k])
    return prefix + s + suffix

def html_link(link):
    prefix = '<html><head></head><body><a href="'
    mid = '">'
    suffix = '</a></body></html>'
    return prefix + link + mid + link + suffix

def mail(subj, logfn = None, log = None, link=None):
    if logfn:
        with open(logfn) as f:
            log = f.read()

    msg = EmailMessage()
    msg['Subject'] = '[i586con-BB] ' + subj
    msg['From'] = whoami
    msg['To'] = toaddr

    if log:
        snip_threshold = 100
        if log.count('\n') > snip_threshold:
            log = log.splitlines()
            log = log[-snip_threshold:]
            log = '<snip>\n' + '\n'.join(log) + '\n'

        msg.set_content(log)
        msg.add_alternative(htmlize(log), subtype='html')
    elif link:
        msg.set_content(link)
        msg.add_alternative(html_link(link), subtype='html')
    else:
        msg.set_content("\n")

    #print(msg)
    if email_enabled:
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
    search = b'Latest long term support release:'

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


def publish(fullv, image):
    rt = os.path.realpath('.')
    cmds = [
        [ 'git', 'push' ]
    ]
    isoname = 'i586con-' + fullv + '.iso'
    targetpath = 'i586con_autobuilds/'
    if email_enabled: # Misnomer but ... maintainer mode-ish
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
    mail(f"i586con {fullv} built", link='https://urja.dev/' + targetpath + isoname)

rebuild = False
if len(sys.argv) >= 2:
    for e in sys.argv[1:]:
        if e == '--email':
            email_enabled = True
        elif e == '--rebuild':
            rebuild = True
        else:
            print(f"usage: {sys.argv[0]} [--email|--rebuild]")
            sys.exit(1)

if not rebuild:
    # Update
    with open(version_file) as f:
        prev_brversion = f.read().strip()
    full_prev_version = version()

    cur_brversion = latest_lts()

    # Run a pull in case I've updated stuff elsewhere in the meantime
    sub(['git','pull'])

    if cur_brversion != prev_brversion:
        os.rename(version_file, prev_version_file)
        with open(version_file, 'w') as f:
            f.write(cur_brversion + '\n')
        gitcommit(cur_brversion)

    full_version = version()

    if full_version == full_prev_version and not os.path.exists(prev_version_file):
        print("Nothing to update.")
        sys.exit(0)
else:
    # Rebuild
    with open(version_file) as f:
        cur_brversion = f.read().strip()

    full_version = version()


fextract_ok_f = '.fextract-ok-' + cur_brversion
brpath = "buildroot-" + cur_brversion
buildpath = "Build-" + full_version

if rebuild:
    subc(['rm', '-rf', brpath, buildpath, fextract_ok_f])
else:
    if full_version != full_prev_version and cur_brversion == prev_brversion:
        if os.path.exists(brpath):
            subc(['rm','-rf', brpath, fextract_ok_f])

if not os.path.exists(fextract_ok_f):
    run_fextract(cur_brversion)

imagefile = build(brpath, buildpath, full_version)
publish(full_version, imagefile)
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
