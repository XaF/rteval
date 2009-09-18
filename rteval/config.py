#!/usr/bin/python -tt
#
#   rteval - script for evaluating platform suitability for RT Linux
#
#           This program is used to determine the suitability of
#           a system for use in a Real Time Linux environment.
#           It starts up various system loads and measures event
#           latency while the loads are running. A report is generated
#           to show the latencies encountered during the run.
#
#   Copyright 2009   Clark Williams <williams@redhat.com>
#   Copyright 2009   David Sommerseth <davids@redhat.com>
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
import ConfigParser

class rtevalCfgSection(object):

    def __init__(self, section_cfg):
        self.__update_config_vars(section_cfg)

    def __str__(self):
        "Simple method for dumping config when object is used as a string"
        return str(self.__cfgdata)

    def __update_config_vars(self, section_cfg):
        if section_cfg is None:
            return
        self.__cfgdata = section_cfg

        # create member variables from config info
        for m in section_cfg.keys():
            self.__dict__[m] = section_cfg[m]



class rtevalConfig(rtevalCfgSection):
    "Config parser for rteval"
    
    def __init__(self, logfunc = None):
        self.__config_data = {}
        self.__info = logfunc or self.__nolog


    def __str__(self):
        "Simple method for dumping config when object is used as a string"
        return str(self.__config_data)


    def __nolog(self, str):
        "Dummy log function, used when no log function is configured"
        pass


    def __find_config(self):
        "locate a config file"
        for f in ('rteval.conf', '/etc/rteval.conf'):
            p = os.path.abspath(f)
            if os.path.exists(p):
                self.__info("found config file %s" % p)
                return p
        raise RuntimeError, "Unable to find configfile"


    def Load(self, fname = None):
        "read and parse the configfile"

        cfgfile = fname or self.__find_config()
        self.__info("reading config file %s" % cfgfile)
        ini = ConfigParser.ConfigParser()
        ini.read(cfgfile)

        # wipe any previously read config info (other than the rteval stuff)
        for s in self.__config_data.keys():
            if s == 'rteval': 
                continue
            self.__config_data[s] = {}

        # copy the section data into the __config_data dictionary
        for s in ini.sections():
            self.__config_data[s] = {}
            for i in ini.items(s):
                self.__config_data[s][i[0]] = i[1]

        # export the rteval section to member variables
        try:
            self._rtevalCfgSection__update_config_vars(self.__config_data['rteval'])
        except KeyError:
            pass
        except Exception, err:
            raise err

    def GetSection(self, section):
        try:
            return rtevalCfgSection(self.__config_data[section])
        except KeyError, err:
            raise KeyError("The section '%s' does not exist" % section)

