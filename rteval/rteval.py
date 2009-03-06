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
import xmlout

class RtEval(object):
    def __init__(self):
        self.version = "0.6"
        self.load_modules = (hackbench, kcompile)
        self.keepdata = True
        self.verbose = False
        self.debugging = False
        self.duration = 60.0
        self.interrupted = False
        self.sysreport = False
        self.reportdir = None
        self.reportfile = None
        self.runlatency = True
        self.runsmi = False
        self.loads = []
        self.start = datetime.now()
        self.loaddir = "/usr/share/rteval-%s/loadsource" % self.version
        self.tmpdir = self.find_biggest_tmp()
        self.topdir = os.getcwd()
        self.numcores = self.get_num_cores()
        self.memsize = self.get_memory_size()

    def find_biggest_tmp(self):
        dir = ''
        avail = 0;
        for d in ('/tmp', '/var/tmp', '/usr/tmp'):
            a = os.statvfs(d)[statvfs.F_BAVAIL]
            if a > avail:
                dir = d
                avail = a
                self.debug("using tmp dir: %s\n" % dir)
        return dir


    def get_num_cores(self):
        f = open('/proc/cpuinfo')
        numcores = 0
        for line in f:
            if line.startswith('processor'):
                numcores += 1
        f.close()
        self.debug("counted %d cores\n" % numcores)
        return numcores

    def get_memory_size(self):
        f = open('/proc/meminfo')
        for l in f:
            if l.startswith('MemTotal:'):
                size = int(l.split()[1])
                f.close()
                self.debug("memory size %d\n" % size)
                return size
        raise RuntimeError, "can't find memtotal in /proc/meminfo!"

    def parse_options(self):
        parser = optparse.OptionParser()
        parser.add_option("-d", "--duration", dest="duration",
                          type="string", default=str(self.duration),
                          help="specify length of test run")
        parser.add_option("-v", "--verbose", dest="verbose",
                          action="store_true", default=False,
                          help="turn on verbose prints")
        parser.add_option("-w", "--workdir", dest="workdir",
                          type="string", default=self.topdir,
                          help="top directory for rteval data")
        parser.add_option("-l", "--loaddir", dest="loaddir",
                          type="string", default=self.loaddir,
                          help="top directory for rteval data")
        parser.add_option("-s", "--sysreport", dest="sysreport",
                          action="store_true", default=False,
                          help='run sysreport to collect system data')
        parser.add_option("-L", '--latency', dest='latency',
                          action="store_true", default=False)
        parser.add_option("-S", '--smi', dest='smi',
                          action="store_true", default=False)
        parser.add_option("-D", '--debug', dest='debugging',
                          action='store_true', default=False)

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
        if options.latency == False and options.smi == False:
            options.latency = True
        return (options, args)

    def debug(self, str):
        if self.debugging: print 

    def info(self, str):
        if self.verbose: print str

    def run_sysreport(self):
        import glob
        if os.path.exists('/usr/sbin/sosreport'):
            exe = '/usr/sbin/sosreport'
        elif os.path.exists('/usr/sbin/sysreport'):
            exe = '/usr/sbin/sysreport'
        else:
            raise RuntimeError, "Can't find sosreport/sysreport"

        self.debug("report tool: %s\n" % exe)
        options =  ['-k', 'rpm.rpmvma=off',
                    '--name=rteval', 
                    '--ticket=1234',
                    '--no-progressbar']

        print "Generating SOS report"
        subprocess.call([exe] + options)
        for s in glob.glob('/tmp/s?sreport-rteval-*'):
            shutil.move(s, self.reportdir)
    

    def genxml(self, duration, accum, samples, xslt = None):
        seconds = duration.seconds
        hours = seconds / 3600
        if hours: seconds -= (hours * 3600)
        minutes = seconds / 60
        if minutes: seconds -= (minutes * 60)
        (sys, node, release, ver, machine) = os.uname()

        indent = 0
        x = xmlout.XMLOut('rteval', {'version':self.version})
        x.openblock('run_info', {'days': duration.days,
                                 'hours': hours,
                                 'minutes': minutes,
                                 'seconds': seconds})
        x.taggedvalue('date', self.start.strftime('%Y-%m-%d'))
        x.taggedvalue('time', self.start.strftime('%H:%M:%S'))
        x.closeblock()
        x.openblock('uname')
        x.taggedvalue('node', node)
        isrt = 1
        if ver.find(' RT ') == -1:
            isrt = 0
        x.taggedvalue('kernel', release, {'is_RT':isrt})
        x.taggedvalue('arch', machine)
        x.closeblock()

        x.openblock('hardware')
        x.taggedvalue('cpu_cores', self.numcores)
        x.taggedvalue('memory_size', self.memsize)
        x.closeblock()


        x.openblock('loads', {'load_average':str(accum / samples)})
        for load in self.loads:
            load.genxml(x)
        x.closeblock()
        self.cyclictest.genxml(x)
        x.closeblock()
        x.close()

        # Write XML (or write XSLT parsed XML if xslt != None)
        if self.xml != None:
            x.Write(dstfile, xslt)
        else:
            # If no file is set, use stdout
            x.Write("-", xslt) # libxml2 defines a filename as "-" to be stdout
        
    def report(self):
        r = open(self.reportfile, "r")
        for l in r:
            print l[:-1]

    def start_loads(self):
        if len(self.loads) == 0:
            raise RuntimeError, "start_loads: No loads defined!"
        self.info ("starting loads:")
        for l in self.loads:
            l.start()
        # now wait until they're all ready
        self.info("waiting for ready from all loads")
        ready=False
        while not ready:
            busy = 0
            for l in self.loads:
                self.debug("checking load: %s" % l.name)
                if not l.isAlive():
                    raise RuntimeError, "%s died" % l.name
                if not l.isReady():
                    busy += 1
                    self.debug("%s is busy" % l.name)
            if busy:
                time.sleep(1.0)
            else:
                ready = True

    def stop_loads(self):
        if len(self.loads) == 0:
            raise RuntimeError, "stop_loads: No loads defined!"
        self.info("stopping loads: ")
        for l in self.loads:
            self.info("\t%s" % l.name)
            l.stopevent.set()
            l.join(2.0)

    def make_report_dir(self):
        t = self.start
        i = 1
        self.reportdir = os.path.join(self.topdir,
                                      t.strftime("rteval-%Y%m%d-"+str(i)))
        while os.path.exists(self.reportdir):
            i += 1
            self.reportdir = os.path.join(self.topdir,
                                          t.strftime('rteval-%Y%m%d-'+str(i)))
        if not os.path.isdir(self.reportdir): 
            os.mkdir(self.reportdir)
        return self.reportdir

    def measure_latency(self):
        builddir = os.path.join(self.tmpdir, 'rteval-build')
        if not os.path.isdir(builddir): os.mkdir(builddir)
        self.make_report_dir()
        self.reportfile = os.path.join(self.reportdir, "latency.rpt")
        self.xml = os.path.join(self.reportdir, "latency.xml")

        nthreads = 0

        self.info("setting up loads")
        self.loads = []
        for m in self.load_modules:
            self.loads.append(m.create(builddir, self.loaddir, self.verbose, self.numcores))

        self.info("setting up cyclictest")
        self.cyclictest = cyclictest.Cyclictest(duration=self.duration, debugging=self.debugging)

        try:
            # start the loads
            self.start_loads()
            
            print "started %d loads on %d cores" % (len(self.loads), self.numcores)
            print "Run duration: %d seconds" % self.duration
            
            start = datetime.now()
            
            # start the cyclictest thread
            self.info("starting cyclictest")
            self.cyclictest.start()
            
            # turn loose the loads
            self.info("sending start event to all loads")
            for l in self.loads:
                l.startevent.set()
                nthreads += 1
                

            # open the loadavg /proc entry
            p = open("/proc/loadavg")
            accum = 0.0
            samples = 0

            # wait for time to expire or thread to die
            self.info("waiting for duration (%f)" % self.duration)
            stoptime = (time.time() + self.duration)
            while time.time() <= stoptime:
                time.sleep(1.0)
                if not self.cyclictest.isAlive():
                    raise RuntimeError, "cyclictest thread died!"
                if len(threading.enumerate()) < nthreads:
                    raise RuntimeError, "load thread died!"
                p.seek(0)
                accum += float(p.readline().split()[0])
                samples += 1
                
        finally:
            # stop cyclictest
            self.cyclictest.stopevent.set()
            
        # stop the loads
            self.stop_loads()

        end = datetime.now()
        duration = end - start
