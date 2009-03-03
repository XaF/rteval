#!/usr/bin/python -tt

import os
import sys
import subprocess
import tempfile
import time
import signal
import schedutils
from threading import *
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

    def xmlout(self, f, indent, tag, val):
        f.write('%s<%s>%s</%s>\n' % ('\t'*indent, tag, val, tag))

    def xmlopen(self, f, indent, tag):
        f.write('%s<%s>\n' % ('\t'*indent, tag))
        return indent + 1

    def xmlclose(self, f, indent, tag):
        indent -= 1
        f.write('%s</%s>\n' % ('\t'*indent, tag))
        return indent

    def genxml(self, x):
        if self.type == 'system':
            x.openblock(self.type)
            x.taggedvalue('description', self.description)
        else:
            x.openblock(self.type, {'id':self.id})
            x.taggedvalue('priority', str(self.priority))
        x.openblock('statistics')
        x.taggedvalue('samples', str(len(self.samples)))
        x.taggedvalue('minimum', str(self.min))
        x.taggedvalue('maximum', str(self.max))
        x.taggedvalue('median', str(self.median))
        x.taggedvalue('mode', str(self.mode))
        x.taggedvalue('range', str(self.range))
        x.taggedvalue('mean', str(self.mean))
        x.taggedvalue('standard_deviation', str(self.stddev))
        x.closeblock()
        x.closeblock()

    def report(self, f):
        f.write("%s: %s (priority: %d)\n" % (self.id, self.description, self.priority))
        f.write("\tsamples:  %d\n" % len(self.samples))
        f.write("\tminimum:  %dus\n" % self.min)
        f.write("\tmaximum:  %dus\n" % self.max)
        f.write("\tmedian:   %dus\n" % self.median)
        f.write("\tmode:     %dus\n" % self.mode)
        f.write("\trange:    %dus\n" % self.range)
        f.write("\tmean:     %0.2fus\n" % self.mean)
        #f.write("\tvariance: %f\n" % self.variance)
        f.write("\tstddev:   %0.2fus\n" % self.stddev)
        f.write("\n")

class Cyclictest(Thread):
    def __init__(self, duration=None, priority = 95, 
                 outfile = None, threads = None, debugging=False,
                 keepdata = True):
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
        self.outfile = outfile
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
                self.data[core].description = line.split(': ')[-1][:-1]
        f.close()
        self.data['system'] = RunData('system', 'system', self.priority)
        self.data['system'].description = ("(%d cores) " % numcores) + self.data['0'].description
        self.dataitems = len(self.data.keys())
        self.debug("system has %d cpu cores" % (self.dataitems - 1))

    def __del__(self):
        if self.outfile and not self.keepdata and os.path.exists(self.outfile):
            os.remove(self.outfile)

    def debug(self, str):
        if self.debugging: print str

    def run(self):
        if self.outfile:
            self.outhandle = os.open(self.outfile, os.O_RDWR)
        else:
            (self.outhandle, self.outfile) = tempfile.mkstemp(prefix='cyclictest-', suffix='.dat')

        self.cmd = ['cyclictest', self.interval, '-nmv', 
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

    def xmlout(self, f, indent, tag, val):
        f.write('%s<%s>%s</%s>\n' % ('\t'*indent, tag, val, tag))

    def xmlopen(self, f, indent, tag):
        f.write('%s<%s>\n' % ('\t'*indent, tag))
        return indent + 1

    def xmlclose(self, f, indent, tag):
        indent -= 1
        f.write('%s</%s>\n' % ('\t'*indent, tag))
        return indent

    def genxml(self, x):
        x.openblock('cyclictest')
        x.taggedvalue('command_line', " ".join(self.cmd))

        f = open(self.outfile)
        for line in f:
            if line.startswith("Thread"): continue
            pieces = line.split()
            if len(pieces) != 3:  continue
            cpu = pieces[0][:-1]
            latency = int(pieces[2])
            self.data[cpu].sample(latency)
            self.data['system'].sample(latency)
        ids = self.data.keys()
        ids.sort()
        if 'system' in ids:
            ids.remove('system')
        c = self.data['system']
        c.reduce()
        c.genxml(x)
        for id in ids:
            d = self.data[id]
            d.reduce()
            d.genxml(x)
        x.closeblock()

    def report(self, handle=None):
        f = open(self.outfile)
        for line in f:
            if line.startswith("Thread"): continue
            pieces = line.split()
            if len(pieces) != 3:  continue
            cpu = pieces[0][:-1]
            latency = int(pieces[2])
            self.data[cpu].sample(latency)
            self.data['system'].sample(latency)
        ids = self.data.keys()
        ids.sort()
        if 'system' in ids:
            ids.remove('system')
        c = self.data['system']
        c.reduce()
        if handle:
            r = handle
        else:
            r = open(self.reportfile, "w")
        r.write('\nCyclictest Command Line: %s\n' % " ".join(self.cmd))
        if self.keepdata:
            r.write('Cyclictest raw data: %s\n' % os.path.basename(self.outfile))
        r.write('\nOverall System Statistics\n')
        c.report(r)
        r.write("Individual Core Statistics\n")
        for id in ids:
            d = self.data[id]
            d.reduce()
            d.report(r)
        if not handle:
            r.close()

if __name__ == '__main__':
    c = CyclicTest()
    c.run()

    
