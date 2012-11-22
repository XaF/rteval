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

import ethtool, os, shutil, subprocess
import sys
sys.path.append(".")
from Log import Log
from glob import glob
from kernel import KernelInfo
from services import SystemServices
from cputopology import CPUtopology
from memory import MemoryInfo
import dmi


class SystemInfo(KernelInfo, SystemServices, dmi.DMIinfo, CPUtopology, MemoryInfo):
    def __init__(self, config, logger=None):
        self.__logger = logger
        KernelInfo.__init__(self, logger=logger)
        SystemServices.__init__(self, logger=logger)
        dmi.DMIinfo.__init__(self, config, logger=logger)
        CPUtopology.__init__(self)

        # Parse initial DMI decoding errors
        dmi.ProcessWarnings()

        # Parse CPU info
        CPUtopology._parse(self)


    def __log(self, logtype, msg):
        if self.__logger:
            self.__logger.log(logtype, msg)


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


    def run_sysreport(self, repdir):
        if os.path.exists('/usr/sbin/sosreport'):
            exe = '/usr/sbin/sosreport'
        elif os.path.exists('/usr/sbin/sysreport'):
            exe = '/usr/sbin/sysreport'
        else:
            raise RuntimeError, "Can't find sosreport/sysreport"

        self.__logger.log(Log.DEBUG, "report tool: %s" % exe)
        options =  ['-k', 'rpm.rpmva=off',
                    '--name=rteval',
                    '--batch']

        self.__logger.log(Log.INFO, "Generating SOS report")
        self.__logger.log(Log.INFO, "using command %s" % " ".join([exe]+options))
        subprocess.call([exe] + options)
        for s in glob('/tmp/s?sreport-rteval-*'):
            self.__logger.log(Log.DEBUG, "moving %s to %s" % (s, repdir))
            shutil.move(s, repdir)


    def cpu_getXMLdata(self):
        ''' figure out how many processors we have available'''

        self.__logger.log(Log.DEBUG, "counted %d cores (%d online) and %d sockets" %
                   (CPUtopology.cpu_getCores(self, False), CPUtopology.cpu_getCores(self, True),
                    CPUtopology.cpu_getSockets(self)))
        return CPUtopology.cpu_getXMLdata(self)


if __name__ == "__main__":
    from rtevalConfig import rtevalConfig
    l = Log()
    l.SetLogVerbosity(Log.INFO|Log.DEBUG)
    cfg = rtevalConfig(logger=l)
    cfg.Load("../rteval.conf")
    cfg.installdir = "."
    si = SystemInfo(cfg, logger=l)

    print "\tRunning on %s" % si.get_base_os()
    print "\tNUMA nodes: %d" % si.mem_get_numa_nodes()
    print "\tMemory available: %03.2f %s\n" % si.mem_get_size()

    print "\tServices: "
    for (s, r) in si.services_get().items():
        print "\t\t%s: %s" % (s, r)
    (curr, avail) = si.kernel_get_clocksources()

    print "\tCurrent clocksource: %s" % curr
    print "\tAvailable clocksources: %s" % avail
    print "\tModules:"
    for m in si.kernel_get_modules():
        print "\t\t%s: %s" % (m['modname'], m['modstate'])
    print "\tKernel threads:"
    for (p, i) in si.kernel_get_kthreads().items():
        print "\t\t%-30.30s pid: %-5.5s policy: %-7.7s prio: %-3.3s" % (
            i["name"]+":", p, i["policy"], i["priority"]
            )

    print "\n\tCPU topology info - cores: %i  online: %i  sockets: %i" % (
        si.cpu_getCores(False), si.cpu_getCores(True), si.cpu_getSockets()
        )
