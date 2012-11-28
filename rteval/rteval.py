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
import socket
import optparse
import tempfile
import signal
import rtevalclient
import xmlrpclib
from datetime import datetime
from distutils import sysconfig
from Log import Log
from sysinfo import SystemInfo
from modules.loads import LoadModules
from rtevalReport import rtevalReport

# put local path at start of list to overide installed methods
sys.path.insert(0, "./rteval")
from modules import loads
from modules.measurement import cyclictest, HWLatDetect
import xmlout
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
        self.version = "1.36"
        self.workdir = os.getcwd()
        self.reportdir = None
        self.inifile = None
        self.cmd_options = {}

        default_config = {
            'rteval': {
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
                }
            }

        # Prepare logging
        self.__logger = Log()
        self.__logger.SetLogVerbosity(Log.INFO)

        # setup initial configuration
        self.config = rtevalConfig.rtevalConfig(default_config, logger=self.__logger)

        # parse command line options
        self.parse_options(cmdargs)

        # read in config file info
        self.inifile = self.config.Load(self.cmd_options.inifile)

        # copy the command line options into the rteval config section
        # (cmd line overrides config file values)
        self.config.AppendConfig('rteval', self.cmd_options)

        # Update log level, based on config/command line args
        loglev = (self.config.verbose and Log.INFO) | (self.config.debugging and Log.DEBUG)
        self.__logger.SetLogVerbosity(loglev)

        self.__logger.log(Log.DEBUG, "workdir: %s" % self.workdir)

        # prepare a mailer, if that's configured
        if self.config.HasSection('smtp'):
            self.mailer = rtevalMailer.rtevalMailer(self.config.GetSection('smtp'))
        else:
            self.mailer = None

        self._sysinfo = SystemInfo(self.config, logger=self.__logger)
        self._loadmods = LoadModules(self.config, logger=self.__logger)

        self.xml = None
        self.annotate = self.cmd_options.annotate

        if not self.config.xslt_report.startswith(self.config.installdir):
            self.config.xslt_report = os.path.join(self.config.installdir, "rteval_text.xsl")

        if not os.path.exists(self.config.xslt_report):
            raise RuntimeError, "can't find XSL template (%s)!" % self.config.xslt_report

        # Add rteval directory into module search path
        sys.path.insert(0, '%s/rteval' % sysconfig.get_python_lib())

        # Initialise the report module
        rtevalReport.__init__(self, self.version, self.config.installdir, self.annotate)

        # If --xmlrpc-submit is given, check that we can access the server
        res = None
        if self.config.xmlrpc:
            self.__logger.log(Log.DEBUG, "Checking if XML-RPC server '%s' is reachable" % self.config.xmlrpc)
            attempt = 0
            warning_sent = False
            ping_failed = False
            while attempt < 6:
                try:
                    client = rtevalclient.rtevalclient("http://%s/rteval/API1/" % self.config.xmlrpc)
                    res = client.Hello()
                    attempt = 10
                    ping_failed = False
                except xmlrpclib.ProtocolError:
                    # Server do not support Hello(), but is reachable
                    self.__logger.log(Log.INFO, "Got XML-RPC connection with %s but it did not support Hello()"
                              % self.config.xmlrpc)
                    res = None
                except socket.error, err:
                    self.__logger.log(Log.INFO, "Could not establish XML-RPC contact with %s\n%s"
                              % (self.config.xmlrpc, str(err)))

                    if (self.mailer is not None) and (not warning_sent):
                        self.mailer.SendMessage("[RTEVAL:WARNING] Failed to ping XML-RPC server",
                                                "Server %s did not respond.  Not giving up yet."
                                                % self.config.xmlrpc)
                        warning_sent = True

                    # Do attempts handling
                    attempt += 1
                    if attempt > 5:
                        break # To avoid sleeping before we abort

                    print "Failed pinging XML-RPC server.  Doing another attempt(%i) " % attempt
                    time.sleep(attempt*15) # Incremental sleep - sleep attempts*15 seconds
                    ping_failed = True

            if ping_failed:
                if not self.cmd_options.xmlrpc_noabort:
                    print "ERROR: Could not reach XML-RPC server '%s'.  Aborting." % self.config.xmlrpc
                    sys.exit(2)
                else:
                    print "WARNING: Could not ping the XML-RPC server.  Will continue anyway."

            if res:
                self.__logger.log(Log.INFO, "Verified XML-RPC connection with %s (XML-RPC API version: %i)"
                          % (res["server"], res["APIversion"]))
                self.__logger.log(Log.DEBUG, "Recieved greeting: %s" % res["greeting"])


    def parse_options(self, cmdargs):
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
        parser.add_option("-l", "--loaddir", dest="srcdir",
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

        parser.add_option("--hwlatdetect", dest="hwlatdetect",
                          action='store_true', default=False,
                          help="Run hardware latency detect afterwards")

        (self.cmd_options, self.cmd_arguments) = parser.parse_args(args = cmdargs)
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
        self.workdir = os.path.abspath(self.cmd_options.workdir)
    

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
        builddir = os.path.join(self.workdir, 'rteval-build')
        if not os.path.isdir(builddir): os.mkdir(builddir)

        # create our report directory
        try:
            # Only create a report dir if we're doing measurements
            # or the loads logging is enabled
            if not onlyload or self.config.logging:
                self.reportdir = self._make_report_dir(self.workdir)
        except Exception, e:
            raise RuntimeError("Cannot create report directory (NFS with rootsquash on?) [%s]", str(e))

        self.__logger.log(Log.INFO, "setting up loads")
        params = {'workdir':self.workdir, 
                  'reportdir':self.reportdir,
                  'builddir':builddir,
                  'srcdir':self.config.srcdir,
                  'verbose': self.config.verbose,
                  'debugging': self.config.debugging,
                  'numcores':self._sysinfo.cpu_getCores(True),
                  'logging':self.config.logging,
                  'memsize':self._sysinfo.mem_get_size(),
                  'numanodes':self._sysinfo.mem_get_numa_nodes(),
                  'duration':self.config.duration,
                  }
        self._loadmods.Setup(params)

        if not onlyload:
            self.config.AppendConfig('cyclictest', params)
            self.__logger.log(Log.INFO, "setting up cyclictest")
            self.cyclictest = cyclictest.Cyclictest(params=self.config.GetSection('cyclictest'),
                                                    logger=self.__logger)

            self.xml = os.path.join(self.reportdir, "summary.xml")


    def measure(self):
        try:
            nthreads = 0

            # start the loads
            self._loadmods.Start()
            
            print "rteval run on %s started at %s" % (os.uname()[2], time.asctime())
            print "started %d loads on %d cores" % (self._loadmods.ModulesLoaded(), self._sysinfo.cpu_getCores(True)),
            if self._sysinfo.mem_get_numa_nodes() > 1:
                print " with %d numa nodes" % self._sysinfo.mem_get_numa_nodes()
            else:
                print ""
            print "Run duration: %d seconds" % self.config.duration

            # start the cyclictest thread
            self.__logger.log(Log.INFO, "starting cyclictest")
            self.cyclictest.start()
            
            nthreads = self._loadmods.Unleash()

            report_interval = int(self.config.GetSection('rteval').report_interval)

            # wait for time to expire or thread to die
            signal.signal(signal.SIGINT, sigint_handler)
            signal.signal(signal.SIGTERM, sigterm_handler)
            self.__logger.log(Log.INFO, "waiting for duration (%f)" % self.config.duration)
            stoptime = (time.time() + self.config.duration)
            currtime = time.time()
            rpttime = currtime + report_interval
            loadcount = 5
            while (currtime <= stoptime) and not sigint_received:
                time.sleep(1.0)
                if not self.cyclictest.isAlive():
                    raise RuntimeError, "cyclictest thread died!"
                if len(threading.enumerate()) < nthreads:
                    raise RuntimeError, "load thread died!"
                if not loadcount:
                    self._loadmods.SaveLoadAvg()
                    loadcount = 5
                else:
                    loadcount -= 1
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
            # stop cyclictest
            self.cyclictest.stopevent.set()
            
            # stop the loads
            self._loadmods.Stop()

        if self.cmd_options.hwlatdetect:
            try:
                self.__hwlat = HWLatDetect.HWLatDetectRunner(self.config.GetSection('hwlatdetect'),
                                                             logger=self.__logger)
                self.__logger.log(Log.INFO, "Running hwlatdetect")
                self.__hwlat.run()
            except Exception, e:
                self.__logger.log(Log.INFO, "Failed to run hwlatdetect")
                self.__logger.log(Log.DEBUG, str(e))

        print "stopping run at %s" % time.asctime()

        # wait for cyclictest to finish calculating stats
        self.cyclictest.finished.wait()


    def XMLRPC_Send(self):
        "Sends the report to a given XML-RPC host.  Returns 0 on success or 2 on submission failure."

        if not self.config.xmlrpc:
            return 2

        url = "http://%s/rteval/API1/" % self.config.xmlrpc
        attempt = 0
        exitcode = 2   # Presume failure
        warning_sent = False
        while attempt < 6:
            try:
                client = rtevalclient.rtevalclient(url)
                print "Submitting report to %s" % url
                rterid = client.SendReport(self._XMLreport())
                print "Report registered with submission id %i" % rterid
                attempt = 10
                exitcode = 0 # Success
            except socket.error:
                if (self.mailer is not None) and (not warning_sent):
                    self.mailer.SendMessage("[RTEVAL:WARNING] Failed to submit report to XML-RPC server",
                                            "Server %s did not respond.  Not giving up yet."
                                            % self.config.xmlrpc)
                    warning_sent = True

                attempt += 1
                if attempt > 5:
                    break # To avoid sleeping before we abort

                print "Failed sending report.  Doing another attempt(%i) " % attempt
                time.sleep(attempt*5*60) # Incremental sleep - sleep attempts*5 minutes

            except Exception, err:
                raise err

        if (self.mailer is not None):
            # Send final result messages
            if exitcode == 2:
                self.mailer.SendMessage("[RTEVAL:FAILURE] Failed to submit report to XML-RPC server",
                                        "Server %s did not respond at all after %i attempts."
                                        % (self.config.xmlrpc, attempt - 1))
            elif (exitcode == 0) and warning_sent:
                self.mailer.SendMessage("[RTEVAL:SUCCESS] XML-RPC server available again",
                                        "Succeeded to submit the report to %s in the end."
                                        % (self.config.xmlrpc))
        return exitcode


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
        if self.cmd_options.summarize or self.cmd_options.rawhistogram:
            if len(self.cmd_arguments) < 1:
                raise RuntimeError, "Must specify at least one XML file with --summarize!"

            for x in self.cmd_arguments:
                if self.cmd_options.summarize:
                    self.summarize(x)
                elif self.cmd_options.rawhistogram:
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
        inifile:  %s''' % (self.workdir, self.config.srcdir, self.reportdir, self.config.verbose,
                           self.config.debugging, self.config.logging, self.config.duration, 
                           self.config.sysreport, self.inifile))

        if not os.path.isdir(self.workdir):
            raise RuntimeError, "work directory %d does not exist" % self.workdir

        self.prepare(self.cmd_options.onlyload)

        if self.cmd_options.onlyload:
            # If --onlyload were given, just kick off the loads and nothing more
            # No reports will be created.
            self._loadmods.Start()
            nthreads = self._loadmods.Unleash()
            self.__logger.log(Log.INFO, "Started %i load threads - will run for %f seconds" % (
                    nthreads, self.config.duration))
            self.__logger.log(Log.INFO, "No measurements will be performed, due to the --onlyload option")
            time.sleep(self.config.duration)
            self._loadmods.Stop()
            retval = 0
        else:
            # ... otherwise, run the full measurement suite with reports
            measure_start = datetime.now()
            self.measure()
            self._report(measure_start, self.config.xslt_report)
            if self.config.sysreport:
                self._sysinfo.run_sysreport(self.reportdir)

            # if --xmlrpc-submit | -X was given, send our report to this host
            if self.config.xmlrpc:
                retval = self.XMLRPC_Send()

            self._sysinfo.copy_dmesg(self.reportdir)
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
