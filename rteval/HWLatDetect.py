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

import os
import sys
import libxml2
import xmlout

class HWLatDetectRunner(object):
    def __init__(self,params={}):
        try:
            import hwlatdetect
            self.__hwlat = hwlatdetect.Detector()
        except Exception, e:
            print "** ERROR ** hwlatdetect could not be loaded.  Will not run hwlatdetect"
            print e
            self.__hwlat = None
            return

        self.__hwlat.set('threshold', int(params.setdefault('threshold', 15)))
        self.__hwlat.set('window', int(params.setdefault('window', 1000000)))
        self.__hwlat.set('width', int(params.setdefault('width', 800000)))
        self.__hwlat.testduration = int(params.setdefault('duration', 10))
        self.__hwlat.setup()

        self.__exceeding = None
        self.__samples = []


    def run(self):
        if self.__hwlat is None:
            raise Exception('Cannot run hwlatdetect')

        self.__hwlat.detect()

        # Copy out the results
        self.__exceeding = self.__hwlat.get("count")
        for s in self.__hwlat.samples:
            self.__samples.append(s.split('\t'))


    def genxml(self, x):
        x.openblock('hwlatdetect', {'format': '1.0'})
        x.taggedvalue('RunParams', '',
                      {'threshold': self.__hwlat.get('threshold'),
                       'window': self.__hwlat.get('window'),
                       'width': self.__hwlat.get('width'),
                       'duration': self.__hwlat.testduration}
                      )
        sn = libxml2.newNode('samples')
        sn.newProp('count', str(self.__exceeding))
        for s in self.__samples:
            n = libxml2.newNode('sample')
            n.newProp('timestamp', s[0])
            n.newProp('duration', s[1])
            sn.addChild(n)
        x.AppendXMLnodes(sn)
        x.closeblock()


if __name__ == '__main__':
    c = HWLatDetectRunner()
    c.run()
    x = xmlout.XMLOut('hwlat_test', '1.0')
    x.NewReport()
    c.genxml(x)
    x.close()
    x.Write('-')
