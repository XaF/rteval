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

import libxml2
from modules import RtEvalModules, ModuleContainer


class MeasurementProfile(RtEvalModules):
    """Keeps and controls all the measurement modules with the same measurement profile"""

    def __init__(self, with_load, run_parallel, modules_root, logger):
        self.__with_load = with_load
        self.__run_parallel = run_parallel

        self._module_type = "measurement"
        self._module_config = "measurement"
        self._report_tag = "Profile"
        RtEvalModules.__init__(self, modules_root, logger)


    def GetProfile(self):
        "Returns the profile characteristic as (with_load, run_parallel)"
        return (self.__with_load, self.__run_parallel)


    def ImportModule(self, module):
        "Imports an exported module from a ModuleContainer() class"
        return self._ImportModule(module)


    def Setup(self, modname, modcfg):
        "Instantiates and prepares a measurement module"

        modobj = self._InstantiateModule(modname, modcfg)
        self._RegisterModuleObject(modname, modobj)


    def MakeReport(self):
        "Generates an XML report for all run measurement modules in this profile"
        rep_n = RtEvalModules.MakeReport(self)
        rep_n.newProp("loads", self.__with_load and "1" or "0")
        rep_n.newProp("parallel", self.__run_parallel and "1" or "0")
        return rep_n



class MeasurementModules(object):
    """Class which takes care of all measurement modules and groups them into
measurement profiles, based on their characteristics"""

    def __init__(self, config, logger):
        self.__cfg = config
        self.__logger = logger
        self.__measureprofiles = []
        self.__modules_root = "modules.measurement"


    def GetProfile(self, with_load, run_parallel):
        "Returns the appropriate MeasurementProfile object, based on the profile type"

        for p in self.__measureprofiles:
            mp = p.GetProfile()
            if mp == (with_load, run_parallel):
                return p
        return None


    def Setup(self, modparams):
        "Loads all measurement modules and group them into different measurement profiles"

        if not isinstance(modparams, dict):
            raise TypeError("modparams attribute is not of a dictionary type")

        # Temporary module container, which is used to evalute measurement modules
        container = ModuleContainer(self.__modules_root, self.__logger)

        modcfg = self.__cfg.GetSection("measurement")
        for (modname, modtype) in modcfg:
            if modtype.lower() == 'module':  # Only 'module' will be supported (ds)
                # Extract the measurement modules info
                modinfo = container.ModuleInfo(modname)

                # Get the correct measurement profile container for this module
                mp = self.GetProfile(modinfo["loads"], modinfo["parallel"])
                if mp is None:
                    # If not found, create a new measurement profile
                    mp = MeasurementProfile(modinfo["loads"], modinfo["parallel"],
                                            self.__modules_root, self.__logger)
                    self.__measureprofiles.append(mp)

                    # Export the module imported here and transfer it to the
                    # measurement profile
                    mp.ImportModule(container.ExportModule(modname))

                # Setup this imported module inside the appropriate measurement profile
                self.__cfg.AppendConfig(modname, modparams)
                mp.Setup(modname, self.__cfg.GetSection(modname))

        del container


    def MakeReport(self):
        "Generates an XML report for all measurement profiles"

        # Get the reports from all meaurement modules in all measurement profiles
        rep_n = libxml2.newNode("Measurements")
        for mp in self.__measureprofiles:
            mprep_n = mp.MakeReport()
            if mprep_n:
                rep_n.addChild(mprep_n)

        return rep_n
