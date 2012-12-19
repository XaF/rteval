#  
#   hackbench.py - class to manage an instance of hackbench load
#
#   Copyright 2009 - 2012  Clark Williams <williams@redhat.com>
#   Copyright 2009 - 2012  David Sommerseth <davids@redhat.com>
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

import sys, os, time, glob, subprocess, errno
from signal import SIGTERM, SIGKILL
from rteval.modules.loads import CommandLineLoad
from rteval.Log import Log


class Hackbench(CommandLineLoad):
    def __init__(self, config, logger):
        CommandLineLoad.__init__(self, "hackbench", config, logger)


    def _WorkloadSetup(self):
        'calculate arguments based on input parameters'
        (mem, units) = self.memsize
        if units == 'KB':
            mem = mem / (1024.0 * 1024.0)
        elif units == 'MB':
            mem = mem / 1024.0
        elif units == 'TB':
            mem = mem * 1024
        ratio = float(mem) / float(self.num_cpus)
        if ratio >= 0.75:
            mult = float(self._cfg.setdefault('jobspercore', 2))
        else:
            self._log(Log.INFO, "hackbench: low memory system (%f GB/core)! Not running\n" % ratio)
            mult = 0
        self.jobs = self.num_cpus * mult

        self.args = ['hackbench',  '-P',
                     '-g', str(self.jobs), 
                     '-l', str(self._cfg.setdefault('loops', '100')),
                     '-s', str(self._cfg.setdefault('datasize', '100'))
                     ]
        self.__err_sleep = 5.0


    def _WorkloadBuild(self):
        # Nothing to build, so we're basically ready
        self._setReady()


    def _WorkloadPrepare(self):
        # if we don't have any jobs just wait for the stop event and return
        if self.jobs == 0:
            self.WaitForCompletion()
            return

        self.__nullfp = os.open("/dev/null", os.O_RDWR)
        if self._logging:
            self.__out = self.open_logfile("hackbench.stdout")
            self.__err = self.open_logfile("hackbench.stderr")
        else:
            self.__out = self.__err = self.__nullfp

        self._log(Log.DEBUG, "starting loop (jobs: %d)" % self.jobs)


    def _WorkloadTask(self):
        if self.shouldStop():
            return

        self._log(Log.DEBUG, "running: %s" % " ".join(self.args))
        try:
            self.__hbproc = subprocess.Popen(self.args,
                                             stdin=self.__nullfp,
                                             stdout=self.__out,
                                             stderr=self.__err)
        except OSError, e:
            if e.errno != errno.ENOMEM:
                raise e
            # Catch out-of-memory errors and wait a bit to (hopefully)
            # ease memory pressure
            self._log(Log.DEBUG, "hackbench: %s, sleeping for %f seconds" % (e.strerror, self.__err_sleep))
            time.sleep(self.__err_sleep)
            if self.__err_sleep < 60.0:
                self.__err_sleep *= 2.0
            if self.__err_sleep > 60.0:
                self.__err_sleep = 60.0


    def WorkloadAlive(self):
        # As hackbench is short-lived, lets pretend it is always alive
        return True


    def _WorkloadCleanup(self):
        if self.__hbproc.poll() == None:
            os.kill(self.__hbproc.pid, SIGKILL)
        self.__hbproc.wait()

        os.close(self.__nullfp)
        if self._logging:
            os.close(self.__out)
            del self.__out
            os.close(self.__err)
            del self.__err

        del self.__hbproc
        del self.__nullfp



def ModuleParameters():
    return {"jobspercore": {"descr": "Number of working threads per CPU core",
                            "default": 5,
                            "metavar": "NUM"}
            }



def create(config, logger):
    return Hackbench(config, logger)


if __name__ == '__main__':
    h = Hackbench(params={'debugging':True, 'verbose':True})
    h.run()
