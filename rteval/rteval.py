#!/usr/bin/python -tt
#
# rteval  - script for evaluating platform suitability for RT Linux
#
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
import tempfile
import statvfs
import shutil
from datetime import datetime

sys.pathconf = "."
import load
import hackbench
import kcompile
import cyclictest

version = "0.4"

load_modules = (hackbench, kcompile)

deftmpdirs = ('/tmp', '/var/tmp', '/usr/tmp')

loaddir = "/usr/share/rteval-%s/loadsource" % version
builddir = None
keepdata = False
verbose = False
debugging = False
duration = 60.0
interrupted = False
sysreport = False
reportdir  = None
reportfile = None

def get_num_cores():
    f = open('/proc/cpuinfo')
    numcores = 0
    for line in f:
        if line.startswith('processor'):
            numcores += 1
    f.close()
    debug("counted %d cores\n" % numcores)
    return numcores

def get_memory_size():
    f = open('/proc/meminfo')
    for l in f:
        if l.startswith('MemTotal:'):
            size = int(l.split()[1])
            f.close()
            debug("memory size %d\n" % size)
            return size
    raise RuntimeError, "can't find memtotal in /proc/meminfo!"

def parse_options(tmpdir):
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
    parser.add_option("-w", "--workdir", dest="workdir",
                      type="string", default=tmpdir,
                      help="top directory for rteval data")
    parser.add_option("-l", "--loaddir", dest="loaddir",
                      type="string", default=loaddir,
                      help="top directory for rteval data")
    parser.add_option("-s", "--sysreport", dest="sysreport",
                      action="store_true", default=False,
                      help='run sysreport to collect system data')
    
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
    if debugging: print str

def info(str):
    if verbose: print str

def run_sysreport():
    global reportdir
    import glob
    if os.path.exists('/usr/sbin/sosreport'):
        exe = '/usr/sbin/sosreport'
    elif os.path.exists('/usr/sbin/sysreport'):
        exe = '/usr/sbin/sysreport'
    else:
        raise RuntimeError, "Can't find sosreport/sysreport"

    debug("report tool: %s\n" % exe)
    options =  ['-k', 'rpm.rpmvma=off',
                '--name=rteval', 
                '--ticket=1234',
                '--no-progressbar']

    print "Generating SOS report"
    subprocess.call([exe] + options)
    for s in glob.glob('/tmp/s?sreport-rteval-*'):
        shutil.move(s, reportdir)
    

def find_biggest_tmp():
    dir = ''
    avail = 0;

    for d in deftmpdirs:
        a = os.statvfs(d)[statvfs.F_BAVAIL]
        if a > avail:
            dir = d
            avail = a
    debug("using tmp dir: %s\n" % dir)
    return dir

def report(duration, loads, cyclictest, accum, samples):
    global reportfile, version

    seconds = duration.seconds
    hours = seconds / 3600
    if hours: seconds -= (hours * 3600)
    minutes = seconds / 60
    if minutes: seconds -= (minutes * 60)

    (sys, node, release, ver, machine) = os.uname()
    r = open(reportfile, "w")
    r.write('%s\n' % ('-' * 72))
    r.write(' rteval version %s\n' % version)
    r.write(' Node: %s\n' % node)
    r.write(' Kernel: %s\n' % release)
    r.write(' Arch: %s\n' % machine)
    r.write(' Memory: %0.2fGB\n' % (get_memory_size() / 1024.0 / 1024.0))
    if ver.find(' RT ') == -1:
        r.write(' ******* NOT AN RT KERNEL! ********\n')
    r.write(' Run Length: %d days %d hours, %d minutes, %d seconds\n' % 
            (duration.days, hours, minutes, seconds))
    r.write(' Average Load Average during run: %0.2f (%d samples)\n' % (accum / samples, samples))
    r.write('\nLoad Command lines:\n')
    for l in loads:
        l.report(r)
    cyclictest.report(r)
    r.write('%s\n' % ('-' * 72))
    r.close()
    r = open(reportfile, "r")
    for l in r:
        print l[:-1]


