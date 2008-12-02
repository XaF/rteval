#!/usr/bin/python -tt

import os
import sys
import subprocess
import tempfile
import time
import signal
import schedutils
from threading import *

class CpuData(object):
    def __init__(self, cpu):
        self.cpu = cpu
        self.description = ''
        self.samples = []
        self.min = 100000000
        self.max = 0
        self.stddev = 0.0
        self.mean = 0.0
        self.mode = 0.0
        self.median = 0.0
        self.range = 0.0

    def sample(self, cpu, value):
        if cpu != self.cpu:
            raise RuntimeError, "Invalid cpu value (%d) on cpu %d" % (cpu, self.cpu)
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
        self.mean = total / len(self.samples)
        occurances = 0
        for i in histogram.keys():
            if histogram[i] > occurances:
                occurances = histogram[i]
                self.mode = i
        # median
        sorted = copy.copy(self.samples)
        sorted.sort()
        self.range = sorted[-1] - sorted[0]
        mid = length/2
        if length & 1:
            self.median = sorted[mid]
        else:
            self.median = (sorted[mid-1]+sorted[mid]) / 2
        # variance
        n1 = (length * reduce(lambda x,y: x + y**2, self.samples, 0))
        n2 = reduce(lambda x,y: x+y, self.samples, 0) ** 2
        self.variance = (n1 - n2) / (length * (length - 1))
        self.stddev = math.sqrt(self.variance)

    def report(self):
        print "cpu%d: %s" % (self.cpu, self.description)
        print "\tsamples:  %d" % len(self.samples)
        print "\tminimum:  %d" % self.min
        print "\tmaximum:  %d" % self.max
        print "\tmedian:   %d" % self.median
        print "\tmode:     %d" % self.mode
        print "\trange:    %d" % self.range
        print "\tmean:     %d" % self.mean
        print "\tvariance: %f" % self.variance
        print "\tstddev:   %f" % self.stddev
        print ""

( SCHED_OTHER, SCHED_FIFO, SCHED_RR, SCHED_BATCH ) = range(4)

class Cyclictest(Thread):
    def __init__(self, duration=60.0, priority = 90, outfile = None, threads = None):
        Thread.__init__(self)
        self.duration = duration
        self.stopevent = Event()
        self.threads = threads
        self.priority = priority
        self.outfile = outfile
        f = open('/proc/cpuinfo')
        self.cpus = []
        core = 0
        for line in f:
            if line.startswith('processor'):
                core = int(line.split()[-1])
                self.cpus.append(CpuData(core))
            if line.startswith('model name'):
                self.cpus[core].description = line.split(': ')[-1][:-1]
        f.close()
        self.cores = len(self.cpus)
        print "system has %d cpu cores" % self.cores

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
        print "cyclictest running for %.2f seconds" % self.duration
        stoptime = time.time() + self.duration
        while time.time() < stoptime:
            if self.stopevent.isSet():
                break
            if c.poll():
                break
            time.sleep(1.0)
        os.kill(c.pid, signal.SIGINT)
        os.close(self.outhandle)

    def report(self):
        f = open(self.outfile)
        for line in f:
            if line.startswith("Thread"): continue
            pieces = line.split()
            if len(pieces) != 3:
                raise RuntimeError, "Invalid input data: %s" % line
            cpu = int(pieces[0][:-1])
            latency = int(pieces[2])
            self.cpus[cpu].sample(cpu, latency)
        for c in self.cpus:
            c.reduce()
            c.report()
