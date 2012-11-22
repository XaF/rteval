# -*- coding: utf-8 -*-
#!/usr/bin/python -tt
#
#   Copyright 2009-2012   Clark Williams <williams@redhat.com>
#   Copyright 2012        David Sommerseth <davids@redhat.com>
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

import os, shutil, subprocess
from glob import glob
from Log import Log

class OSInfo(object):
    def __init__(self, logger):
        self.__logger = logger


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


def unit_test(rootdir):
    import sys

    try:
        log = Log()
        log.SetLogVerbosity(Log.DEBUG|Log.INFO)
        osi = OSInfo(logger=log)
        print "Base OS: %s" % osi.get_base_os()

        print "Testing OSInfo::copy_dmesg('/tmp'): ",
        osi.copy_dmesg('/tmp')
        if os.path.isfile("/tmp/dmesg"):
            md5orig = subprocess.check_output(("md5sum","/var/log/dmesg"))
            md5copy = subprocess.check_output(("md5sum","/tmp/dmesg"))
            if md5orig.split(" ")[0] == md5copy.split(" ")[0]:
                print "PASS"
            else:
                print "FAIL (md5sum)"
            os.unlink("/tmp/dmesg")
        else:
            print "FAIL (copy failed)"

        print "Running sysreport/sosreport with output to current dir"
        osi.run_sysreport(".")

    except Exception, e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        print "** EXCEPTION %s", str(e)
        return 1

if __name__ == '__main__':
    unit_test(None)
