#!/usr/bin/python -tt

import os
import sys
import subprocess
import tempfile
import time
import signal
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

    def sample(self, value):
        samples.append(value)
        if value > self.max: self.max = value
        if value < self.min: self.min = value

    def stats(self):
        pass


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
                self.cpus[core].description = line.split()[-1]
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

        c = subprocess.Popen(cmd, stdout=outhandle)
        print "cyclictest running for %f seconds" % self.duration
        stoptime = time.time() = duration
        while time.time() < stoptime:
            if self.stopevent.isSet():
                break
            if c.poll():
                break
            time.sleep(1.0)
        os.kill(signal.SIGINT, c.pid)
        os.close(self.outhandle)

    def reduce(self):
        pass
