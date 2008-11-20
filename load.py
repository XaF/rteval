#!/usr/bin/python -tt

import sys
import os
import os.path
import time
import subprocess
import threading

class Load(threading.Thread):
    def __init__(self, name="<unnamed>", source=None, dir=None,
                 setup=None, build=None, run=None):
        threading.Thread.__init__(self)
        self.name = name
        self.source = source
        self.setupfn = setup
        self.buildfn = build
        self.runfn = run
        self.dir = dir
        self.startevent = threading.Event()
        self.stopevent = threading.Event()
        self.ready = False

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        os.chdir(self.dir)
        print "%s: cd'ing to %s" % (self.name, os.getcwd())

    def isReady(self):
        return self.ready

    def run(self):
        if self.stopevent.isSet():
            return
        self.mydir = self.setupfn(self.dir, self.source)
        if self.stopevent.isSet():
            return
        self.buildfn(self.mydir)
        self.ready = True
        while True:
            if self.stopevent.isSet():
                return
            self.startevent.wait(1.0)
            if self.startevent.isSet():
                break
        self.runfn(self.mydir, self.stopevent)


