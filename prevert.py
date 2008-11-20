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

sys.pathconf = "."
import load
import hackbench
import kcompile

load_modules = (hackbench, kcompile)

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

def prevert():
    loads = []
    here = os.getcwd()
    dir = os.path.join(here, 'run')
    src = os.path.join(here, 'loadsource')
    
    for m in load_modules:
        loads.append(m.create(dir, src))

    # create the cyclictst thread
    #c = threading.Thread(name="cyclictest", target=cyclictest, args=(95, None, None, 60.0, stopev,))
    
    # start the loads
    for l in loads:
        l.start()

    # now wait until they're all ready
    ready=False
    while not ready:
        for l in loads:
            ready = l.isReady()
        time.sleep(1.0)

    # start the loads
    for l in loads:
        l.startevent.set()

    time.sleep(60.0)

    # stop the loads
    for l in loads:
        l.stopevent.set()

    
if __name__ == '__main__':
    prevert()
