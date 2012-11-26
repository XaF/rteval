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

import sys, libxml2
from Log import Log
from glob import glob
from kernel import KernelInfo
from services import SystemServices
from cputopology import CPUtopology
from memory import MemoryInfo
from osinfo import OSInfo
from network import NetworkInfo
import dmi


class SystemInfo(KernelInfo, SystemServices, dmi.DMIinfo, CPUtopology, MemoryInfo, OSInfo, NetworkInfo):
    def __init__(self, config, logger=None):
        self.__logger = logger
        KernelInfo.__init__(self, logger=logger)
        SystemServices.__init__(self, logger=logger)
        dmi.DMIinfo.__init__(self, config, logger=logger)
        CPUtopology.__init__(self)
        OSInfo.__init__(self, logger=logger)

        # Parse initial DMI decoding errors
        dmi.ProcessWarnings()

        # Parse CPU info
        CPUtopology._parse(self)


    def MakeReport(self):
        report_n = libxml2.newNode("SystemInfo");
        report_n.newProp("version", "1.0")

        # Populate the report
        report_n.addChild(OSInfo.MakeReport(self))
        report_n.addChild(KernelInfo.MakeReport(self))
        report_n.addChild(NetworkInfo.MakeReport(self))
        report_n.addChild(SystemServices.MakeReport(self))
        report_n.addChild(CPUtopology.MakeReport(self))
        report_n.addChild(MemoryInfo.MakeReport(self))
        report_n.addChild(dmi.DMIinfo.MakeReport(self))

        return report_n


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

    xml = si.MakeReport()
    xml_d = libxml2.newDoc("1.0")
    xml_d.setRootElement(xml)
    xml_d.saveFormatFileEnc("-", "UTF-8", 1)
