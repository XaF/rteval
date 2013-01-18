# -*- coding: utf-8 -*-
#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2009 - 2013   David Sommerseth <davids@redhat.com>
#   Copyright 2012 - 2013   Raphaël Beamonte <raphael.beamonte@gmail.com>
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

import sys, subprocess, os, glob, fnmatch, libxml2
from rteval.sysinfo.tools import getcmdpath
from rteval.Log import Log


class SystemServices(object):
    def __init__(self, logger=None):
        self.__logger = logger
        self.__init = "unknown"

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
        self.__init = c.stdout.read().strip()
        if self.__init == 'systemd':
            self.__log(Log.DEBUG, "Using systemd to get services status")
            return self.__get_services_systemd()
        elif self.__init == 'init':
            self.__init = 'sysvinit'
            self.__log(Log.DEBUG, "Using sysvinit to get services status")
            return self.__get_services_sysvinit()
        else:
            raise RuntimeError, "Unknown init system (%s)" % self.__init
        return {}


    def MakeReport(self):
        srvs = self.services_get()

        rep_n = libxml2.newNode("Services")
        rep_n.newProp("init", self.__init)

        for s in srvs:
            srv_n = libxml2.newNode("Service")
            srv_n.newProp("state", srvs[s])
            srv_n.addContent(s)
            rep_n.addChild(srv_n)

        return rep_n

def unit_test(rootdir):
    from pprint import pprint

    try:
        syssrv = SystemServices()
        pprint(syssrv.services_get())

        srv_xml = syssrv.MakeReport()
        xml_d = libxml2.newDoc("1.0")
        xml_d.setRootElement(srv_xml)
        xml_d.saveFormatFileEnc("-", "UTF-8", 1)

        return 0
    except Exception, e:
        print "** EXCEPTION: %s" % str(e)
        return 1


if __name__ == '__main__':
    sys.exit(unit_test(None))

