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
import dmi

class RtEval(object):
    def __init__(self):
        self.version = "0.8"
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
        self.runoprofile = False
        self.loads = []
        self.topdir = os.getcwd()
        self.start = datetime.now()
        self.mydir = '/usr/share/rteval-%s' % self.version
        if not os.path.exists(self.mydir):
            self.mydir = os.path.join(self.topdir, "rteval")
        if not os.path.exists(self.mydir):
            raise RuntimeError, "Can't find rteval directory (%s)!" % self.mydir
        self.xslt = os.path.join(self.mydir, "rteval_text.xsl")
        if not os.path.exists(self.xslt):
            raise RuntimeError, "can't find XSL template (%s)!" % self.xslt
        self.loaddir = os.path.join(self.mydir, 'loadsource')
        self.tmpdir = self.find_biggest_tmp()
        self.numcores = self.get_num_cores()
        self.memsize = self.get_memory_size()
        self.get_clocksources()
        self.xml = ''
        self.xmlreport = xmlout.XMLOut('rteval', self.version)
        self.make_report_dir()

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

    def get_clocksources(self):
        path = '/sys/devices/system/clocksource/clocksource0'
        if not os.path.exists(path):
            raise RuntimeError, "Can't find clocksource path in /sys"
        f = open (os.path.join (path, "current_clocksource"))
        self.current_clocksource = f.readline().strip()
        f = open (os.path.join (path, "available_clocksource"))
        self.available_clocksource = f.readline().strip()
        f.close()

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
                          action="store_true", default=False,
                          help='run latency detector (default)')
        parser.add_option("-S", '--smi', dest='smi',
                          action="store_true", default=False,
                          help='run smi detector (not implemented)')
        parser.add_option("-D", '--debug', dest='debugging',
                          action='store_true', default=False,
                          help='turn on debug prints')
        parser.add_option("-O", '--oprofile', dest='oprofile',
                          action='store_true', default=False,
                          help='run oprofile while running evaluation (not implemented)')
        parser.add_option("-Z", '--summarize', dest='summarize',
                          action='store_true', default=False,
                          help='summarize an already existing XML report')

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

        # Start new XML report
        self.xmlreport.NewReport()

        self.xmlreport.openblock('run_info', {'days': duration.days,
                                 'hours': hours,
                                 'minutes': minutes,
                                 'seconds': seconds})
        self.xmlreport.taggedvalue('date', self.start.strftime('%Y-%m-%d'))
        self.xmlreport.taggedvalue('time', self.start.strftime('%H:%M:%S'))
        self.xmlreport.closeblock()
        self.xmlreport.openblock('uname')
        self.xmlreport.taggedvalue('node', node)
        isrt = 1
        if ver.find(' RT ') == -1:
            isrt = 0
        self.xmlreport.taggedvalue('kernel', release, {'is_RT':isrt})
        self.xmlreport.taggedvalue('arch', machine)
        self.xmlreport.closeblock()

        self.xmlreport.openblock("clocksource")
        self.xmlreport.taggedvalue('current', self.current_clocksource)
        self.xmlreport.taggedvalue('available', self.available_clocksource)
        self.xmlreport.closeblock()
        
        self.xmlreport.openblock('hardware')
        self.xmlreport.taggedvalue('cpu_cores', self.numcores)
        self.xmlreport.taggedvalue('memory_size', self.memsize)
        self.xmlreport.closeblock()


        self.xmlreport.openblock('loads', {'load_average':str(accum / samples)})
        for load in self.loads:
            load.genxml(self.xmlreport)
        self.xmlreport.closeblock()
        self.cyclictest.genxml(self.xmlreport)

        # now generate the dmidecode data for this host
        d = dmi.DMIinfo()
        d.genxml(self.xmlreport)
        
        # Close the report - prepare for return the result
        self.xmlreport.close()

        # Write XML (or write XSLT parsed XML if xslt != None)
        if self.xml != None:
            self.xmlreport.Write(self.xml, xslt)
        else:
            # If no file is set, use stdout
            self.xmlreport.Write("-", xslt) # libxml2 defines a filename as "-" to be stdout


    def report(self):
        self.xmlreport.Write("-", self.xslt)

    def summarize(self, xmlfile):
        print "loading %s for summarizing" % xmlfile
        self.xmlreport.LoadReport(xmlfile)
        self.xmlreport.Write('-', self.xslt)

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

    def get_dmesg(self):
        dpath = "/var/log/dmesg"
        if not os.path.exists(dpath):
            print "dmesg file not found at %s" % dpath
            return
        shutil.copyfile(dpath, os.path.join(self.reportdir, "dmesg"))

    def measure_latency(self):
        builddir = os.path.join(self.tmpdir, 'rteval-build')
        if not os.path.isdir(builddir): os.mkdir(builddir)
        self.reportfile = os.path.join(self.reportdir, "summary.rpt")
        self.xml = os.path.join(self.reportdir, "summary.xml")

        nthreads = 0

        print "setting up loads"
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
        self.genxml(duration, accum, samples)
        shutil.move(self.cyclictest.outfile, self.reportdir)
        self.report()
        if self.sysreport:
            self.run_sysreport()

    def tar_results(self):
        if not os.path.isdir(self.reportdir):
            raise RuntimeError, "no such directory: %s" % self.reportdir
        import tarfile
        dirname = os.path.dirname(self.reportdir)
        rptdir = os.path.basename(self.reportdir)
        cwd = os.getcwd()
        os.chdir(dirname)
        try:
            t = tarfile.open(rptdir + ".tar.bz2", "w:bz2")
            t.add(rptdir)
            t.close()
        except:
            os.chdir(cwd)

    def oprofile_setup(self):
        if self.runoprofile == False:
            return
        rel = os.uname()[2]
        vmlinux = os.path.join('/usr/lib/debug/lib/modules', rel)
        if not os.path.exists(vmlinux):
            print "Can't run oprofile. Load kernel-rt-debuginfo packages."
            return
        ret = subprocess.call(['opcontrol', '--init'])
        if ret:
            print "failed to run opcontrol --init! is oprofile installed?"
            return
        ret = subprocess.call(['opcontrol', '--vmlinux=%s' % vmlinux])
        if ret:
            print "opcontrol failed to set vmlinux image: %s" % vmlinux
            return

    def rteval(self):
        (opts, args) = self.parse_options()
        workdir  = opts.workdir
        self.loaddir  = opts.loaddir
        self.verbose  = opts.verbose
        self.debugging = opts.debugging
        self.duration = opts.duration
        self.sysreport = opts.sysreport

        # if --summarize was specified then just parse the XML, print it and exit
        if opts.summarize:
            if len(args) < 1:
                raise RuntimeError, "Must specify at least one XML file with --summarize!"
            for x in args:
                self.summarize(x)
            sys.exit(0)

        if os.getuid() != 0:
            raise RuntimeError, "Must be root to run evaluator!"

        self.debug('''rteval options: 
        workdir: %s
        loaddir: %s
        verbose: %s
        debugging: %s
        duration: %f
        sysreport: %s''' % (workdir, self.loaddir, self.verbose, 
                            self.debugging, self.duration, self.sysreport))

        if not os.path.isdir(workdir):
            raise RuntimeError, "work directory %d does not exist" % workdir

        if workdir != self.topdir:
            self.topdir = workdir

        if self.runlatency: 
            self.measure_latency()
            self.get_dmesg()
            self.tar_results()
        

if __name__ == '__main__':
    import pwd, grp

    try:
        RtEval().rteval()
    except KeyboardInterrupt:
        sys.exit(0)