#        self.report(duration, accum, samples)
#        shutil.move(self.cyclictest.outfile, self.reportdir)
        self.genxml(duration, accum, samples)

        if self.sysreport:
            self.run_sysreport()


    def rteval(self):
        (opts, args) = self.parse_options()
        workdir  = opts.workdir
        self.loaddir  = opts.loaddir
        self.verbose  = opts.verbose
        self.debugging = opts.debugging
        self.duration = opts.duration
        self.sysreport = opts.sysreport

        if self.sysreport and os.getuid() != 0:
            raise RuntimeError, "Must be root to get a sysreport"

        self.debug('''rteval options: 
        workdir: %s
        loaddir: %s
        verbose: %s
        debugging: %s
        duration: %f
        sysreport: %s''' % (workdir, self.loaddir, self.verbose, self.debugging, self.duration, self.sysreport))

        if not os.path.isdir(workdir):
            raise RuntimeError, "work directory %d does not exist" % workdir

        if (workdir != self.topdir):
            self.topdir = workdir

        if self.runlatency: self.measure_latency()


if __name__ == '__main__':
    import pwd, grp
    if os.getuid():
        login = pwd.getpwuid(os.getuid())[0]
        try:
           if not login in grp.getgrnam('realtime')[3]:
               raise RuntimeError, "must be root or a member of the 'realtime' group"
        except:
            raise RuntimeError, "realtime group does not exist! (please install rt-setup package)"
    try:
        RtEval().rteval()
    except KeyboardInterrupt:
        sys.exit(0)
