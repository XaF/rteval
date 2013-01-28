# -*- coding: utf-8 -*-
#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2012 - 2013   David Sommerseth <davids@redhat.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#   For the avoidance of doubt the "preferred form" of this code is one which
#   is in an open unpatent encumbered format. Where cryptographic key signing
#   forms part of the process of creating an executable the information
#   including keys needed to generate an equivalently functional executable
#   are deemed to be part of the source code.
#

import libxml2
from glob import glob

class MemoryInfo(object):
    numa_nodes = None

    def __init__(self):
        pass


    def mem_get_numa_nodes(self):
        if self.numa_nodes is None:
            self.numa_nodes = len(glob('/sys/devices/system/node/node*'))
        return self.numa_nodes


    def mem_get_size(self):
        '''find out how much memory is installed'''
        f = open('/proc/meminfo')
        rawsize = 0
        for l in f:
            if l.startswith('MemTotal:'):
                parts = l.split()
                if parts[2].lower() != 'kb':
                    raise RuntimeError, "Units changed from kB! (%s)" % parts[2]
                rawsize = int(parts[1])
                f.close()
                break
        if rawsize == 0:
            raise RuntimeError, "can't find memtotal in /proc/meminfo!"

        # Get a more readable result
        # Note that this depends on  /proc/meminfo starting in Kb
        units = ('KB', 'MB','GB','TB')
        size = rawsize
        for unit in units:
            if size < (1024*1024):
                break
            size = float(size) / 1024
        return (size, unit)


    def MakeReport(self):
        rep_n = libxml2.newNode("Memory")

        numa_n = libxml2.newNode("numa_nodes")
        numa_n.addContent(str(self.mem_get_numa_nodes()))
        rep_n.addChild(numa_n)

        memsize = self.mem_get_size()
        mem_n = libxml2.newNode("memory_size")
        mem_n.addContent("%.3f" % memsize[0])
        mem_n.newProp("unit", memsize[1])
        rep_n.addChild(mem_n)

        return rep_n



def unit_test(rootdir):
    import sys
    try:
        mi = MemoryInfo()
        print "Numa nodes: %i" % mi.mem_get_numa_nodes()
        print "Memory: %i %s" % mi.mem_get_size()
    except Exception, e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        print "** EXCEPTION %s", str(e)
        return 1

if __name__ == '__main__':
    unit_test(None)
