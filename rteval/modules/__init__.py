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
import time, libxml2


class ModuleContainer(object):
    """The ModuleContainer keeps an overview over loaded modules and the objects it
will instantiate.  These objects are accessed by iterating the ModuleContainer object."""

    def __init__(self, modules_root, logger):
        """Creates a ModuleContainer object.  modules_root defines the default
directory where the modules will be loaded from.  logger should point to a Log()
object which will be used for logging and will also be given to the instantiated
objects during module import."""
        if logger and not isinstance(logger, Log):
            raise TypeError("logger attribute is not a Log() object")

        self.__modules_root = modules_root
        self.__logger = logger
        self.__modobjects = {}  # Keeps track of instantiated objects
        self.__modsloaded = {}     # Keeps track of imported modules
        self.__iter_list = None


    def __importmod(self, modname, modroot=None):
        """Imports a module and saves references to the imported module.
If the same module is tried imported more times, it will return the module
reference from the first import"""

        if modroot is None:
            modroot = self.__modules_root

        # If this module is already reported return the module,
        # if not (except KeyError:) import it and return the imported module
        try:
            idxname = "%s.%s" % (modroot, modname)
            return self.__modsloaded[idxname]
        except KeyError:
            self.__logger.log(Log.INFO, "importing module %s" % modname)
            mod = __import__("%s.%s" % (modroot, modname),
                             fromlist=modroot)
            self.__modsloaded[idxname] = mod
            return mod


    def ModuleInfo(self, modname, modroot = None):
        """Imports a module and calls the modules' ModuleInfo() function and returns
the information provided by the module"""

        mod = self.__importmod(modname, modroot)
        return mod.ModuleInfo()


    def InstantiateModule(self, modname, modcfg, modroot = None):
        """Imports a module and instantiates an object from the modules create() function.
The instantiated object is returned in this call"""

        mod = self.__importmod(modname, modroot)
        return mod.create(modcfg, self.__logger)


    def RegisterModuleObject(self, modname, modobj):
        """Registers an instantiated module object.  This module object will be
returned when a ModuleContainer object is iterated over"""
        self.__modobjects[modname] = modobj


    def ModulesLoaded(self):
        "Returns number of registered module objects"
        return len(self.__modobjects)


    def __iter__(self):
        "Initiates the iterating process"

        self.__iter_list = self.__modobjects.keys()
        return self


    def next(self):
        """Internal Python iterating method, returns the next
module name and object to be processed"""

        if len(self.__iter_list) == 0:
            self.__iter_list = None
            raise StopIteration
        else:
            modname = self.__iter_list.pop()
            return (modname, self.__modobjects[modname])



class RtEvalModules(object):
    """RtEvalModules should normally be inherrited by a more specific module class.
    This class takes care of managing imported modules and have methods for starting
    and stopping the workload these modules contains."""

    def __init__(self, modules_root, logger):
        """Initialises the RtEvalModules() internal variables.  The modules_root
argument should point at the root directory where the modules will be loaded from.
The logger argument should point to a Log() object which will be used for logging
and will also be given to the instantiated objects during module import."""

        self._logger = logger
        self.__modules = ModuleContainer(modules_root, logger)


    # Export some of the internal module container methods
    # Primarily to have better control of the module containers
    # iteration API
    def _InstantiateModule(self, modname, modcfg, modroot = None):
        "Imports a module and returns an instantiated object from the module"
        return self.__modules.InstantiateModule(modname, modcfg, modroot)

    def _RegisterModuleObject(self, modname, modobj):
        "Registers an instantiated module object which RtEvalModules will control"
        return self.__modules.RegisterModuleObject(modname, modobj)

    def ModulesLoaded(self):
        "Returns number of imported modules"
        return self.__modules.ModulesLoaded()
    # End of exports


    def Start(self):
        """Prepares all the imported modules workload to start, but they will not
start their workloads yet"""

        if self.__modules.ModulesLoaded() == 0:
            raise RuntimeError("No %s modules configured" % self._module_type)

        self._logger.log(Log.INFO, "Starting %s modules" % self._module_type)
        for (modname, mod) in self.__modules:
            mod.start()
            self._logger.log(Log.DEBUG, "\t - %s started" % modname)

        self._logger.log(Log.DEBUG, "Waiting for all %s modules to get ready" % self._module_type)
        busy = True
        while busy:
            busy = False
            for (modname, mod) in self.__modules:
                if not mod.isAlive():
                    raise RuntimeError("%s died" % modname)
                if not mod.isReady():
                    busy = True
                    self._logger.log(Log.DEBUG, "Waiting for %s" % modname)

            if busy:
                time.sleep(1)

        self._logger.log(Log.DEBUG, "All %s modules are ready" % self._module_type)


    def Unleash(self):
        """Unleashes all the loaded modules workloads"""

        # turn loose the loads
        nthreads = 0
        self._logger.log(Log.INFO, "sending start event to all %s modules" % self._module_type)
        for (modname, mod) in self.__modules:
            mod.startevent.set()
            nthreads += 1

        return nthreads


    def Stop(self):
        """Stops all the running workloads from in all the loaded modules"""

        if self.ModulesLoaded() == 0:
            raise RuntimeError("No %s modules configured" % self._module_type)

        self._logger.log(Log.INFO, "Stopping %s modules" % self._module_type)
        for (modname, mod) in self.__modules:
            mod.stopevent.set()
            self._logger.log(Log.DEBUG, "\t - Stopping %s" % modname)
            mod.join(2.0)


    def MakeReport(self):
        """Collects all the loaded modules reports in a single libxml2.xmlNode() object"""

        rep_n = libxml2.newNode(self._report_tag)

        for (modname, mod) in self.__modules:
            self._logger.log(Log.DEBUG, "Getting report from %s" % modname)
            modrep_n = mod.MakeReport()
            if modrep_n is not None:
                rep_n.addChild(modrep_n)

        return rep_n
