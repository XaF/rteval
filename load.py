#!/usr/bin/python -tt

import sys
import os
import os.path
import time
import subprocess
import threading

class Load(threading.Thread):
    def __init__(self, name="<unnamed>", source=None, dir=None):
        threading.Thread.__init__(self)
        self.name = name
        self.source = source	# abs path to source archive
        self.dir = dir		# abs path to run dir
        self.mydir = None
        self.startevent = threading.Event()
        self.stopevent = threading.Event()
        self.ready = False

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

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
        self.ready = True
        while True:
            if self.stopevent.isSet():
                return
            self.startevent.wait(1.0)
            if self.startevent.isSet():
                break
        self.runload()


