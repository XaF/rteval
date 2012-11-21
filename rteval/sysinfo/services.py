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

import sys, subprocess, os, glob, fnmatch
from sysinfo.tools import getcmdpath
from Log import Log


class SystemServices(object):
    def __init__(self, logger=None):
        self.__logger = logger


    def __log(self, logtype, msg):
        if self.__logger:
            self.__logger.log(logtype, msg)


    def __get_services_sysvinit(self):
        reject = ('functions', 'halt', 'killall', 'single', 'linuxconf', 'kudzu',
                  'skeleton', 'README', '*.dpkg-dist', '*.dpkg-old', 'rc', 'rcS',
                  'single', 'reboot', 'bootclean.sh')
        for sdir in ('/etc/init.d', '/etc/rc.d/init.d'):
            if os.path.isdir(sdir):
                servicesdir = sdir
                break
        if not servicesdir:
            raise RuntimeError, "No services dir (init.d) found on your system"
        self.__log(Log.DEBUG, "Services located in %s, going through each service file to check status" % servicesdir)
        ret_services = {}
        for service in glob.glob(os.path.join(servicesdir, '*')):
            servicename = os.path.basename(service)
            if not [1 for p in reject if fnmatch.fnmatch(servicename, p)] and os.access(service, os.X_OK):
                cmd = '%s -qs "\(^\|\W\)status)" %s' % (getcmdpath('grep'), service)
                c = subprocess.Popen(cmd, shell=True)
                c.wait()
                if c.returncode == 0:
                    cmd = ['env', '-i', 'LANG="%s"' % os.environ['LANG'], 'PATH="%s"' % os.environ['PATH'], 'TERM="%s"' % os.environ['TERM'], service, 'status']
                    c = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    c.wait()
                    if c.returncode == 0 and (c.stdout.read() or c.stderr.read()):
                        ret_services[servicename] = 'running'
                    else:
                        ret_services[servicename] = 'not running'
                else:
                    ret_services[servicename] = 'unknown'
        return ret_services


    def __get_services_systemd(self):
        ret_services = {}
        cmd = '%s list-unit-files -t service --no-legend' % getcmdpath('systemctl')
        self.__log(Log.DEBUG, "cmd: %s" % cmd)
        c = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for p in c.stdout:
            # p are lines like "servicename.service status"
            v = p.strip().split()
            ret_services[v[0].split('.')[0]] = v[1]
        return ret_services


    def services_get(self):
        cmd = [getcmdpath('ps'), '-ocomm=',  '1']
        c = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.init = c.stdout.read().strip()
        if self.init == 'systemd':
            self.__log(Log.DEBUG, "Using systemd to get services status")
            return self.__get_services_systemd()
        elif self.init == 'init':
            self.init = 'sysvinit'
            self.__log(Log.DEBUG, "Using sysvinit to get services status")
            return self.__get_services_sysvinit()
        else:
            raise RuntimeError, "Unknown init system (%s)" % self.init
        return {}



def unit_test(rootdir):
    from pprint import pprint

    try:
        syssrv = SystemServices()
        pprint(syssrv.get_services())
        return 0
    except Exception, e:
        print "** EXCEPTION: %s" % str(e)
        return 1


if __name__ == '__main__':
    sys.exit(unit_test(None))

