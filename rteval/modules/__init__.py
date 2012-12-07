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
from rtevalConfig import rtevalCfgSection
import time, libxml2, threading

__all__ = ["rtevalModulePrototype", "ModuleContainer", "RtEvalModules"]


class rtevalModulePrototype(threading.Thread):
    "Prototype class for rteval modules - must be inherited by the real module"

    def __init__(self, modtype, name, logger=None):
        if logger and not isinstance(logger, Log):
            raise TypeError("logger attribute is not a Log() object")

        threading.Thread.__init__(self)

        self._module_type = modtype
        self._name = name
        self.__logger = logger
        self.__ready = False
        self.__events = {"start": threading.Event(),
                         "stop": threading.Event(),
                         "finished": threading.Event()}


    def _log(self, logtype, msg):
        "Common log function for rteval modules"
        if self.__logger:
            self.__logger.log(logtype, "[%s] %s" % (self._name, msg))


    def isReady(self):
        "Returns a boolean if the module is ready to run"
        return self.__ready


    def _setReady(self, state=True):
        "Sets the ready flag for the module"
        self.__ready = state


    def setStart(self):
        "Sets the start event state"
        self.__events["start"].set()


    def shouldStart(self):
        "Returns the start event state - indicating the module can start"
        return self.__events["start"].isSet()


    def setStop(self):
        "Sets the stop event state"
        self.__events["stop"].set()


    def shouldStop(self):
        "Returns the stop event state - indicating the module should stop"
        return self.__events["stop"].isSet()


    def _setFinished(self):
        "Sets the finished event state - indicating the module has completed"
        self.__events["finished"].set()


    def WaitForCompletion(self, wtime = None):
        "Blocks until the module has completed its workload"
        if not self.shouldStart():
            # If it hasn't been started yet, nothing to wait for
            return None
        return self.__events["finished"].wait(wtime)


    def _WorkloadSetup(self):
        "Required module method, which purpose is to do the initial workload setup, preparing for _WorkloadBuild()"
        raise NotImplementedError("_WorkloadSetup() method must be implemented in the %s module" % self._name)

    def _WorkloadBuild(self):
        "Required module method, which purpose is to compile additional code needed for the worklaod"
        raise NotImplementedError("_WorkloadBuild() method must be implemented in the %s module" % self._name)


    def _WorkloadPrepare(self):
        "Required module method, which will initialise and prepare the workload just before it is about to start"
        raise NotImplementedError("_WorkloadPrepare() method must be implemented in the %s module" % self._name)


    def _WorkloadTask(self):
        "Required module method, which kicks off the workload"
        raise NotImplementedError("_WorkloadTask() method must be implemented in the %s module" % self._name)


    def WorkloadAlive(self):
        "Required module method, which should return True if the workload is still alive"
        raise NotImplementedError("WorkloadAlive() method must be implemented in the %s module" % self._name)


    def _WorkloadCleanup(self):
        "Required module method, which will be run after the _WorkloadTask() has completed or been aborted by the 'stop event flag'"
        raise NotImplementedError("_WorkloadCleanup() method must be implemented in the %s module" % self._name)


    def run(self):
        "Workload thread runner - takes care of keeping the workload running as long as needed"
        if self.shouldStop():
            return

        # Initial workload setups
        self._WorkloadSetup()

        # Compile the workload
        self._WorkloadBuild()

        # Do final preparations of workload  before we're ready to start running
        self._WorkloadPrepare()

        # Wait until we're released
        while True:
            if self.shouldStop():
                return
            self.__events["start"].wait(1.0)
            if self.shouldStart():
                break

        self._log(Log.DEBUG, "Starting %s workload" % self._module_type)
        while not self.shouldStop():
            # Run the workload
            self._WorkloadTask()

            if self.shouldStop():
                break
            if not self.WorkloadAlive():
                self._log(Log.DEBUG, "%s workload stopped running." % self._module_type)
                break
            time.sleep(1.0)
        self._log(Log.DEBUG, "stopping %s workload" % self._module_type)
        self._WorkloadCleanup()


    def MakeReport(self):
        "required module method, needs to return an libxml2.xmlNode object with the the results from running"
        raise NotImplementedError("MakeReport() method must be implemented in the%s module" % self._name)



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

        if modcfg and not isinstance(modcfg, rtevalCfgSection):
            raise TypeError("modcfg attribute is not a rtevalCfgSection() object")

        mod = self.__importmod(modname, modroot)
        return mod.create(modcfg, self.__logger)


    def RegisterModuleObject(self, modname, modobj):
        """Registers an instantiated module object.  This module object will be
returned when a ModuleContainer object is iterated over"""
        self.__modobjects[modname] = modobj


    def ExportModule(self, modname, modroot = None):
        "Export module info, used to transfer an imported module to another ModuleContainer"
        if modroot is None:
            modroot = self.__modules_root

        mod = "%s.%s" % (modroot, modname)
        return (mod, self.__modsloaded[mod])


    def ImportModule(self, module):
        "Imports an exported module from another ModuleContainer"
        (modname, moduleimp) = module
        self.__modsloaded[modname] = moduleimp


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
    def _ImportModule(self, module):
        "Imports a module exported by ModuleContainer::ExportModule()"
        return self.__modules.ImportModule(module)

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
            mod.setStart()
            nthreads += 1

        return nthreads


    def _isAlive(self):
        """Returns True if all modules are running"""

        for (modname, mod) in self.__modules:
            # We requiring all modules to run to pass
            if not mod.WorkloadAlive():
                return False
        return True



    def Stop(self):
        """Stops all the running workloads from in all the loaded modules"""

        if self.ModulesLoaded() == 0:
            raise RuntimeError("No %s modules configured" % self._module_type)

        self._logger.log(Log.INFO, "Stopping %s modules" % self._module_type)
        for (modname, mod) in self.__modules:
            mod.setStop()
            self._logger.log(Log.DEBUG, "\t - Stopping %s" % modname)
            mod.join(2.0)


    def WaitForCompletion(self, wtime = None):
        """Waits for the running modules to complete their running"""

        self._logger.log(Log.INFO, "Waiting for %s modules to complete" % self._module_type)
        for (modname, mod) in self.__modules:
            self._logger.log(Log.DEBUG, "\t - Waiting for %s" % modname)
            mod.WaitForCompletion(wtime)
        self._logger.log(Log.DEBUG, "All %s modules completed" % self._module_type)


    def MakeReport(self):
        """Collects all the loaded modules reports in a single libxml2.xmlNode() object"""

        rep_n = libxml2.newNode(self._report_tag)

        for (modname, mod) in self.__modules:
            self._logger.log(Log.DEBUG, "Getting report from %s" % modname)
            modrep_n = mod.MakeReport()
            if modrep_n is not None:
                rep_n.addChild(modrep_n)

        return rep_n
