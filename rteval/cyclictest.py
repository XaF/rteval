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
    '''class to keep instance data from a cyclictest run'''
    def __init__(self, id, type, priority):
        self.id = id
        self.type = type
        self.priority = priority
        self.description = ''
        # histogram of data
        self.samples = {}
        self.numsamples = 0
        self.min = 100000000
        self.max = 0
        self.stddev = 0.0
        self.mean = 0.0
        self.mode = 0.0
        self.median = 0.0
        self.range = 0.0
        self.mad = 0.0

    def sample(self, value):
        self.samples[value] += self.samples.setdefault(value, 0) + 1
        if value > self.max: self.max = value
        if value < self.min: self.min = value
        self.numsamples += 1

    def bucket(self, index, value):
        self.samples[index] = self.samples.setdefault(index, 0) + value
        if value and index > self.max: self.max = index
        if value and index < self.min: self.min = index
        self.numsamples += value

    def reduce(self):
        import math
        print "reducing %s" % self.id
        total = 0
        keys = self.samples.keys()
        keys.sort()
        sorted = []

        mid = self.numsamples / 2

        # mean, mode, and median
        occurances = 0
        lastkey = -1
        for i in keys:
            if mid > total and mid <= (total + self.samples[i]):
                if self.numsamples & 1 and mid == total+1:
                    self.median = (lastkey + i) / 2
                else:
                    self.median = i
            total += (i * self.samples[i])
            if self.samples[i] > occurances:
                occurances = self.samples[i]
                self.mode = i
        self.mean = float(total) / float(self.numsamples)

        # range
        for i in keys:
            if self.samples[i]:
                low = i
                break
        high = keys[-1]
        while high and self.samples[high] == 0:
            high -= 1
        self.range = high - low

        # Mean Absolute Deviation and Variance
        madsum = 0
        varsum = 0
        for i in keys:
            madsum += float(abs(float(i) - self.mean) * self.samples[i])
            varsum += float(((float(i) - self.mean) ** 2) * self.samples[i])
        self.mad = madsum / self.numsamples
        self.variance = varsum / (self.numsamples - 1)
        
        # standard deviation
        self.stddev = math.sqrt(self.variance)

    def genxml(self, x):
        if self.type == 'system':
            x.openblock(self.type, {'description':self.description})
        else:
            x.openblock(self.type, {'id': self.id, 'priority': self.priority})
        x.openblock('statistics')
        x.taggedvalue('samples', str(self.numsamples))
        x.taggedvalue('minimum', str(self.min), {"unit": "us"})
        x.taggedvalue('maximum', str(self.max), {"unit": "us"})
        x.taggedvalue('median', str(self.median), {"unit": "us"})
        x.taggedvalue('mode', str(self.mode), {"unit": "us"})
        x.taggedvalue('range', str(self.range), {"unit": "us"})
        x.taggedvalue('mean', str(self.mean), {"unit": "us"})
        x.taggedvalue('mean_absolute_deviation', str(self.mad), {"unit": "us"})
        x.taggedvalue('variance', str(self.variance), {"unit": "us"})
        x.taggedvalue('standard_deviation', str(self.stddev), {"unit": "us"})
        x.closeblock()
        h = libxml2.newNode('histogram')
        h.newProp('nbuckets', str(len(self.samples)))
        keys = self.samples.keys()
        keys.sort()
        for k in keys:
            b = libxml2.newNode('bucket')
            b.newProp('index', str(k))
            b.newProp('value', str(self.samples[k]))
            h.addChild(b)
        x.AppendXMLnodes(h)
        x.closeblock()


class Cyclictest(Thread):
    def __init__(self, duration=None, priority = 95, 
                 outfile = None, threads = None, debugging=False,
                 keepdata = False, params={}):
        Thread.__init__(self)
        self.duration = duration
        self.keepdata = keepdata
        self.stopevent = Event()
        self.finished = Event()
        self.threads = threads
        self.priority = priority
        self.interval = "-i100"
        self.debugging = debugging
        self.reportfile = 'cyclictest.rpt'
        self.params = params
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
        self.numcores = numcores

    def __del__(self):
        pass

    def debug(self, str):
        if self.debugging: print "cyclictest: %s" % str

    def run(self):
        if self.params.has_key('buckets'):
            buckets = int(self.params.buckets)
        else:
            buckets = 2000
        if self.params.has_key('interval'):
            self.interval = '-i%d' % int(self.params.interval)

        self.cmd = ['cyclictest', self.interval, '-a', '-qnm', '-d0', '-h %d' % buckets,
                    "-p%d" % self.priority]
        if self.threads:
            self.cmd.append("-t%d" % self.threads)
        else:
            self.cmd.append("-t")

        self.debug("starting with cmd: %s" % " ".join(self.cmd))
        null = os.open('/dev/null', os.O_RDWR)
        c = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=null, stdin=null)
        while True:
            if self.stopevent.isSet():
                break
            if c.poll():
                self.debug("process died! bailng out...")
                break
            time.sleep(1.0)
        self.debug("stopping")
        os.kill(c.pid, signal.SIGINT)
        # now parse the histogram output
        for line in c.stdout:
            if line.startswith('#'): continue
            vals = line.split()
            index = int(vals[0])
            for i in range(0, len(self.data)-1):
                self.data[str(i)].bucket(index, int(vals[i+1]))
                self.data['system'].bucket(index, int(vals[i+1]))
        for n in self.data.keys():
            self.data[n].reduce()
        self.finished.set()

    def genxml(self, x):
        x.openblock('cyclictest')
        x.taggedvalue('command_line', " ".join(self.cmd))

        self.data["system"].genxml(x)
        for t in range(0, self.numcores):
            self.data[str(t)].genxml(x)
        x.closeblock()


if __name__ == '__main__':
    c = CyclicTest()
    c.run()

    
