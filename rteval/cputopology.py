# -*- coding: utf-8 -*-
#!/usr/bin/python -tt
#
#   Copyright 2010   David Sommerseth <davids@redhat.com>
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

import sys, os, libxml2

class CPUtopology:
    "Retrieves an overview over the installed CPU cores and the system topology"

    def __init__(self, root="/"):
        self.sysdir = root + "/sys/devices/system/cpu"
        self.__cputop_n = None

    def __read(self, dirname, fname):
        fp = open(os.path.join(self.sysdir, dirname, fname), 'r')
        data = fp.readline()
        if len(data) > 0:
            ret = int(data)
        else:
            ret = 0
        fp.close()
        return ret

    def parse(self):
        "Parses the cpu topology information from /sys/devices/system/cpu/cpu*"

        self.__cputop_n = libxml2.newNode('cpu_topology')
        cpu_cores = 0
        online_cores = 0
        cpu_sockets = 0

        for dirname in os.listdir(self.sysdir):
            # Only parse directories which starts with 'cpu'
            if (dirname.find('cpu', 0) == 0) and os.path.isdir(os.path.join(self.sysdir, dirname)):
                # Make sure we only parse "proper" cpu<integer> directories, and not f.ex. 'cpuidle'
                try:
                    int(dirname[3:])
                except ValueError:
                    continue

                # Parse contents of the cpu dir
                for cpudir in os.listdir(os.path.join(self.sysdir, dirname)):
                    # Check if it is a proper CPU directory which should contain an 'online' file
                    # except on 'cpu0' which cannot be offline'd
                    if (cpudir.find('online',0) == 0) or dirname == 'cpu0':
                        cpu_n = self.__cputop_n.newChild(None,'cpu',None)
                        cpu_n.newProp('name', dirname)
                        online = (dirname == 'cpu0') and 1 or self.__read(dirname, 'online')
                        cpu_n.newProp('online', str(online))
                        cpu_cores += 1

                        # Check if the CPU is online, if it is, grab more info available
                        if online == 1:
                            online_cores += 1
                            cpu_n.newProp('core_id',
                                          str(self.__read(os.path.join(dirname, 'topology'), 'core_id')))
                            phys_pkg_id = self.__read(os.path.join(dirname, 'topology'),
                                                      'physical_package_id')
                            cpu_n.newProp('physical_package_id', str(phys_pkg_id))
                            if phys_pkg_id > (cpu_sockets - 1):
                                cpu_sockets = phys_pkg_id + 1
                        break;

        # Summarise the core counts
        self.__cputop_n.newProp('num_cpu_cores', str(cpu_cores))
        self.__cputop_n.newProp('num_cpu_cores_online', str(online_cores))
        self.__cputop_n.newProp('num_cpu_sockets', str(cpu_sockets))

        return self.__cputop_n

    def getXMLdata(self):
        return self.__cputop_n;


if __name__ == '__main__':
    cputop = CPUtopology()
    n = cputop.parse()

    x = libxml2.newDoc('1.0')
    x.setRootElement(n)
    x.saveFormatFileEnc('-','UTF-8',1)
