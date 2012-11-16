#!/usr/bin/python -tt
#
# platform utility functions used by various parts of rteval
#

import sys
import os
import os.path
import subprocess

def get_clocksources():
    '''get the available and curent clocksources for this kernel'''
    path = '/sys/devices/system/clocksource/clocksource0'
    if not os.path.exists(path):
        raise RuntimeError, "Can't find clocksource path in /sys"
    f = open (os.path.join (path, "current_clocksource"))
    current_clocksource = f.readline().strip()
    f = open (os.path.join (path, "available_clocksource"))
    available_clocksource = f.readline().strip()
    f.close()
    return (current_clocksource, available_clocksource)


def get_modules():
    modlist = []
    try:
        fp = open('/proc/modules', 'r')
        line = fp.readline()
        while line:
            mod = line.split()
            modlist.append({"modname": mod[0],
                            "modsize": mod[1],
                            "numusers": mod[2],
                            "usedby": mod[3],
                            "modstate": mod[4]})
            line = fp.readline()
        fp.close()
    except Exception, err:
        raise err
    return modlist


if __name__ == "__main__":
    (curr, avail) = get_clocksources()
    print "\tCurrent clocksource: %s" % curr
    print "\tAvailable clocksources: %s" % avail
    print "\tModules:"
    for m in get_modules():
        print "\t\t%s: %s" % (m['modname'], m['modstate'])
    
