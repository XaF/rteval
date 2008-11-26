#!/usr/bin/python -tt

import os
import sys
import subprocess
import tempfile
import time
import signal
from threading import *


class Cyclictest(Thread):
    def __init__(self, duration=60.0, priority = 90, outfile = None, threads = None):
        Thread.__init__(self)
        self.duration = duration
        self.stopevent = Event()
        self.threads = threads
        self.priority = priority
        self.outfile = outfile

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

    def reduce(self):
        pass
