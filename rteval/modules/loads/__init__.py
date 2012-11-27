#
#   Copyright 2009 - 2012   Clark Williams <williams@redhat.com>
#   Copyright 2012          David Sommerseth <davids@redhat.com>
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

import os
import time
import threading
import libxml2
from Log import Log
from modules import RtEvalModules

class LoadThread(threading.Thread):
    def __init__(self, name="<unnamed>", params={}, logger=None):
        threading.Thread.__init__(self)
        self.__logger = logger
        self.name = name
        self.builddir = params.setdefault('builddir', os.path.abspath("../build"))	# abs path to top dir
        self.srcdir = params.setdefault('srcdir', os.path.abspath("../loadsource"))	# abs path to src dir
        self.num_cpus = params.setdefault('numcores', 1)
        self.debugging = params.setdefault('debugging', False)
        self.source = params.setdefault('source', None)
        self.reportdir = params.setdefault('reportdir', os.getcwd())
        self.logging = params.setdefault('logging', False)
        self.memsize = params.setdefault('memsize', (0, 'GB'))
        self.params = params
        self.ready = False
        self.mydir = None
        self.startevent = threading.Event()
        self.stopevent = threading.Event()
        self.jobs = 0
        self.args = None

        if not os.path.exists(self.builddir):
            os.makedirs(self.builddir)

    def _log(self, logtype, msg):
        if self.__logger:
            self.__logger.log(logtype, msg)

    def debug(self, str):
        if self.debugging: print "%s: %s" % (self.name, str)

    def isReady(self):
        return self.ready

    def shouldStop(self):
        return self.stopevent.isSet()

    def shouldStart(self):
        return self.startevent.isSet()

    def setup(self, builddir, tarball):
        pass

    def build(self, builddir):
        pass

    def runload(self, rundir):
        pass

    def run(self):
        if self.shouldStop():
            return
        self.setup()
        if self.shouldStop():
            return
        self.build()
        while True:
            if self.shouldStop():
                return
            self.startevent.wait(1.0)
            if self.shouldStart():
                break
        self.runload()

    def report(self):
        pass

    def open_logfile(self, name):
        return os.open(os.path.join(self.reportdir, "logs", name), os.O_CREAT|os.O_WRONLY)


class CommandLineLoad(LoadThread):
    def __init__(self, name="<unnamed>", params={}, logger=None):
        LoadThread.__init__(self, name, params, logger)


    def MakeReport(self):
        rep_n = libxml2.newNode("command_line")
        rep_n.newProp("name", self.name)
        rep_n.newProp("run", (self.jobs and self.args) and '1' or '0')

        if self.jobs:
            rep_n.newProp("job_instances", str(self.jobs))
            if self.args:
                rep_n.addContent(" ".join(self.args))

        return rep_n


class LoadModules(RtEvalModules):
    """Module container for LoadThread based modules"""

    def __init__(self, config, logger):
        self._module_type = "load"
        self._module_root = "modules.loads"
        self._module_config = "loads"
        self._report_tag = "loads"
        self.__loadavg_accum = 0.0
        self.__loadavg_samples = 0
        RtEvalModules.__init__(self, config, logger)


    def MakeReport(self):
        rep_n = RtEvalModules.MakeReport(self)
        rep_n.newProp("load_average", str(self.GetLoadAvg()))

        return rep_n


    def SaveLoadAvg(self):
        # open the loadavg /proc entry
        p = open("/proc/loadavg")
        load = float(p.readline().split()[0])
        p.close()
        self.__loadavg_accum += load
        self.__loadavg_samples += 1


    def GetLoadAvg(self):
        if self.__loadavg_samples == 0:
            self.SaveLoadAvg()
        return float(self.__loadavg_accum / self.__loadavg_samples)

