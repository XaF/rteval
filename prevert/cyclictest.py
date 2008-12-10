#!/usr/bin/python -tt

import os
import sys
import subprocess
import tempfile
import time
import signal
import schedutils
from threading import *

class RunData(object):
    def __init__(self, id):
        self.id = id
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

    def report(self, f):
        f.write("%s: %s\n" % (self.id, self.description))
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
    def __init__(self, duration=60.0, priority = 95, 
                 outfile = None, threads = None, debugging=False):
        Thread.__init__(self)
        self.duration = duration
        self.stopevent = Event()
        self.threads = threads
        self.priority = priority
        self.outfile = outfile
        self.debugging = debugging
        f = open('/proc/cpuinfo')
        self.data = {}
        numcores = 0
        for line in f:
            if line.startswith('processor'):
                core = line.split()[-1]
                self.data[core] = RunData(core)
                numcores += 1
            if line.startswith('model name'):
                self.data[core].description = line.split(': ')[-1][:-1]
        f.close()
        self.data['system'] = RunData('system')
        self.data['system'].description = ("(%d cores) " % numcores) + self.data['0'].description
        self.dataitems = len(self.data.keys())
        self.debug("system has %d cpu cores" % (self.dataitems - 1))

    def __del__(self):
        if self.outfile:
            os.remove(self.outfile)

    def debug(self, str):
        if self.debugging: print str

    def run(self):
        if self.outfile:
            self.outhandle = os.open(self.outfile, os.O_RDWR)
        else:
            (self.outhandle, self.outfile) = tempfile.mkstemp()

        cmd = ['cyclictest', '-nmv', "-p%d" % self.priority]
        if self.threads:
            cmd.append("-t%d" % self.threads)
        else:
            cmd.append("-t")

        c = subprocess.Popen(cmd, stdout=self.outhandle)
        self.debug("cyclictest running for %.2f seconds" % self.duration)
        stoptime = time.time() + self.duration
        while time.time() < stoptime:
            if self.stopevent.isSet():
                break
            if c.poll():
                break
            time.sleep(1.0)
        self.debug("stopping cyclictest")
        os.kill(c.pid, signal.SIGINT)
        os.close(self.outhandle)

    def report(self):
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
        print "\nOverall System Statistics"
        c.report(sys.stdout)
        print "Individual Core Statistics"
        for id in ids:
            c = self.data[id]
            c.reduce()
            c.report(sys.stdout)

if __name__ == '__main__':
    c = CyclicTest()
    c.run()

    
