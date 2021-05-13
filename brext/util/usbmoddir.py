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
        if '-' in mn:
            modules[mn.replace('-','_')] = (module, deps.strip())

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

def find_common(*lists):
   # Convert first list to a set and intersect
   # with the rest of the lists.
   return list(set(lists[0]).intersection(*lists))

hcilist = ( ('ehci_pci',1), ('ohci_pci',2), ('uhci_hcd',4) )

for hci in hcilist:
    aliasfn = tgtdir + os.path.sep + "alias-" + str(hci[1])
    with open(aliasfn, "w") as af:
        af.write('\n'.join(aliases[hci[0]]) + '\n')

loadeds = []
for i in range(1,8):
    lded = []
    loadfn = tgtdir + os.path.sep + "load-" + str(i)
    script = open(loadfn, "w")
    for hci in hcilist:
        if i & hci[1]:
            insmod(hci[0], script, lded)
    script.close()
    subprocess.run(['chmod', '+x', loadfn])
    loadeds.append(lded)

common_loaded = find_common(*loadeds)
print("common_loaded:")
print(common_loaded)
loadfn = tgtdir + os.path.sep + "load-common"
script = open(loadfn, "w")
for mod in sys.argv[3:]:
    insmod(mod, script, common_loaded)

script.close()
subprocess.run(['chmod', '+x', loadfn])

print("usbmoddir done.")

