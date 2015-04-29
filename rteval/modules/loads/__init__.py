#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2012 - 2013   David Sommerseth <davids@redhat.com>
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

import os
import time
import threading
import libxml2
from rteval.Log import Log
from rteval.rtevalConfig import rtevalCfgSection
from rteval.modules import RtEvalModules, rtevalModulePrototype
from rteval.sysinfo.tools import chown

class LoadThread(rtevalModulePrototype):
    def __init__(self, name, config, logger=None):

        if name is None or not isinstance(name, str):
            raise TypeError("name attribute is not a string")

        if config and not isinstance(config, rtevalCfgSection):
            raise TypeError("config attribute is not a rtevalCfgSection() object")

        if logger and not isinstance(logger, Log):
            raise TypeError("logger attribute is not a Log() object")

        rtevalModulePrototype.__init__(self, "load", name, logger)
        self.builddir = config.setdefault('builddir', os.path.abspath("../build"))	# abs path to top dir
        self.srcdir = config.setdefault('srcdir', os.path.abspath("../loadsource"))	# abs path to src dir
        self.num_cpus = config.setdefault('numcores', 1)
        self.source = config.setdefault('source', None)
        self.reportdir = config.setdefault('reportdir', os.getcwd())
        self.memsize = config.setdefault('memsize', (0, 'GB'))
        self._logging = config.setdefault('logging', True)
        self._cfg = config
        self.mydir = None
        self.jobs = 0
        self.args = None

        if not os.path.exists(self.builddir):
            os.makedirs(self.builddir)


    def open_logfile(self, name):
        logfilepath = os.path.join(self.reportdir, "logs", name)
        logfile = os.open(logfilepath, os.O_CREAT|os.O_WRONLY)
        chown(logfilepath)
        return logfile


class CommandLineLoad(LoadThread):
    def __init__(self, name, config, logger):
        LoadThread.__init__(self, name, config, logger)


    def MakeReport(self):
        if not (self.jobs and self.args) or self._donotrun:
            return None

        rep_n = libxml2.newNode("command_line")
        rep_n.newProp("name", self._name)

        if self.jobs:
            rep_n.newProp("job_instances", str(self.jobs))
            if self.args:
                rep_n.addContent(" ".join(self.args))

        return rep_n


class LoadModules(RtEvalModules):
    """Module container for LoadThread based modules"""

    def __init__(self, config, logger):
        self._module_type = "load"
        self._module_config = "loads"
        self._report_tag = "loads"
        self.__loadavg_accum = 0.0
        self.__loadavg_samples = 0
        RtEvalModules.__init__(self, config, "modules.loads", logger)
        self.__LoadModules(self._cfg.GetSection(self._module_config))


    def __LoadModules(self, modcfg):
        "Loads and imports all the configured modules"

        for m in modcfg:
            # hope to eventually have different kinds but module is only on
            # for now (jcw)
            if m[1].lower() == 'module':
                self._LoadModule(m[0])


    def Setup(self, modparams):
        if not isinstance(modparams, dict):
            raise TypeError("modparams attribute is not of a dictionary type")

        modcfg = self._cfg.GetSection(self._module_config)
        for m in modcfg:
            # hope to eventually have different kinds but module is only on
            # for now (jcw)
            if m[1].lower() == 'module':
                self._cfg.AppendConfig(m[0], modparams)
                modobj = self._InstantiateModule(m[0], self._cfg.GetSection(m[0]))
                self._RegisterModuleObject(m[0], modobj)


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

