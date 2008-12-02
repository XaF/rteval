#!/usr/bin/python -tt

# PreVeRT - Pre-Verification for Real Time
#           This program is used to determine the suitability of
#           a system for use in a Real Time Linux environment.
#           It starts up various system loads and measures event
#           latency while the loads are running. A report is generated
#           to show the latencies encountered during the run.

import sys
import os
import os.path
import time
import threading
import subprocess
import glob
import tempfile
import optparse

sys.pathconf = "."
import load
import hackbench
import kcompile
import cyclictest

load_modules = (hackbench, kcompile)

verbose = False
duration = 60.0
interrupted = False

def parse_options():
    global verbose, duration
    parser = optparse.OptionParser()
    parser.add_option("-d", "--duration", dest="duration",
                      type="float", 
                      help="specify length of test run in seconds")
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="store_true", default=False,
                      help="turn on verbose prints")
    (options, args) = parser.parse_args()
    verbose = options.verbose
    duration = options.duration
    return args

def debug(str):
    if verbose: print str

def prevert():
    args = parse_options()

    loads = []
    here = os.getcwd()
    dir = os.path.join(here, 'run')
    src = os.path.join(here, 'loadsource')
    
    nthreads = 0

    debug("setting up loads")
    for m in load_modules:
        loads.append(m.create(dir, src, verbose))

    debug("setting up cyclictest")
    c = cyclictest.Cyclictest(duration=duration)

    try:

        # start the cyclictest thread
        debug("starting cyclictest")
        c.start()

        # start the loads
        debug("starting loads:")
        for l in loads:
            debug("\t%s" % l.name)
            l.start()

        # now wait until they're all ready
        debug("waiting for ready from all loads")
        ready=False
        while not ready:
            for l in loads:
                ready = l.isReady()
                time.sleep(1.0)

        # start the loads
        debug("starting all loads")
        for l in loads:
            l.startevent.set()
            nthreads += 1
    

        # wait for time to expire or thread to die
        debug("waiting for duration (%f)" % duration)
        stoptime = (time.time() + duration)
        tick = duration
        while time.time() <= stoptime:
            time.sleep(1.0)
            if len(threading.enumerate()) < nthreads:
                raise RuntimeError, "load thread died!"

    except KeyboardInterrupt, e:
        pass

    finally:
        # stop cyclictest
        c.stopevent.set()

        # stop the loads
        debug("stopping all loads")
        for l in loads:
            debug("\t%s" % l.name)
            l.stopevent.set()

    c.report()

if __name__ == '__main__':
    prevert()
