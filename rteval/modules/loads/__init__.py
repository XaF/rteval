#
#   Copyright 2009,2010   Clark Williams <williams@redhat.com>
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

import sys
import os
import os.path
import time
import subprocess
import threading
import libxml2
from Log import Log

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

    def genxml(self, x):
        pass

    def open_logfile(self, name):
        return os.open(os.path.join(self.reportdir, "logs", name), os.O_CREAT|os.O_WRONLY)


class CommandLineLoad(LoadThread):
    def __init__(self, name="<unnamed>", params={}, logger=None):
        LoadThread.__init__(self, name, params, logger)


    def MakeReport(self):
        rep_n = libxml2.newNode("command_line")
        rep_n.newProp("name", self.name)
        rep_n.newProp("run", self.jobs and '1' or '0')

        if self.jobs:
            rep_n.newProp("job_instances", str(self.jobs))
            rep_n.addContent(" ".join(self.args))

        return rep_n


class LoadModules(object):
    """Module container for LoadThread based modules"""

    def __init__(self, config, logger):
        self.__module_root = "modules.loads"
        self.__module_config = "loads"
        self.__report_tag = "loads"
        self.__loadavg_accum = 0.0
        self.__loadavg_samples = 0

        self.__cfg = config
        self.__logger = logger
        self.__modules = {}
        self.__loadlog = []


    def Setup(self, modparams):
        modcfg = self.__cfg.GetSection(self.__module_config)
        for m in modcfg:
            # hope to eventually have different kinds but module is only on
            # for now (jcw)
            if m[1].lower() == 'module':
                self.__logger.log(Log.INFO, "importing module %s" % m[0])
                self.__cfg.AppendConfig(m[0], modparams)
                mod = __import__("%s.%s" % (self.__module_root, m[0]),
                                 fromlist=self.__module_root)
                self.__modules[m[0]] = { "module": mod,
                                         "object": mod.create(self.__cfg.GetSection(m[0])) }


    def MakeReport(self):
        rep_n = libxml2.newNode(self.__report_tag)
        rep_n.newProp("load_average", str(self.GetLoadAvg()))

        for (modname, mod) in self.__modules.iteritems():
            self.__logger.log(Log.DEBUG, "Getting report from %s" % modname)
            modrep_n = mod["object"].MakeReport()
            rep_n.addChild(modrep_n)

        return rep_n


    def ModulesLoaded(self):
        return len(self.__modules)


    def Start(self):
        if len(self.__modules) == 0:
            raise RuntimeError("No loads configured")

        self.__logger.log(Log.INFO, "Starting loads")
        for (modname, mod) in self.__modules.iteritems():
            mod["object"].start()
            self.__logger.log(Log.DEBUG, "\t - %s started" % modname)

        self.__logger.log(Log.DEBUG, "Waiting for all loads to be ready")

        busy = True
        while not busy:
            busy = False
            for (modname, mod) in self.__modules.iteritems():
                if not mod["object"].isAlive():
                    raise RuntimeError("%s died" % modname)
                if not mod["object"].isReady():
                    busy = True
                    self.__logger.log(Log.DEBUG, "Waiting for %s" % modname)

            if busy:
                time.sleep(1)


    def Unleash(self):
        # turn loose the loads
        nthreads = 0
        self.__logger.log(Log.INFO, "sending start event to all loads")
        for (modname, mod) in self.__modules.iteritems():
            mod["object"].startevent.set()
            nthreads += 1

        return nthreads


    def Stop(self):
        if len(self.__modules) == 0:
            raise RuntimeError("No loads configured")

        self.__logger.log(Log.INFO, "Stopping loads")
        for (modname, mod) in self.__modules.iteritems():
            mod["object"].stopevent.set()
            self.__logger.log(Log.DEBUG, "\t - Stopping %s" % modname)
            mod["object"].join(2.0)


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

