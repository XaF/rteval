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
import signal
import glob
import tempfile
import signal
import optparse

sys.pathconf = "."
import load
import hackbench
import kcompile

load_modules = (hackbench, kcompile)

verbose = False
duration = 60.0

# prio - SCHED_FIFO priority
# threads - create more than one thread
# logfile - where to put output
# duration - how long to run

def cyclictest(prio=90, threads=None, logfile=None, duration=60.0, stopev=None):

    while True:
        startev.wait(1.0)
        if startev.isSet():
            break
        if stopev.isSet():
            print "bailing out of cyclictest before start"
            return
        
    args = '-mnv -p %d' % prio
    if threads == None:
        args += ' -t'
    else:
        args += ' -t%d' % threads

    if logfile == None:
        (loghandle, logfile) = tempfile.mkstemp()
    else:
        loghandle = os.open(logfile, os.O_RDWR)

    c = subprocess.Popen(["cyclictest", args], stdout=loghandle)

    time.sleep(duration)

    print("stopping cyclictest after %d second run" % duration)
    os.kill(c.pid, os.SIGINT)
    
    # tell the loads to stop 
    stopev.set()

    print("reducing data")
    data = os.fdopen(loghandle, 'r')
    samples = {}
    for line in data:
        (t,i,l) = line.split(':')
        array = samples.setdefault(t.strip(), [])
        array.append(l.strip())
    for k in samples.keys():
        print "thread %d: %d samples" % (k, len(samples[k]))

def parse_options():
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
        loads.append(m.create(dir, src))

    # create the cyclictst thread
    #c = threading.Thread(name="cyclictest", target=cyclictest, args=(95, None, None, 60.0, stopev,))
    
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
    stoptime = time.clock() + duration
    while time.clock() <= stoptime:
        time.sleep(0.5)
        if len(threading.enumerate()) != nthreads:
            raise RuntimeError, "load thread died!"

    # stop the loads
    debug("stopping all loads")
    for l in loads:
        debug("\t%s" % l.name)
        l.stopevent.set()

if __name__ == '__main__':
    prevert()
