#!/usr/bin/env python3
import os
import sys
import urllib.request
import urllib.error
import shutil
import subprocess
import time
import datetime
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

def build(v):
    rt = os.path.realpath('.')
    buildroot_dir = os.path.realpath('buildroot-' + v)
    build_dir = os.path.realpath('build-' + v)
    ext_dir = os.path.realpath('brext')
    imagepath = build_dir + '/images/i586con.iso'
    os.makedirs(build_dir, exist_ok=True)
    if os.path.exists(imagepath):
        return imagepath

    os.chdir(build_dir)
    vb = '[' + v + '] '

    cmd = [ 'make', 'BR2_EXTERNAL=' + ext_dir, 'O=' + build_dir, '-C', buildroot_dir ]
    cmds = [
        cmd + ['i586con_defconfig'],
        cmd
        ]

    subtea(cmds, "build-log", vb + "build failed")
    os.chdir(rt)
    return imagepath

def gitup(v):
    cmds = [
        ['git', 'add', version_file ],
        ['git', 'commit', '-m', 'Automatic update to buildroot ' + v ],
        ['git', 'push' ]
    ]
    subtea(cmds, ".gitops-log", "git failed")

def publish(v, image):
    targetpath = 'i586con_autobuilds/i586con-' + v + '.iso'
    cmd = [ "scp", image, "urja.dev:srv/" + targetpath ]
    subtea(cmd, ".scp-log", "scp failed")
    mail("i586con updated to " + v, link='https://urja.dev/' + targetpath)

if len(sys.argv) >= 2:
    if sys.argv[1] == '--email':
        email_enabled = True

with open(version_file) as f:
    prev_version = f.read().strip()

cur_version = latest_lts()

if cur_version == prev_version and not os.path.exists(prev_version_file):
    print("Nothing to update.")
    sys.exit(0)

if cur_version != prev_version:
    os.rename(version_file, prev_version_file)
    with open(version_file, 'w') as f:
        f.write(cur_version + '\n')

if not os.path.exists('.fextract-ok-' + cur_version):
    run_fextract(cur_version)

imagefile = build(cur_version)
gitup(cur_version)
# This is a misnomer now, but ehhhh .... *shrug*
if email_enabled:
    publish(cur_version, imagefile)
os.unlink(prev_version_file)
