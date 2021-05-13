#!/usr/bin/env python3

import os
import sys
import subprocess

[moddir, tgtdir] = sys.argv[1:3]

modules = {}

with open(moddir + "/modules.dep") as deps:
    for dep in deps:
        module, deps = dep.split(':', maxsplit=1)
        dir, fn = os.path.split(module)
        mn, _ = fn.split('.ko', maxsplit=1)
        modules[mn] = (module, deps.strip())

aliases = {}
with open(moddir + "/modules.alias") as alias:
    for al in alias:
        if al[0] == '#':
            continue
        alcmd , alst, modname = al.split()
        if alcmd != 'alias':
            continue
        if modname in aliases:
            aliases[modname].append(alst)
        else:
            aliases[modname] = [alst]

def doit(mfn, script, loaded, ignore=False):
    if mfn in loaded:
        return
    subprocess.run(['cp',moddir + os.path.sep + mfn,tgtdir]).check_returncode()
    loaded.append(mfn)
    dir, fn = os.path.split(mfn)
    if ignore:
        script.write(f"insmod {fn} 2>/dev/null\n")
    else:
        script.write(f"insmod {fn}\n")
    
def insmod(mod, script, loaded = None):
    if loaded is None:
        loaded = []
    if mod in loaded:
        return
    mpth, deps  = modules[mod]
    for dfn in reversed(deps.split()):
        doit(dfn, script, loaded, ignore=True)
    doit(mpth, script, loaded)

modlstfn = tgtdir + os.path.sep + "modules"
modlst = open(modlstfn, "w")

# Do not put in these "drivers" ;)
blacklist = ( 'libata', 'libahci', 'pata_legacy', 'ata_generic', 'pata_isapnp' )

for mod in sys.argv[3:]:
    path, fn = os.path.split(mod)
    mname, _ = fn.split('.ko', maxsplit=1)
    if mname in blacklist:
        continue
    loadfn = tgtdir + os.path.sep + "load-" + mname
    with open(loadfn, "w") as script:
        insmod(mname, script)
    subprocess.run(['chmod', '+x', loadfn])

    aliasfn = tgtdir + os.path.sep + "alias-" + mname
    with open(aliasfn, "w") as af:
        af.write('\n'.join(aliases[mname]) + '\n')
    modlst.write(mname + '\n')

print("atamoddir done.")

