#!/usr/bin/python -tt
#
#   rteval - script for evaluating platform suitability for RT Linux
#
#           This program is used to determine the suitability of
#           a system for use in a Real Time Linux environment.
#           It starts up various system loads and measures event
#           latency while the loads are running. A report is generated
#           to show the latencies encountered during the run.
#
#   Copyright 2009   Clark Williams <williams@redhat.com>
#   Copyright 2009   David Sommerseth <davids@redhat.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
#   For the avoidance of doubt the "preferred form" of this code is one which
#   is in an open unpatent encumbered format. Where cryptographic key signing
#   forms part of the process of creating an executable the information
#   including keys needed to generate an equivalently functional executable
#   are deemed to be part of the source code.
#

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
import rtevalclient
import ethtool
from datetime import datetime

sys.pathconf = "."
import load
import cyclictest
import xmlout
import dmi
import rtevalConfig

class RtEval(object):
    def __init__(self):
        self.version = "1.2"
        self.load_modules = []
        self.workdir = os.getcwd()
        self.inifile = None
        self.cmd_options = {}

        instdir = '/usr/share/rteval-%s' % self.version
        default_config = {
            'rteval': {
                'verbose'   : False,
                'keepdata'  : True,
                'debugging' : False,
                'duration'  : 60.0,
                'sysreport' : False,
                'reportdir' : None,
                'reportfile': None,
                'installdir': instdir,
                'srcdir'    : os.path.join(instdir, 'loadsource'),
                'xmlrpc'    : None
                }
            }
        self.config = rtevalConfig.rtevalConfig(default_config, logfunc=self.info)

        # read in config file info
        self.inifile = self.config.Load()

        # parse command line options
        self.parse_options()

        # if one of the command line options was a config file
        # then re-read the config info from there
        if not self.config.ConfigParsed(self.cmd_options.inifile):
            self.inifile = self.cmd_options.inifile
            self.config.Load(self.inifile)

        # copy the command line options into the rteval config section
        self.config.AppendConfig('rteval', self.cmd_options)

        self.debug("workdir: %s" % self.workdir)

        self.loads = []
        self.start = datetime.now()
        self.numcores = self.get_num_cores()
        self.memsize = self.get_memory_size()
        self.get_clocksources()
        self.xml = ''
        self.xmlreport = xmlout.XMLOut('rteval', self.version)
        self.xslt = os.path.join(self.config.installdir, "rteval_text.xsl")
        if not os.path.exists(self.xslt):
            raise RuntimeError, "can't find XSL template (%s)!" % self.xslt


    def get_num_cores(self):
        ''' figure out how many processors we have available'''
        f = open('/proc/cpuinfo')
        numcores = 0
        for line in f:
            if line.lower().startswith('processor'):
                numcores += 1
        f.close()
        self.debug("counted %d cores" % numcores)
        return numcores

    def get_memory_size(self):
        '''find out how much memory is installed'''
        f = open('/proc/meminfo')
        for l in f:
            if l.startswith('MemTotal:'):
                size = int(l.split()[1])
                f.close()
                self.debug("memory size %d" % size)
                return size
        raise RuntimeError, "can't find memtotal in /proc/meminfo!"

    def get_clocksources(self):
        '''get the available and curent clocksources for this kernel'''
        path = '/sys/devices/system/clocksource/clocksource0'
        if not os.path.exists(path):
            raise RuntimeError, "Can't find clocksource path in /sys"
        f = open (os.path.join (path, "current_clocksource"))
        self.current_clocksource = f.readline().strip()
        f = open (os.path.join (path, "available_clocksource"))
        self.available_clocksource = f.readline().strip()
        f.close()


    def parse_options(self):
        '''parse the command line arguments'''
        parser = optparse.OptionParser()
        parser.add_option("-d", "--duration", dest="duration",
                          type="string", default=self.config.duration,
                          help="specify length of test run (default: %default)")
        parser.add_option("-v", "--verbose", dest="verbose",
                          action="store_true", default=self.config.verbose,
                          help="turn on verbose prints (default: %default)")
        parser.add_option("-w", "--workdir", dest="workdir",
                          type="string", default=self.workdir,
                          help="top directory for rteval data (default: %default)")
        parser.add_option("-l", "--loaddir", dest="loaddir",
                          type="string", default=self.config.srcdir,
                          help="directory for load source tarballs (default: %default)")
        parser.add_option("-i", "--installdir", dest="installdir",
                          type="string", default=self.config.installdir,
                          help="place to locate installed templates (default: %default)")
        parser.add_option("-s", "--sysreport", dest="sysreport",
                          action="store_true", default=self.config.sysreport,
                          help='run sysreport to collect system data (default: %default)')
        parser.add_option("-D", '--debug', dest='debugging',
                          action='store_true', default=self.config.debugging,
                          help='turn on debug prints (default: %default)')
        parser.add_option("-X", '--xmlrpc-submit', dest='xmlrpc',
                          action='store', default=self.config.xmlrpc, metavar='HOST',
                          help='Hostname to XML-RPC server to submit reports')
        parser.add_option("-Z", '--summarize', dest='summarize',
                          action='store_true', default=False,
                          help='summarize an already existing XML report')
        parser.add_option("-f", "--inifile", dest="inifile",
                          type='string', default=self.inifile,
                          help="initialization file for configuring loads and behavior (default: %default)")

        (self.cmd_options, self.cmd_arguments) = parser.parse_args()
        if self.cmd_options.duration:
            mult = 1.0
            v = self.cmd_options.duration.lower()
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
            self.cmd_options.duration = float(v) * mult

    def debug(self, str):
        if self.config.debugging is True:
            print str

    def info(self, str):
        if self.config.verbose is True:
            print str

    def run_sysreport(self):
        import glob
        if os.path.exists('/usr/sbin/sosreport'):
            exe = '/usr/sbin/sosreport'
        elif os.path.exists('/usr/sbin/sysreport'):
            exe = '/usr/sbin/sysreport'
        else:
            raise RuntimeError, "Can't find sosreport/sysreport"

        self.debug("report tool: %s" % exe)
        options =  ['-k', 'rpm.rpmvma=off',
                    '--name=rteval', 
                    '--ticket=1234',
                    '--no-progressbar']

        self.info("Generating SOS report")
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

        # Retrieve configured IP addresses
        self.xmlreport.openblock('network_config')

        # Get the interface name for the IPv4 default gw
        route = open('/proc/net/route')
        defgw4 = None
        if route:
            rl = route.readline()
            while rl != '' :
                rl = route.readline()
                splt = rl.split("\t")
                if len(splt) > 2 and splt[2] != '00000000': # Only catch default route
                    defgw4 = splt[0]
                    break
            route.close()

        # Get lists over all devices, remove loopback device
        ifdevs = ethtool.get_active_devices()
        ifdevs.remove('lo')
        ifdevs.sort()

        # Make an interface tag for each device found
        for dev in ifdevs:
            self.xmlreport.openblock('interface',
                                     {'device': dev,
                                      'hwaddr': ethtool.get_hwaddr(dev)}
                                     )
            # Protcol configurations
            self.xmlreport.openblock('IPv4',
                                     {'ipaddr': ethtool.get_ipaddr(dev),
                                      'netmask': ethtool.get_netmask(dev),
                                      'defaultgw': (defgw4 == dev) and '1' or '0'}
                                     )
            self.xmlreport.closeblock()
            self.xmlreport.closeblock()
        self.xmlreport.closeblock()

        self.xmlreport.openblock('loads', {'load_average':str(accum / samples)})
        for load in self.loads:
            load.genxml(self.xmlreport)
        self.xmlreport.closeblock()
        self.cyclictest.genxml(self.xmlreport)

        # now generate the dmidecode data for this host
        d = dmi.DMIinfo(self.config.installdir)
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
        "Create a screen report, based on a predefined XSLT template"
        self.xmlreport.Write("-", self.xslt)

    def summarize(self, xmlfile):
        '''summarize a previously generated xml file'''
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
        self.reportdir = os.path.join(self.workdir,
                                      t.strftime("rteval-%Y%m%d-"+str(i)))
        while os.path.exists(self.reportdir):
            i += 1
            self.reportdir = os.path.join(self.workdir,
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


    def measure(self):
        builddir = os.path.join(self.workdir, 'rteval-build')
        if not os.path.isdir(builddir): os.mkdir(builddir)
        self.reportfile = os.path.join(self.reportdir, "summary.rpt")
        self.xml = os.path.join(self.reportdir, "summary.xml")

        # read in loads from the ini file
        self.load_modules = []
        loads = self.config.GetSection("loads")
        for l in loads:
            # hope to eventually have different kinds but module is only on
            # for now (jcw)
            if l[1].lower() == 'module':
                self.info("importing load module %s" % l[0])
                self.load_modules.append(__import__(l[0]))

        self.info("setting up loads")
        self.loads = []
        for m in self.load_modules:
            self.info("creating load instance for %s" % m.__name__)
            self.loads.append(m.create(builddir, self.config.srcdir, self.config.verbose,
                                       self.numcores, self.config.GetSection(m.__name__)))

        self.info("setting up cyclictest")
        self.cyclictest = cyclictest.Cyclictest(duration=self.config.duration,
                                                debugging=self.config.debugging)

        nthreads = 0
        try:
            # start the loads
            self.start_loads()
            
            print "started %d loads on %d cores" % (len(self.loads), self.numcores)
            print "Run duration: %d seconds" % self.config.duration
            
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
            self.info("waiting for duration (%f)" % self.config.duration)
            stoptime = (time.time() + self.config.duration)
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
        self.report()
        if self.config.sysreport:
            self.run_sysreport()

        # if --xmlrpc-submit | -X was given, send our report to this host
        if self.config.xmlrpc:
            url = "http://%s/rteval/API1/" % self.config.xmlrpc

            client = rtevalclient.rtevalclient(url)
            print "Submitting report to %s" % url
            rterid = client.SendReport(self.xmlreport.GetXMLdocument())
            print "Report registered with rterid %i" % rterid


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

    def rteval(self):
        ''' main function for rteval'''

        # if --summarize was specified then just parse the XML, print it and exit
        if self.cmd_options.summarize:
            if len(self.cmd_arguments) < 1:
                raise RuntimeError, "Must specify at least one XML file with --summarize!"
            for x in self.cmd_arguments:
                self.summarize(x)
            sys.exit(0)

        if os.getuid() != 0:
            print "Must be root to run evaluator!"
            sys.exit(-1)

        self.debug('''rteval options: 
        workdir: %s
        loaddir: %s
        verbose: %s
        debugging: %s
        duration: %f
        sysreport: %s
        inifile:  %s''' % (self.workdir, self.config.srcdir, self.config.verbose,
                           self.config.debugging, self.config.duration, self.config.sysreport,
                           self.inifile))

        if not os.path.isdir(self.workdir):
            raise RuntimeError, "work directory %d does not exist" % self.workdir

        self.make_report_dir()
        self.measure()
        self.get_dmesg()
        self.tar_results()
        

if __name__ == '__main__':
    import pwd, grp

    try:
        RtEval().rteval()
    except KeyboardInterrupt:
        sys.exit(0)
