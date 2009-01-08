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
import optparse
from datetime import datetime

sys.pathconf = "."
import load
import hackbench
import kcompile
import cyclictest

version = "0.2"

load_modules = (hackbench, kcompile)

defbuilddirs = ('/tmp', '/var/tmp', '/usr/tmp')

loaddir = "/usr/share/prevert-%s/loadsource" % version
builddir = None
keepdata = False
verbose = False
duration = 60.0
interrupted = False
sysreport = False
reportfile = 'prevert.rpt'

def get_num_cores():
    f = open('/proc/cpuinfo')
    numcores = 0
    for line in f:
        if line.startswith('processor'):
            numcores += 1
    f.close()
    return numcores

def parse_options():
    parser = optparse.OptionParser()
    parser.add_option("-d", "--duration", dest="duration",
                      type="string", default="120",
                      help="specify length of test run")
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="store_true", default=False,
                      help="turn on verbose prints")
    parser.add_option("-k", "--keepdata", dest="keepdata",
                      action="store_true", default=False,
                      help="keep measurement data")
    parser.add_option("-b", "--builddir", dest="builddir",
                      type="string", default=None,
                      help="directory for unpacking and building loads")
    parser.add_option("-l", "--loaddir", dest="loaddir",
                      type="string", default=loaddir,
                      help="directory for finding loads source")
    parser.add_option("-s", "--sysreport", dest="sysreport",
                      action="store_true", default=False,
                      help='run sysreport to collect system data')
    parser.add_option("-r", "--report", dest="reportfile",
                      type="string", default="prevert.rpt")
    (options, args) = parser.parse_args()
    if options.duration:
        mult = 1.0
        v = options.duration.lower()
        if v.endswith('s'):
            v = v[:-1]
        elif v.endswith('m'):
            v = v[:-1]
            mult = 60.0
        elif v.endswith('h'):
            v = v[:-1]
            mult = 3600.0
        elif v.endswith('d'):
            v = v[:-1]
            mult = 3600.0 * 24.0
        options.duration = float(v) * mult
    return (options, args)

def debug(str):
    if verbose: print str

def setup_builddir(dir):
    if dir == None:
        for d in defbuilddirs:
            if os.path.exists(d):
                dir = os.path.join(d, 'prevert-builddir')
                if not os.path.exists(dir): os.mkdir(dir)
                break
    debug("build dir: %s" % dir)
    return dir

def prevert():
    global loaddir, verbose, duration, keepdata, builddir

    (opts, args) = parse_options()

    loaddir  = opts.loaddir
    verbose  = opts.verbose
    duration = opts.duration
    keepdata = opts.keepdata
    reportfile = opts.reportfile

    builddir = setup_builddir(opts.builddir)

    num_cpu_cores = get_num_cores()

    nthreads = 0

    debug("setting up loads")
    loads = []
    for m in load_modules:
        loads.append(m.create(builddir, loaddir, verbose, num_cpu_cores))

    debug("setting up cyclictest")
    c = cyclictest.Cyclictest(duration=duration, debugging=verbose, keepdata=keepdata)

    try:

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

        print "starting %d loads on %d cores" % (len(loads), num_cpu_cores)
        print "Run duration: %d seconds" % duration

        start = datetime.now()

        # start the cyclictest thread
        debug("starting cyclictest")
        c.start()

        # turn loose the loads
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

    finally:
        # stop cyclictest
        c.stopevent.set()

        # stop the loads
        debug("stopping all loads")
        for l in loads:
            debug("\t%s" % l.name)
            l.stopevent.set()
    end = datetime.now()
    d = end - start
    hours = d.seconds / 3600
    if hours: d.seconds -= (hours * 3600)
    minutes = d.seconds / 60
    if minutes: d.seconds -= (minutes * 60)

    (sys, node, release, ver, machine) = os.uname()
    r = open(reportfile, "w")
    r.write('%s\n' % ('-' * 72))
    r.write(' Prevert version %s\n' % version)
    r.write(' Node: %s\n' % node)
    r.write(' Kernel: %s\n' % release)
    r.write(' Arch: %s\n' % machine)
    if ver.find(' RT ') == -1:
        r.write(' ******* NOT AN RT KERNEL! ********\n')
    r.write(' Run Length: %d days %d hours, %d minutes, %d seconds\n' % 
            (d.days, hours, minutes, d.seconds))
    c.report(r)
    r.write('%s\n' % ('-' * 72))

    if sysreport:
        print "generating sysreport"
        subprocess.call(['/usr/sbin/sysreport', '-dmidecode'])

if __name__ == '__main__':
    prevert()
