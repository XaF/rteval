# -*- coding: utf-8 -*-
#!/usr/bin/python -tt
#
#   Copyright 2009-2012   Clark Williams <williams@redhat.com>
#   Copyright 2009-2012   David Sommerseth <davids@redhat.com>
#   Copyright 2012        Raphaël Beamonte <raphael.beamonte@gmail.com>
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

import sys, subprocess, os
from sysinfo.tools import getcmdpath
from Log import Log


class KernelInfo(object):
    def __init__(self, logger = None):
        self.__logger = logger


    def __log(self, logtype, msg):
        if self.__logger:
            self.__logger.log(logtype, msg)


    def kernel_get_kthreads(self):
        policies = {'FF':'fifo', 'RR':'rrobin', 'TS':'other', '?':'unknown' }
        ret_kthreads = {}
        self.__log(Log.DEBUG, "getting kthread status")
        cmd = '%s -eocommand,pid,policy,rtprio,comm' % getcmdpath('ps')
        self.__log(Log.DEBUG, "cmd: %s" % cmd)
        c = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        for p in c.stdout:
            v = p.strip().split()
            kcmd = v.pop(0)
            try:
                if int(v[0]) > 0 and kcmd.startswith('[') and kcmd.endswith(']'):
                    ret_kthreads[v[0]] = {'policy' : policies[v[1]],
                                          'priority' : v[2], 'name' : v[3] }
            except ValueError:
                pass    # Ignore lines which don't have a number in the first row
        return ret_kthreads


    def kernel_get_modules(self):
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


    def kernel_get_clocksources(self):
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



def unit_test(rootdir):
    try:
        from pprint import pprint
        log = Log()
        log.SetLogVerbosity(Log.INFO|Log.DEBUG)

        ki = KernelInfo(logger=log)
        pprint(ki.kernel_get_kthreads())
        pprint(ki.kernel_get_modules())
        pprint(ki.kernel_get_clocksources())
    except Exception, e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        print "** EXCEPTION %s", str(e)
        return 1

if __name__ == '__main__':
    unit_test(None)

