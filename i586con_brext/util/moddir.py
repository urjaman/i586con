#!/usr/bin/env python3

import os
import sys
import subprocess

[moddir, mod, tgtdir] = sys.argv[1:]

modules = {}

with open(moddir + "/modules.dep") as deps:
    for dep in deps:
        module, deps = dep.split(':', maxsplit=1)
        dir, fn = os.path.split(module)
        mn, _ = fn.split('.ko', maxsplit=1)
        modules[mn] = (module, deps.strip())

if mod not in modules:
    sys.exit("Module not found")

loadfn = tgtdir + os.path.sep + "load"
loadscript = open(loadfn, "w")
loadscript.write("#!/sh\n")

loaded = []

def doit(mfn, script, tgtdir):
    global loaded
    if mfn in loaded:
        return
    subprocess.run(['cp',moddir + os.path.sep + mfn,tgtdir]).check_returncode()
    loaded.append(mfn)
    dir, fn = os.path.split(mfn)
    script.write(f"insmod {fn}\n")
    
def insmod(mod, script, tgtdir):
    global modules
    if mod == '':
        return
    if mod in loaded:
        return
    mpth, deps  = modules[mod]
    for dfn in reversed(deps.split()):
        doit(dfn, script, tgtdir)
    doit(mpth, script,tgtdir)

insmod(mod, loadscript, tgtdir)
loadscript.close()
subprocess.run(['chmod', '+x', loadfn])
print("Whoopsie, done.")

