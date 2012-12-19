#
#   HWLatDetect.py - Runs hwlatdetect and prepares the result for rteval
#
#   Copyright 2012   David Sommerseth <davids@redhat.com>
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

import os, sys, libxml2
from rteval.modules import rtevalModulePrototype
from rteval.Log import Log


class HWLatDetectRunner(rtevalModulePrototype):
    def __init__(self, config, logger=None):
        rtevalModulePrototype.__init__(self, 'measurement', 'hwlatdetect', logger)

        self.__cfg = config
        self.__hwlat = None
        self.__exceeding = None
        self.__samples = []


    def _WorkloadSetup(self):
        try:
            import hwlatdetect
            self.__hwlat = hwlatdetect.Detector()
        except Exception, e:
            self._log(Log.WARN, "hwlatdetect could not be loaded.  Will not run hwlatdetect")
            self._log(Log.DEBUG, str(e))


    def _WorkloadBuild(self):
        self._setReady()


    def _WorkloadPrepare(self):
        self.__running = False
        if self.__hwlat is None:
            return

        self._log(Log.DEBUG, "Preparing hwlatdetect")
        self.__hwlat.set('threshold', int(self.__cfg.setdefault('threshold', 15)))
        self.__hwlat.set('window', int(self.__cfg.setdefault('window', 1000000)))
        self.__hwlat.set('width', int(self.__cfg.setdefault('width', 800000)))
        self.__hwlat.testduration = int(self.__cfg.setdefault('duration', 10))
        self.__hwlat.setup()


    def _WorkloadTask(self):
        if self.__hwlat is None:
            return
        if self.__running:
            return

        self.__running = True
        self.__hwlat.detect()


    def WorkloadAlive(self):
        return self.__running


    def _WorkloadCleanup(self):
        if not self.__hwlat or not self.__running:
            self._setFinished()
            return

        self._log(Log.DEBUG, "Parsing results")
        # Grab the measurement results
        self.__exceeding = self.__hwlat.get("count")
        for s in self.__hwlat.samples:
            self.__samples.append(s.split('\t'))

        self.__running = False
        self._setFinished()


    def MakeReport(self):
        rep_n = libxml2.newNode('hwlatdetect')
        rep_n.newProp('format', '1.0')

        if self.__hwlat is None:
            rep_n.newProp('aborted', '1')
            return rep_n

        runp_n = rep_n.newChild(None, 'RunParams', None)
        runp_n.newProp('threshold', str(self.__hwlat.get('threshold')))
        runp_n.newProp('window', str(self.__hwlat.get('window')))
        runp_n.newProp('width', str(self.__hwlat.get('width')))
        runp_n.newProp('duration', str(self.__hwlat.testduration))

        sn = rep_n.newChild(None, 'samples', None)
        sn.newProp('exceeding', str(self.__exceeding))
        sn.newProp('count', str(len(self.__samples)))
        for s in self.__samples:
            n = sn.newChild(None, 'sample', None)
            n.newProp('timestamp', s[0])
            n.newProp('duration', s[1])

        return rep_n



def ModuleInfo():
    return {"parallel": False,
            "loads": False}



def ModuleParameters():
    return {"threshold": {"descr": "Specify the TSC gap in microseconds used to detect an SMI",
                          "default": 15,
                          "metavar": "MICROSEC"},
            "window":    {"descr": "Sample window size (in microseconds)",
                          "default": 1000000,
                          "metavar": "MICROSEC"},
            "width":     {"descr": "Sampling width inside the sampling window (in microseconds)",
                          "default": 800000,
                          "metavar": "MICROSEC"},
            "duration":  {"descr": "How long in seconds to run hwlatdetect",
                          "default": 15,
                          "metavar": "SEC"}
        }



def create(params, logger):
    return HWLatDetectRunner(params, logger)


if __name__ == '__main__':
    from rtevalConfig import rtevalConfig
    l = Log()
    l.SetLogVerbosity(Log.INFO|Log.DEBUG|Log.ERR|Log.WARN)
    cfg = rtevalConfig({}, logger=l)
    c = HWLatDetectRunner(cfg, l)
    c._WorkloadSetup()
    c._WorkloadPrepare()
    c._WorkloadTask()
    c._WorkloadCleanup()
    rep_n = c.MakeReport()

    xml = libxml2.newDoc('1.0')
    xml.setRootElement(rep_n)
    xml.saveFormatFileEnc('-','UTF-8',1)
