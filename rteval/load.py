#!/usr/bin/python -tt

import sys
import os
import os.path
import time
import subprocess
import threading

class Load(threading.Thread):
    def __init__(self, name="<unnamed>", source=None, dir=None, 
                 debug=False, num_cpus=1):
        threading.Thread.__init__(self)
        self.name = name
        self.source = source	# abs path to source archive
        self.dir = dir		# abs path to run dir
        self.mydir = None
        self.startevent = threading.Event()
        self.stopevent = threading.Event()
        self.ready = False
        self.debugging = debug
        self.num_cpus = num_cpus

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

    def debug(self, str):
        if self.debugging: print str

    def isReady(self):
        return self.ready

    def setup(self, topdir, tarball):
        pass

    def build(self, dir):
        pass

    def runload(self, dir):
        pass

    def run(self):
        if self.stopevent.isSet():
            return
        self.setup()
        if self.stopevent.isSet():
            return
        self.build()
        while True:
            if self.stopevent.isSet():
                return
            self.startevent.wait(1.0)
            if self.startevent.isSet():
                break
        self.runload()

    def report(self):
        pass
