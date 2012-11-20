#!/usr/bin/python -tt
#
#   Copyright 2009-2012   Clark Williams <williams@redhat.com>
#   Copyright 2009-2012   David Sommerseth <davids@redhat.com>
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
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
#   For the avoidance of doubt the "preferred form" of this code is one which
#   is in an open unpatent encumbered format. Where cryptographic key signing
#   forms part of the process of creating an executable the information
#   including keys needed to generate an equivalently functional executable
#   are deemed to be part of the source code.
#

import ethtool, os, shutil
from Log import Log
from glob import glob
from kernel import KernelInfo
from services import SystemServices
from cputopology import CPUtopology


class SystemInfo(object):
    def __init__(self, config, logger=None):
        self.__logger = logger
        self.__kernel = KernelInfo(logger=logger)
        self.__services = SystemServices(logger=logger)


    def __log(self, logtype, msg):
        if self.__logger:
            self.__logger.log(logtype, msg)


    def get_num_nodes(self):
        nodes = len(glob('/sys/devices/system/node/node*'))
        return nodes


    def get_memory_size(self):
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
            if size < 1024:
                break
            size = float(size) / 1024
        return (size, unit)


    def get_base_os(self):
        '''record what userspace we're running on'''
        distro = "unknown"
        for f in ('redhat-release', 'fedora-release'):
            p = os.path.join('/etc', f)
            if os.path.exists(p):
                f = open(p, 'r')
                distro = f.readline().strip()
                f.close()
                break
        return distro


    def copy_dmesg(self, repdir):
        dpath = "/var/log/dmesg"
        if not os.path.exists(dpath):
            print "dmesg file not found at %s" % dpath
            return
        shutil.copyfile(dpath, os.path.join(repdir, "dmesg"))


    def get_services(self):
        # Temporary wrapper
        return self.__services.get_services()


    def get_kthreads(self):
        # Temporary wrapper
        return self.__kernel.get_kthreads()


    def get_modules(self):
        # Temporary wrapper
        return self.__kernel.get_modules()


    def get_clocksources(self):
        # Temporary wrapper
        return self.__kernel.get_clocksources()


    def get_cpu_topology(self):
        ''' figure out how many processors we have available'''

        topology = CPUtopology()
        topology.parse()

        numcores = topology.getCPUcores(True)
        self.__logger.log(Log.DEBUG, "counted %d cores (%d online) and %d sockets" %
                   (topology.getCPUcores(False), numcores,
                    topology.getCPUsockets()))
        return (numcores, topology.getXMLdata())



if __name__ == "__main__":
    l = Log()
    l.SetLogVerbosity(Log.INFO|Log.DEBUG)
    si = SystemInfo(None, logger=l)

    print "\tRunning on %s" % si.get_base_os()
    print "\tNUMA nodes: %d" % si.get_num_nodes()
    print "\tMemory available: %03.2f %s" % si.get_memory_size()

    print "\tServices: %s" % si.get_services()
    (curr, avail) = si.get_clocksources()
    print "\tCurrent clocksource: %s" % curr
    print "\tAvailable clocksources: %s" % avail
    print "\tModules:"
    for m in si.get_modules():
        print "\t\t%s: %s" % (m['modname'], m['modstate'])
