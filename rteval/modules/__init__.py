#
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

from Log import Log
from rtevalConfig import rtevalConfig
import libxml2

class RtEvalModules(object):
    def __init__(self, config, logger):
        if logger and not isinstance(logger, Log):
            raise TypeError("logger attribute is not a Log() object")

        if not isinstance(config, rtevalConfig):
            raise TypeError("config attribue is not an rtevalConfig() object")

        self._cfg = config
        self._logger = logger
        self.__modules = {}


    def Setup(self, modparams):
        if not isinstance(modparams, dict):
            raise TypeError("modparams attribute is not of a dictionary type")

        modcfg = self._cfg.GetSection(self._module_config)
        for m in modcfg:
            # hope to eventually have different kinds but module is only on
            # for now (jcw)
            if m[1].lower() == 'module':
                self._logger.log(Log.INFO, "importing module %s" % m[0])
                self._cfg.AppendConfig(m[0], modparams)
                mod = __import__("%s.%s" % (self._module_root, m[0]),
                                 fromlist=self._module_root)
                modobj = mod.create(self._cfg.GetSection(m[0]), self._logger)
                self.__modules[m[0]] = { "module": mod,
                                         "object": modobj }


    def ModulesLoaded(self):
        return len(self.__modules)


    def Start(self):
        if len(self.__modules) == 0:
            raise RuntimeError("No %s modules configured" % self._module_type)

        self._logger.log(Log.INFO, "Starting %s modules" % self._module_type)
        for (modname, mod) in self.__modules.iteritems():
            mod["object"].start()
            self._logger.log(Log.DEBUG, "\t - %s started" % modname)

        self._logger.log(Log.DEBUG, "Waiting for all %s modules to get ready" % self._module_type)
        busy = True
        while not busy:
            busy = False
            for (modname, mod) in self.__modules.iteritems():
                if not mod["object"].isAlive():
                    raise RuntimeError("%s died" % modname)
                if not mod["object"].isReady():
                    busy = True
                    self._logger.log(Log.DEBUG, "Waiting for %s" % modname)

            if busy:
                time.sleep(1)

        self._logger.log(Log.DEBUG, "All %s modules are ready" % self._module_type)


    def Unleash(self):
        # turn loose the loads
        nthreads = 0
        self._logger.log(Log.INFO, "sending start event to all %s modules" % self._module_type)
        for (modname, mod) in self.__modules.iteritems():
            mod["object"].startevent.set()
            nthreads += 1

        return nthreads


    def Stop(self):
        if len(self.__modules) == 0:
            raise RuntimeError("No %s modules configured" % self._module_type)

        self._logger.log(Log.INFO, "Stopping %s modules" % self._module_type)
        for (modname, mod) in self.__modules.iteritems():
            mod["object"].stopevent.set()
            self._logger.log(Log.DEBUG, "\t - Stopping %s" % modname)
            mod["object"].join(2.0)


    def MakeReport(self):
        rep_n = libxml2.newNode(self._report_tag)

        for (modname, mod) in self.__modules.iteritems():
            self._logger.log(Log.DEBUG, "Getting report from %s" % modname)
            modrep_n = mod["object"].MakeReport()
            rep_n.addChild(modrep_n)

        return rep_n
