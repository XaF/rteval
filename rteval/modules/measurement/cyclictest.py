#
#   cyclictest.py - object to manage a cyclictest executable instance
#
#   Copyright 2009 - 2012  Clark Williams <williams@redhat.com>
#   Copyright 2012         David Sommerseth <davids@redhat.com>
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

import os, sys, subprocess, signal, libxml2
from Log import Log
from modules import rtevalModulePrototype


class RunData(object):
    '''class to keep instance data from a cyclictest run'''
    def __init__(self, id, type, priority, logfnc):
        self.id = id
        self.type = type
        self.priority = int(priority)
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
        self.variance = 0.0
        self._log = logfnc

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

        # check to see if we have any samples and if we
        # only have 1 (or none) set the calculated values
        # to zero and return
        if self.numsamples <= 1:
            self._log(Log.DEBUG, "skipping %s (%d samples)" % (self.id, self.numsamples))
            self.variance = 0
            self.mad = 0
            self.stddev = 0
            return

        self._log(Log.INFO, "reducing %s" % self.id)
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


    def MakeReport(self):
        rep_n = libxml2.newNode(self.type)
        if self.type == 'system':
            rep_n.newProp('description', self.description)
        else:
            rep_n.newProp('id', str(self.id))
            rep_n.newProp('priority', str(self.priority))

        stat_n = rep_n.newChild(None, 'statistics', None)

        stat_n.newTextChild(None, 'samples', str(self.numsamples))

        n = stat_n.newTextChild(None, 'minimum', str(self.min))
        n.newProp('unit', 'us')

        n = stat_n.newTextChild(None, 'maximum', str(self.max))
        n.newProp('unit', 'us')

        n = stat_n.newTextChild(None, 'mediam', str(self.median))
        n.newProp('unit', 'us')

        n = stat_n.newTextChild(None, 'mode', str(self.mode))
        n.newProp('unit', 'us')

        n = stat_n.newTextChild(None, 'range', str(self.range))
        n.newProp('unit', 'us')

        n = stat_n.newTextChild(None, 'mean', str(self.mean))
        n.newProp('unit', 'us')

        n = stat_n.newTextChild(None, 'mean_absolute_deviation', str(self.mad))
        n.newProp('unit', 'us')

        n = stat_n.newTextChild(None, 'variance', str(self.variance))
        n.newProp('unit', 'us')

        n = stat_n.newTextChild(None, 'standard_deviation', str(self.stddev))
        n.newProp('unit', 'us')

        hist_n = rep_n.newChild(None, 'histogram', None)
        hist_n.newProp('nbuckets', str(len(self.samples)))
        keys = self.samples.keys()
        keys.sort()
        for k in keys:
            b_n = hist_n.newChild(None, 'bucket', None)
            b_n.newProp('index', str(k))
            b_n.newProp('value', str(self.samples[k]))

        return rep_n


class Cyclictest(rtevalModulePrototype):
    def __init__(self, config, logger=None):
        rtevalModulePrototype.__init__(self, 'measurement', 'cyclictest', logger)
        self.__cfg = config

        # Create a RunData object per CPU core
        f = open('/proc/cpuinfo')
        self.__numanodes = int(self.__cfg.setdefault('numanodes', 0))
        self.__priority = int(self.__cfg.setdefault('priority', 95))
        self.__buckets = int(self.__cfg.setdefault('buckets', 2000))
        self.__distance = int(self.__cfg.setdefault('distance', 25))
        self.__numcores = 0
        self.__cyclicdata = {}
        for line in f:
            if line.startswith('processor'):
                core = line.split()[-1]
                self.__cyclicdata[core] = RunData(core, 'core',self.__priority,
                                                  logfnc=self._log)
                self.__numcores += 1
            if line.startswith('model name'):
                desc = line.split(': ')[-1][:-1]
                self.__cyclicdata[core].description = ' '.join(desc.split())
        f.close()

        # Create a RunData object for the overall system
        self.__cyclicdata['system'] = RunData('system', 'system', self.__priority,
                                              logfnc=self._log)
        self.__cyclicdata['system'].description = ("(%d cores) " % self.__numcores) + self.__cyclicdata['0'].description
        self._log(Log.DEBUG, "system has %d cpu cores" % self.__numcores)
        self.__started = False


    def __getmode(self):
        if self.__numanodes > 1:
            self._log(Log.DEBUG, "running in NUMA mode (%d nodes)" % self.__numanodes)
            return '--numa'
        self._log(Log.DEBUG, "running in SMP mode")
        return '--smp'


    def _WorkloadSetup(self):
        self.__cyclicprocess = None
        pass


    def _WorkloadBuild(self):
        self._setReady()


    def _WorkloadPrepare(self):
        if self.__cfg.has_key('interval'):
            self.__interval = '-i%d' % int(self.__cfg.interval)

        self.__cmd = ['cyclictest',
                      self.__interval,
                      '-qm',
                      '-d%d' % self.__distance,
                      '-h %d' % self.__buckets,
                      "-p%d" % int(self.__priority),
                      self.__getmode(),
                      ]

        if self.__cfg.has_key('threads') and __cfg.threads:
            self.__cmd.append("-t%d" % int(self.__cfg.threads))


    def _WorkloadTask(self):
        if self.__started:
            # Don't restart cyclictest if it is already runing
            return

        self._log(Log.DEBUG, "starting with cmd: %s" % " ".join(self.__cmd))
        self.__nullfp = os.open('/dev/null', os.O_RDWR)
        self.__cyclicprocess = subprocess.Popen(self.__cmd,
                                                stdout=subprocess.PIPE,
                                                stderr=self.__nullfp,
                                                stdin=self.__nullfp)
        self.__started = True


    def WorkloadAlive(self):
        if self.__started:
            return self.__cyclicprocess.poll() is None
        else:
            return False


    def _WorkloadCleanup(self):
        if self.__cyclicprocess.poll() == None:
            os.kill(self.__cyclicprocess.pid, signal.SIGINT)

        # now parse the histogram output
        for line in self.__cyclicprocess.stdout:
            if line.startswith('#'): continue
            vals = line.split()
            index = int(vals[0])
            for i in range(0, len(self.__cyclicdata)-1):
                if str(i) not in self.__cyclicdata: continue
                self.__cyclicdata[str(i)].bucket(index, int(vals[i+1]))
                self.__cyclicdata['system'].bucket(index, int(vals[i+1]))
        for n in self.__cyclicdata.keys():
            self.__cyclicdata[n].reduce()

        self._setFinished()
        self.__started = False
        os.close(self.__nullfp)
        del self.__nullfp


    def MakeReport(self):
        rep_n = libxml2.newNode('cyclictest')
        rep_n.newProp('command_line', ' '.join(self.__cmd))

        rep_n.addChild(self.__cyclicdata["system"].MakeReport())
        for thr in range(0, self.__numcores):
            if str(thr) not in self.__cyclicdata:
                continue

            rep_n.addChild(self.__cyclicdata[str(thr)].MakeReport())

        return rep_n


def ModuleInfo():
    return {"parallel": True,
            "loads": True}

def create(params, logger):
    return Cyclictest(params, logger)


if __name__ == '__main__':
    c = CyclicTest()
    c.run()

    
