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


"""
Copyright (c) 2008-2012  Red Hat Inc.

Realtime verification utility
"""
__author__ = "Clark Williams <williams@redhat.com>, David Sommerseth <davids@redhat.com>"
__license__ = "GPLv2 License"

import os, signal, sys, threading, time
from datetime import datetime
from distutils import sysconfig
from modules.loads import LoadModules
from modules.measurement import MeasurementModules, MeasurementProfile
from rtevalReport import rtevalReport
from rtevalXMLRPC import rtevalXMLRPC
from Log import Log
import rtevalConfig, rtevalMailer


RTEVAL_VERSION = "2.0"

sigint_received = False
def sig_handler(signum, frame):

    if signum == signal.SIGINT:
        global sigint_received
        sigint_received = True
        print "*** SIGINT received - stopping rteval run ***"
    elif signum == signal.SIGTERM:
        raise RuntimeError("SIGTERM received!")



class RtEval(rtevalReport):
    def __init__(self, config, loadmods, measuremods, logger):
        self.__version = RTEVAL_VERSION

        if not isinstance(config, rtevalConfig.rtevalConfig):
            raise TypeError("config variable is not an rtevalConfig object")

        if not isinstance(loadmods, LoadModules):
            raise TypeError("loadmods variable is not a LoadModules object")

        if not isinstance(measuremods, MeasurementModules):
            raise TypeError("measuremods variable is not a MeasurementModules object")

        if not isinstance(logger, Log):
            raise TypeError("logger variable is not an Log object")

        self.__cfg = config
        self.__logger = logger
        self._loadmods = loadmods
        self._measuremods = measuremods

        self.__rtevcfg = self.__cfg.GetSection('rteval')
        self.__reportdir = None

        # Import SystemInfo here, to avoid DMI warnings if RtEval() is not used
        from sysinfo import SystemInfo
        self._sysinfo = SystemInfo(self.__rtevcfg, logger=self.__logger)

        # prepare a mailer, if that's configured
        if self.__cfg.HasSection('smtp'):
            self.__mailer = rtevalMailer.rtevalMailer(self.__cfg.GetSection('smtp'))
        else:
            self.__mailer = None

        # Prepare XSLT processing, if enabled
        if not self.__rtevcfg.xslt_report.startswith(self.__rtevcfg.installdir):
            self.__rtevcfg.xslt_report = os.path.join(self.__rtevcfg.installdir, "rteval_text.xsl")

        if not os.path.exists(self.__rtevcfg.xslt_report):
            raise RuntimeError("can't find XSL template (%s)!" % self.__rtevcfg.xslt_report)

        # Add rteval directory into module search path
        sys.path.insert(0, '%s/rteval' % sysconfig.get_python_lib())

        # Initialise the report module
        rtevalReport.__init__(self, self.__version,
                              self.__rtevcfg.installdir, self.__rtevcfg.annotate)

        # If --xmlrpc-submit is given, check that we can access the server
        if self.__rtevcfg.xmlrpc:
            self.__xmlrpc = rtevalXMLRPC(self.__rtevcfg.xmlrpc, self.__logger, self.__mailer)
            if not self.__xmlrpc.Ping():
                if not self.__rtevcfg.xmlrpc_noabort:
                    print "ERROR: Could not reach XML-RPC server '%s'.  Aborting." % \
                        self.__rtevcfg.xmlrpc
                    sys.exit(2)
                else:
                    print "WARNING: Could not ping the XML-RPC server.  Will continue anyway."
        else:
            self.__xmlrpc = None


    def __show_remaining_time(self, remaining):
        r = int(remaining)
        days = r / 86400
        if days: r = r - (days * 86400)
        hours = r / 3600
        if hours: r = r - (hours * 3600)
        minutes = r / 60
        if minutes: r = r - (minutes * 60)
        print "rteval time remaining: %d days, %d hours, %d minutes, %d seconds" % (days, hours, minutes, r)


    def Prepare(self, onlyload = False):
        builddir = os.path.join(self.__rtevcfg.workdir, 'rteval-build')
        if not os.path.isdir(builddir): os.mkdir(builddir)

        # create our report directory
        try:
            # Only create a report dir if we're doing measurements
            # or the loads logging is enabled
            if not onlyload or self.__rtevcfg.logging:
                self.__reportdir = self._make_report_dir(self.__rtevcfg.workdir, "summary.xml")
        except Exception, e:
            raise RuntimeError("Cannot create report directory (NFS with rootsquash on?) [%s]", str(e))

        self.__logger.log(Log.INFO, "Preparing load modules")
        params = {'workdir':self.__rtevcfg.workdir,
                  'reportdir':self.__reportdir,
                  'builddir':builddir,
                  'srcdir':self.__rtevcfg.srcdir,
                  'verbose': self.__rtevcfg.verbose,
                  'debugging': self.__rtevcfg.debugging,
                  'numcores':self._sysinfo.cpu_getCores(True),
                  'logging':self.__rtevcfg.logging,
                  'memsize':self._sysinfo.mem_get_size(),
                  'numanodes':self._sysinfo.mem_get_numa_nodes(),
                  'duration':self.__rtevcfg.duration,
                  }
        self._loadmods.Setup(params)

        self.__logger.log(Log.INFO, "Preparing measurement modules")
        self._measuremods.Setup(params)


    def __RunMeasurementProfile(self, measure_profile):
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
            print "Run duration: %d seconds" % self.__rtevcfg.duration

            # start the cyclictest thread
            measure_profile.Start()

            # Uleash the loads and measurement threads
            report_interval = int(self.__rtevcfg.report_interval)
            nthreads = with_loads and self._loadmods.Unleash() or None
            measure_profile.Unleash()
            measure_start = datetime.now()

            # wait for time to expire or thread to die
            signal.signal(signal.SIGINT, sig_handler)
            signal.signal(signal.SIGTERM, sig_handler)
            self.__logger.log(Log.INFO, "waiting for duration (%f)" % self.__rtevcfg.duration)
            stoptime = (time.time() + self.__rtevcfg.duration)
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
                    self.__show_remaining_time(left_to_run)
                    rpttime = currtime + report_interval
                    print "load average: %.2f" % self._loadmods.GetLoadAvg()
                currtime = time.time()

            self.__logger.log(Log.DEBUG, "out of measurement loop")
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)

        except RuntimeError, e:
            raise RuntimeError("appeared during measurement: %s" % e)

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


    def Measure(self):
        # Run the full measurement suite with reports
        rtevalres = 0
        measure_start = None
        for meas_prf in self._measuremods:
            mstart = self.__RunMeasurementProfile(meas_prf)
            if measure_start is None:
                measure_start = mstart

        self._report(measure_start, self.__rtevcfg.xslt_report)
        if self.__rtevcfg.sysreport:
            self._sysinfo.run_sysreport(self.__reportdir)

        # if --xmlrpc-submit | -X was given, send our report to the given host
        if self.__xmlrpc:
            retvalres = self.__xmlrpc.SendReport(self.GetXMLreport())

        self._sysinfo.copy_dmesg(self.__reportdir)
        self._tar_results()
        return rtevalres
