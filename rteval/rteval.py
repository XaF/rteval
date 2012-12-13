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
#   Copyright 2009,2010,2011,2012   Clark Williams <williams@redhat.com>
#   Copyright 2009,2010,2011,2012   David Sommerseth <davids@redhat.com>
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
import time
import threading
import optparse
import tempfile
import signal
from datetime import datetime
from distutils import sysconfig
from Log import Log
from sysinfo import SystemInfo
from modules.loads import LoadModules
from modules.measurement import MeasurementModules, MeasurementProfile
from rtevalReport import rtevalReport
from rtevalXMLRPC import rtevalXMLRPC

# put local path at start of list to overide installed methods
sys.path.insert(0, "./rteval")
import rtevalConfig
import rtevalMailer


sigint_received = False
def sigint_handler(signum, frame):
    global sigint_received
    sigint_received = True
    print "*** SIGINT received - stopping rteval run ***"

def sigterm_handler(signum, frame):
    raise RuntimeError,  "SIGTERM received!"

class RtEval(rtevalReport):
    def __init__(self, cmdargs):
        self.__version = "2.0_pre"
        self.__workdir = os.getcwd()
        self.__reportdir = None
        self.__inifile = None
        self.__cmd_opts = {}

        default_config = {
            'rteval': {
                'quiet'      : False,
                'verbose'    : False,
                'keepdata'   : True,
                'debugging'  : False,
                'duration'   : '60',
                'sysreport'  : False,
                'reportdir'  : None,
                'reportfile' : None,
                'installdir' : '/usr/share/rteval',
                'srcdir'     : '/usr/share/rteval/loadsource',
                'xmlrpc'     : None,
                'xslt_report': '/usr/share/rteval/rteval_text.xsl',
                'report_interval': '600',
                'logging'    : False,
                },
           'loads' : {
                'kcompile'   : 'module',
                'hackbench'  : 'module',
                },
            'kcompile' : {
                'source'     : 'linux-2.6.21.tar.bz2',
                'jobspercore': '2',
                },
            'hackbench' : {
                'source'     : 'hackbench.tar.bz2',
                'jobspercore': '5',
                },
            'cyclictest' : {
                'interval' : '100',
                'buckets'  : '2000',
                'distance' : '25',
                },
            'measurement' : {
                'cyclictest' : 'module',
                }
            }

        # Prepare logging
        self.__logger = Log()
        self.__logger.SetLogVerbosity(Log.INFO)

        # setup initial configuration
        self.__cfg = rtevalConfig.rtevalConfig(default_config, logger=self.__logger)

        # parse command line options
        self.parse_options(cmdargs)

        # read in config file info
        self.__inifile = self.__cfg.Load(self.__cmd_opts.inifile)

        # copy the command line options into the rteval config section
        # (cmd line overrides config file values)
        self.__cfg.AppendConfig('rteval', self.__cmd_opts)

        # Update log level, based on config/command line args
        loglev = (not self.__cfg.quiet and (Log.ERR | Log.WARN)) \
            | (self.__cfg.verbose and Log.INFO) \
            | (self.__cfg.debugging and Log.DEBUG)
        self.__logger.SetLogVerbosity(loglev)

        self.__logger.log(Log.DEBUG, "workdir: %s" % self.__workdir)

        # prepare a mailer, if that's configured
        if self.__cfg.HasSection('smtp'):
            self.__mailer = rtevalMailer.rtevalMailer(self.__cfg.GetSection('smtp'))
        else:
            self.__mailer = None

        self._sysinfo = SystemInfo(self.__cfg, logger=self.__logger)
        self._loadmods = LoadModules(self.__cfg, logger=self.__logger)
        self._measuremods = MeasurementModules(self.__cfg, logger=self.__logger)

        if not self.__cfg.xslt_report.startswith(self.__cfg.installdir):
            self.__cfg.xslt_report = os.path.join(self.__cfg.installdir, "rteval_text.xsl")

        if not os.path.exists(self.__cfg.xslt_report):
            raise RuntimeError, "can't find XSL template (%s)!" % self.__cfg.xslt_report

        # Add rteval directory into module search path
        sys.path.insert(0, '%s/rteval' % sysconfig.get_python_lib())

        # Initialise the report module
        rtevalReport.__init__(self, self.__version, self.__cfg.installdir, self.__cmd_opts.annotate)

        # If --xmlrpc-submit is given, check that we can access the server
        if self.__cfg.xmlrpc:
            self.__xmlrpc = rtevalXMLRPC(self.__cfg.xmlrpc, self.__logger, self.__mailer)
            if not self.__xmlrpc.Ping():
                if not self.__cmd_opts.xmlrpc_noabort:
                    print "ERROR: Could not reach XML-RPC server '%s'.  Aborting." % self.__cfg.xmlrpc
                    sys.exit(2)
                else:
                    print "WARNING: Could not ping the XML-RPC server.  Will continue anyway."
        else:
            self.__xmlrpc = None


    def parse_options(self, cmdargs):
        '''parse the command line arguments'''
        parser = optparse.OptionParser()
        parser.add_option("-d", "--duration", dest="duration",
                          type="string", default=self.__cfg.duration,
                          help="specify length of test run (default: %default)")
        parser.add_option("-v", "--verbose", dest="verbose",
                          action="store_true", default=self.__cfg.verbose,
                          help="turn on verbose prints (default: %default)")
        parser.add_option("-w", "--workdir", dest="workdir",
                          type="string", default=self.__workdir,
                          help="top directory for rteval data (default: %default)")
        parser.add_option("-l", "--loaddir", dest="srcdir",
                          type="string", default=self.__cfg.srcdir,
                          help="directory for load source tarballs (default: %default)")
        parser.add_option("-i", "--installdir", dest="installdir",
                          type="string", default=self.__cfg.installdir,
                          help="place to locate installed templates (default: %default)")
        parser.add_option("-s", "--sysreport", dest="sysreport",
                          action="store_true", default=self.__cfg.sysreport,
                          help='run sysreport to collect system data (default: %default)')
        parser.add_option("-D", '--debug', dest='debugging',
                          action='store_true', default=self.__cfg.debugging,
                          help='turn on debug prints (default: %default)')
        parser.add_option("-X", '--xmlrpc-submit', dest='xmlrpc',
                          action='store', default=self.__cfg.xmlrpc, metavar='HOST',
                          help='Hostname to XML-RPC server to submit reports')
        parser.add_option("-P", "--xmlrpc-no-abort", dest="xmlrpc_noabort",
                          action='store_true', default=False,
                          help="Do not abort if XML-RPC server do not respond to ping request");
        parser.add_option("-Z", '--summarize', dest='summarize',
                          action='store_true', default=False,
                          help='summarize an already existing XML report')
        parser.add_option("-H", '--raw-histogram', dest='rawhistogram',
                          action='store_true', default=False,
                          help='Generate raw histogram data for an already existing XML report')
        parser.add_option("-f", "--inifile", dest="inifile",
                          type='string', default=None,
                          help="initialization file for configuring loads and behavior")
        parser.add_option("-a", "--annotate", dest="annotate",
                          type="string", default=None,
                          help="Add a little annotation which is stored in the report")
        parser.add_option("-L", "--logging", dest="logging",
                         action='store_true', default=False,
                         help='log the output of the loads in the report directory')

        parser.add_option("-O", "--onlyload", dest="onlyload",
                          action='store_true', default=False,
                          help="only run the loads (don't run measurement threads)")

        (self.__cmd_opts, self.__cmd_args) = parser.parse_args(args = cmdargs)
        if self.__cmd_opts.duration:
            mult = 1.0
            v = self.__cmd_opts.duration.lower()
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
            self.__cmd_opts.duration = float(v) * mult
        self.__workdir = os.path.abspath(self.__cmd_opts.workdir)
    

    def show_remaining_time(self, remaining):
        r = int(remaining)
        days = r / 86400
        if days: r = r - (days * 86400)
        hours = r / 3600
        if hours: r = r - (hours * 3600)
        minutes = r / 60
        if minutes: r = r - (minutes * 60)
        print "rteval time remaining: %d days, %d hours, %d minutes, %d seconds" % (days, hours, minutes, r)


    def prepare(self, onlyload = False):
        builddir = os.path.join(self.__workdir, 'rteval-build')
        if not os.path.isdir(builddir): os.mkdir(builddir)

        # create our report directory
        try:
            # Only create a report dir if we're doing measurements
            # or the loads logging is enabled
            if not onlyload or self.__cfg.logging:
                self.__reportdir = self._make_report_dir(self.__workdir, "summary.xml")
        except Exception, e:
            raise RuntimeError("Cannot create report directory (NFS with rootsquash on?) [%s]", str(e))

        self.__logger.log(Log.INFO, "Preparing load modules")
        params = {'workdir':self.__workdir,
                  'reportdir':self.__reportdir,
                  'builddir':builddir,
                  'srcdir':self.__cfg.srcdir,
                  'verbose': self.__cfg.verbose,
                  'debugging': self.__cfg.debugging,
                  'numcores':self._sysinfo.cpu_getCores(True),
                  'logging':self.__cfg.logging,
                  'memsize':self._sysinfo.mem_get_size(),
                  'numanodes':self._sysinfo.mem_get_numa_nodes(),
                  'duration':self.__cfg.duration,
                  }
        self._loadmods.Setup(params)

        self.__logger.log(Log.INFO, "Preparing measurement modules")
        self._measuremods.Setup(params)


    def measure(self, measure_profile):
        if not isinstance(measure_profile, MeasurementProfile):
            raise Exception("measure_profile is not an MeasurementProfile object")

        measure_start = None
        (with_loads, run_parallel) = measure_profile.GetProfile()
        self.__logger.log(Log.INFO, "Using measurement profile [loads: %s  parallel: %s]" % (
                with_loads, run_parallel))
        try:
            nthreads = 0

            # start the loads
            if with_loads:
                self._loadmods.Start()

            print "rteval run on %s started at %s" % (os.uname()[2], time.asctime())
            print "started %d loads on %d cores" % (self._loadmods.ModulesLoaded(), self._sysinfo.cpu_getCores(True)),
            if self._sysinfo.mem_get_numa_nodes() > 1:
                print " with %d numa nodes" % self._sysinfo.mem_get_numa_nodes()
            else:
                print ""
            print "Run duration: %d seconds" % self.__cfg.duration

            # start the cyclictest thread
            measure_profile.Start()
            

            # Uleash the loads and measurement threads
            report_interval = int(self.__cfg.GetSection('rteval').report_interval)
            nthreads = with_loads and self._loadmods.Unleash() or None
            measure_profile.Unleash()
            measure_start = datetime.now()

            # wait for time to expire or thread to die
            signal.signal(signal.SIGINT, sigint_handler)
            signal.signal(signal.SIGTERM, sigterm_handler)
            self.__logger.log(Log.INFO, "waiting for duration (%f)" % self.__cfg.duration)
            stoptime = (time.time() + self.__cfg.duration)
            currtime = time.time()
            rpttime = currtime + report_interval
            load_avg_checked = 5
            while (currtime <= stoptime) and not sigint_received:
                time.sleep(1.0)
                if not measure_profile.isAlive():
                    stoptime = currtime
                    self.__logger.log(Log.WARN,
                                      "Measurement threads did not use the full time slot. Doing a controlled stop.")

                if with_loads:
                    if len(threading.enumerate()) < nthreads:
                        raise RuntimeError, "load thread died!"

                if not load_avg_checked:
                    self._loadmods.SaveLoadAvg()
                    load_avg_checked = 5
                else:
                    load_avg_checked -= 1

                if currtime >= rpttime:
                    left_to_run = stoptime - currtime
                    self.show_remaining_time(left_to_run)
                    rpttime = currtime + report_interval
                    print "load average: %.2f" % self._loadmods.GetLoadAvg()
                currtime = time.time()

            self.__logger.log(Log.DEBUG, "out of measurement loop")
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
                
        except RuntimeError, e:
            print "Runtime error during measurement: %s", e
            raise

        finally:
            # stop measurement threads
            measure_profile.Stop()
            
            # stop the loads
            if with_loads:
                self._loadmods.Stop()

        print "stopping run at %s" % time.asctime()

        # wait for measurement modules to finish calculating stats
        measure_profile.WaitForCompletion()

        return measure_start


    def summarize(self, file):
        isarchive = False
        summary = file
        if file.endswith(".tar.bz2"):
            import tarfile
            try:
                t = tarfile.open(file)
            except:
                print "Don't know how to summarize %s (tarfile open failed)" % file
                return
            element = None
            for f in t.getnames():
                if f.find('summary.xml') != -1:
                    element = f
                    break
            if element == None:
                print "No summary.xml found in tar archive %s" % file
                return
            tmp = tempfile.gettempdir()
            self.__logger.log(Log.DEBUG, "extracting %s from %s for summarizing" % (element, file))
            t.extract(element, path=tmp)
            summary = os.path.join(tmp, element)
            isarchive = True
        self._show_report(summary, 'rteval_text.xsl')
        if isarchive:
            os.unlink(summary)

    def rteval(self):
        ''' main function for rteval'''
        retval = 0;

        # if --summarize was specified then just parse the XML, print it and exit
        if self.__cmd_opts.summarize or self.__cmd_opts.rawhistogram:
            if len(self.cmd_arguments) < 1:
                raise RuntimeError, "Must specify at least one XML file with --summarize!"

            for x in self.__cmd_args:
                if self.__cmd_opts.summarize:
                    self.summarize(x)
                elif self.__cmd_opts.rawhistogram:
                    self._show_report(x, 'rteval_histogram_raw.xsl')

            sys.exit(0)

        if os.getuid() != 0:
            print "Must be root to run rteval!"
            sys.exit(-1)

        self.__logger.log(Log.DEBUG, '''rteval options:
        workdir: %s
        loaddir: %s
        reportdir: %s
        verbose: %s
        debugging: %s
        logging:  %s
        duration: %f
        sysreport: %s
        inifile:  %s''' % (self.__workdir, self.__cfg.srcdir, self.__reportdir, self.__cfg.verbose,
                           self.__cfg.debugging, self.__cfg.logging, self.__cfg.duration,
                           self.__cfg.sysreport, self.__inifile))

        if not os.path.isdir(self.__workdir):
            raise RuntimeError, "work directory %d does not exist" % self.__workdir

        self.prepare(self.__cmd_opts.onlyload)

        if self.__cmd_opts.onlyload:
            # If --onlyload were given, just kick off the loads and nothing more
            # No reports will be created.
            self._loadmods.Start()
            nthreads = self._loadmods.Unleash()
            self.__logger.log(Log.INFO, "Started %i load threads - will run for %f seconds" % (
                    nthreads, self.__cfg.duration))
            self.__logger.log(Log.INFO, "No measurements will be performed, due to the --onlyload option")
            time.sleep(self.__cfg.duration)
            self._loadmods.Stop()
            retval = 0
        else:
            # ... otherwise, run the full measurement suite with reports
            measure_start = None
            for meas_prf in self._measuremods:
                mstart = self.measure(meas_prf)
                if measure_start is None:
                    measure_start = mstart
            self._report(measure_start, self.__cfg.xslt_report)
            if self.__cfg.sysreport:
                self._sysinfo.run_sysreport(self.__reportdir)

            # if --xmlrpc-submit | -X was given, send our report to this host
            if self.__xmlrpc:
                retval = self.__xmlrpc.SendReport(self._XMLreport())

            self._sysinfo.copy_dmesg(self.__reportdir)
            self._tar_results()

            self.__logger.log(Log.DEBUG, "exiting with exit code: %d" % retval)

        return retval

if __name__ == '__main__':
    import pwd, grp

    try:
        rteval = RtEval(sys.argv[1:])
        ec = rteval.rteval()
        sys.exit(ec)
    except KeyboardInterrupt:
        sys.exit(0)