def start_loads(loads):
    info ("starting loads:")
    for l in loads:
	l.start()
    # now wait until they're all ready
    info("waiting for ready from all loads")
    ready=False
    while not ready:
        busy = 0
        for l in loads:
            debug("checking load: %s" % l.name)
            if not l.isAlive():
                raise RuntimeError, "%s died" % l.name
            if not l.isReady():
                busy += 1
                debug("%s is busy" % l.name)
        if busy:
            time.sleep(1.0)
        else:
            ready = True

def stop_loads(loads):
    info("stopping loads: ")
    for l in loads:
        info("\t%s" % l.name)
	l.stopevent.set()
	l.join(2.0)
	
def measure_latency(topdir):
    global loaddir, verbose, duration, keepdata, builddir, sysreport, reportfile

    builddir= os.path.join(topdir, 'build')
    if not os.path.isdir(builddir): os.mkdir(builddir)
    reportdir = os.path.join(topdir, 'reports')
    if not os.path.isdir(reportdir): os.mkdir(reportdir)
    reportfile = os.path.join(reportdir, "latency.rpt")
    num_cpu_cores = get_num_cores()

    nthreads = 0

    info("setting up loads")
    loads = []
    for m in load_modules:
        loads.append(m.create(builddir, loaddir, verbose, num_cpu_cores))

    info("setting up cyclictest")
    c = cyclictest.Cyclictest(duration=duration, debugging=verbose, keepdata=keepdata)

    try:
        # start the loads
	start_loads(loads)

        print "started %d loads on %d cores" % (len(loads), num_cpu_cores)
        print "Run duration: %d seconds" % duration

        start = datetime.now()

        # start the cyclictest thread
        info("starting cyclictest")
        c.start()

        # turn loose the loads
        info("sending start event to all loads")
        for l in loads:
            l.startevent.set()
            nthreads += 1
    

        # open the loadavg /proc entry
        p = open("/proc/loadavg")
        accum = 0.0
        samples = 0

        # wait for time to expire or thread to die
        info("waiting for duration (%f)" % duration)
        stoptime = (time.time() + duration)
        tick = duration
        while time.time() <= stoptime:
            time.sleep(1.0)
            if not c.isAlive():
                raise RuntimeError, "cyclictest thread died!"
            if len(threading.enumerate()) < nthreads:
                raise RuntimeError, "load thread died!"
            p.seek(0)
            accum += float(p.readline().split()[0])
            samples += 1

    finally:
        # stop cyclictest
        c.stopevent.set()

        # stop the loads
	stop_loads(loads)

    end = datetime.now()
    duration = end - start
    report(duration, loads, c, accum, samples)
    if keepdata:
        shutil.move(c.outfile, reportdir)

    if sysreport:
        run_sysreport()


def rteval():
    global loaddir, verbose, duration, keepdata, builddir, sysreport

    tmpdir = find_biggest_tmp()

    (opts, args) = parse_options(tmpdir)
    workdir  = opts.workdir
    loaddir  = opts.loaddir
    verbose  = opts.verbose
    duration = opts.duration
    keepdata = opts.keepdata
    sysreport = opts.sysreport

    if sysreport and os.getuid() != 0:
        raise RuntimeError, "Must be root to get a sysreport"

    debug('''rteval options: 
        workdir: %s
        loaddir: %s
        verbose: %s
        duration: %f
        keepdata: %s
        sysreport: %s''' % (workdir, loaddir,verbose, duration, 
                            keepdata, sysreport))

    if not os.path.isdir(workdir):
        raise RuntimeError, "work directory %d does not exist" % workdir

    if (workdir == tmpdir):
        topdir = tempfile.mkdtemp(prefix='rteval-', dir=workdir)
    else:
        topdir = workdir

    measure_latency(topdir)



if __name__ == '__main__':
    import pwd, grp
    if os.getuid():
        login = pwd.getpwuid(os.getuid())[0]
        try:
           if not login in grp.getgrnam('realtime')[3]:
               raise RuntimeError, "must be root or member of 'realtime' group"
        except:
            raise RuntimeError, "realtime group does not exist!"
    try:
        rteval()
    except KeyboardInterrupt:
        sys.exit(0)
