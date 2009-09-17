#!/usr/bin/python -tt
#
#   cyclictest.py - object to manage a cyclictest executable instance
#
#   Copyright 2009   Clark Williams <williams@redhat.com>
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
import subprocess
import tempfile
import time
import signal
import schedutils
from threading import *
import libxml2
import xmlout

class RunData(object):
    def __init__(self, id, type, priority):
        self.id = id
        self.type = type
        self.priority = priority
        self.description = ''
        self.samples = []
        self.min = 100000000
        self.max = 0
        self.stddev = 0.0
        self.mean = 0.0
        self.mode = 0.0
        self.median = 0.0
        self.range = 0.0

    def sample(self, value):
        self.samples.append(value)
        if value > self.max: self.max = value
        if value < self.min: self.min = value

    def reduce(self):
        import math
        import copy
        total = 0
        histogram = {}
        length = len(self.samples)

        # mean and mode
        for i in self.samples:
            total += i
            histogram[i] = histogram.setdefault(i, 0) + 1
        self.mean = float(total) / float(len(self.samples))
        occurances = 0
        for i in histogram.keys():
            if histogram[i] > occurances:
                occurances = histogram[i]
                self.mode = i

        # median and range
        sorted = copy.copy(self.samples)
        sorted.sort()
        self.range = sorted[-1] - sorted[0]
        mid = length/2
        if length & 1:
            self.median = sorted[mid]
        else:
            self.median = (sorted[mid-1]+sorted[mid]) / 2

        # variance
        # from Statistics for the Terrified:
        #n1 = (length * reduce(lambda x,y: x + y**2, self.samples))
        #n2 = reduce(lambda x,y: x+y, self.samples) ** 2
        #self.variance = (n1 - n2) / (length * (length - 1))

        # from Statistics for the Utterly Confused
        self.variance = sum(map(lambda x: float((x - self.mean) ** 2), self.samples)) / (length - 1)
        
        # standard deviation
        self.stddev = math.sqrt(self.variance)

    def genxml(self, x):
        if self.type == 'system':
            x.openblock(self.type, {'description':self.description})
        else:
            x.openblock(self.type, {'id': self.id, 'priority': self.priority})
        x.openblock('statistics')
        x.taggedvalue('samples', str(len(self.samples)))
        x.taggedvalue('minimum', str(self.min), {"unit": "us"})
        x.taggedvalue('maximum', str(self.max), {"unit": "us"})
        x.taggedvalue('median', str(self.median), {"unit": "us"})
        x.taggedvalue('mode', str(self.mode))
        x.taggedvalue('range', str(self.range), {"unit": "us"})
        x.taggedvalue('mean', str(self.mean), {"unit": "us"})
        x.taggedvalue('standard_deviation', str(self.stddev), {"unit": "us"})
        x.closeblock()
        x.closeblock()


class Cyclictest(Thread):
    def __init__(self, duration=None, priority = 95, 
                 outfile = None, threads = None, debugging=False,
                 keepdata = False):
        Thread.__init__(self)
        self.duration = duration
        self.keepdata = keepdata
        # if no duration or duration is greater than 3 hours
        #  set sample interval to 1ms
        if duration == None or duration > 3600 * 3:
            self.interval = "-i1000000"
        # if run between 1 and 3 hours set sample interval
        #   to 100 microseconds
        elif duration > 3600:
            self.interval = "-i100000"
        # less than 1hr run default to 10us interval
        else:
            self.interval = "-i10000"
        self.stopevent = Event()
        self.threads = threads
        self.priority = priority
        if outfile:
            self.outfile = outfile
        else:
            self.outfile = "cyclictest.dat"
        self.debugging = debugging
        self.reportfile = 'cyclictest.rpt'
        f = open('/proc/cpuinfo')
        self.data = {}
        numcores = 0
        for line in f:
            if line.startswith('processor'):
                core = line.split()[-1]
                self.data[core] = RunData(core, 'core', self.priority - int(core))
                numcores += 1
            if line.startswith('model name'):
                desc = line.split(': ')[-1][:-1]
                self.data[core].description = ' '.join(desc.split())
        f.close()
        self.data['system'] = RunData('system', 'system', self.priority)
        self.data['system'].description = ("(%d cores) " % numcores) + self.data['0'].description
        self.dataitems = len(self.data.keys())
        self.debug("system has %d cpu cores" % (self.dataitems - 1))


    def __del__(self):
        pass

    def debug(self, str):
        if self.debugging: print str

    def run(self):
        if self.outfile:
            self.outhandle = os.open(self.outfile, os.O_RDWR|os.O_CREAT)
        else:
            (self.outhandle, self.outfile) = tempfile.mkstemp(prefix='cyclictest-', suffix='.dat')

        self.cmd = ['cyclictest', self.interval, '-nmv', '-d0',
                    "-p%d" % self.priority]
        if self.threads:
            self.cmd.append("-t%d" % self.threads)
        else:
            self.cmd.append("-t")

        self.debug("starting cyclictest with cmd: %s" % " ".join(self.cmd))
        null = os.open('/dev/null', os.O_RDWR)
        c = subprocess.Popen(self.cmd, stdout=self.outhandle, 
                             stderr=null, stdin=null)
        while True:
            if self.stopevent.isSet():
                break
            if c.poll():
                self.debug("cyclictest process died! bailng out...")
                break
            time.sleep(1.0)
        self.debug("stopping cyclictest")
        os.kill(c.pid, signal.SIGINT)
        os.close(self.outhandle)

    def genxml(self, x):
        x.openblock('cyclictest')
        x.taggedvalue('command_line', " ".join(self.cmd))

        samplenodes = libxml2.newNode('RawSampleData')
        grouptags = {}

        # Parse the cyclictest results
        f = open(self.outfile)
        for line in f:
            pieces = line.split(':')

            if line.startswith("Thread"):
                # Parse "header" info
                thread = int(pieces[0].split()[1])

                # Create a thread node for each separate thread which we find
                node = libxml2.newNode('Thread')
                node.newProp('id', str(thread))
                node.newProp('interval', str(int(pieces[1])))

                # Add a direct pointer to each thread
                grouptags[thread] = node

                # Add this thread node to the complete sample set
                samplenodes.addChild(node)
            else:
                # Parse sample data - must have 3 parts
                if len(pieces) == 3:
                    # Split up the data - convert to integers, to be sure
                    # we process them as integers later on (spaces, invalid data, etc)
                    cpu = int(pieces[0])
                    seq = int(pieces[1])
                    latency = int(pieces[2])

                    # Create a sample node
                    sample_n = libxml2.newNode('Sample')
                    sample_n.newProp('seq', str(seq))
                    sample_n.newProp('latency', str(latency))
                    sample_n.newProp('latency_unit', 'us');

                    # Append this sample node to the corresponding thread node
                    grouptags[cpu].addChild(sample_n)

                    # Record the latency for calculations later on
                    self.data[str(cpu)].sample(latency)
                    self.data['system'].sample(latency)

        for id in self.data.keys():
            d = self.data[id]
            d.reduce()
            d.genxml(x)
        x.AppendXMLnodes(samplenodes)
        x.closeblock()

        if self.outfile and not self.keepdata and os.path.exists(self.outfile):
            os.remove(self.outfile)

if __name__ == '__main__':
    c = CyclicTest()
    c.run()

    
