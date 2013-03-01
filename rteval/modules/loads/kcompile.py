#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2012 - 2013   David Sommerseth <davids@redhat.com>
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
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#   For the avoidance of doubt the "preferred form" of this code is one which
#   is in an open unpatent encumbered format. Where cryptographic key signing
#   forms part of the process of creating an executable the information
#   including keys needed to generate an equivalently functional executable
#   are deemed to be part of the source code.
#

import sys, os, glob, subprocess
from signal import SIGTERM
from rteval.modules import rtevalRuntimeError
from rteval.modules.loads import CommandLineLoad
from rteval.Log import Log

kernel_prefix="linux-2.6"

class Kcompile(CommandLineLoad):
    def __init__(self, config, logger):
        CommandLineLoad.__init__(self, "kcompile", config, logger)


    def _WorkloadSetup(self):
        # find our source tarball
        if self._cfg.has_key('tarball') and self._cfg.tarball is not None:
            tarfile = os.path.join(self.srcdir, self._cfg.tarball)
            if not os.path.exists(tarfile):
                raise rtevalRuntimeError(self, " tarfile %s does not exist!" % tarfile)
            self.source = tarfile
        else:
            tarfiles = glob.glob(os.path.join(self.srcdir, "%s*" % kernel_prefix))
            if len(tarfiles):
                self.source = tarfiles[0]
            else:
                raise rtevalRuntimeError(self, " no kernel tarballs found in %s" % self.srcdir)

        # check for existing directory
        kdir=None
        names=os.listdir(self.builddir)
        for d in names:
            if d.startswith(kernel_prefix):
                kdir=d
                break
        if kdir == None:
            self._log(Log.DEBUG, "unpacking kernel tarball")
            tarargs = ['tar', '-C', self.builddir, '-x']
            if self.source.endswith(".bz2"):
                tarargs.append("-j")
            elif self.source.endswith(".gz"):
                tarargs.append("-z")
            tarargs.append("-f")
            tarargs.append(self.source)
            try:
                subprocess.call(tarargs)
            except:
                self._log(Log.DEBUG, "untar'ing kernel '%s' failed!" % self.source)
                sys.exit(-1)
            names = os.listdir(self.builddir)
            for d in names:
                self._log(Log.DEBUG, "checking %s" % d)
                if d.startswith(kernel_prefix):
                    kdir=d
                    break
        if kdir == None:
            raise rtevalRuntimeError(self, "Can't find kernel directory!")
        self.jobs = 1 # We only run one instance of the kcompile job
        self.mydir = os.path.join(self.builddir, kdir)
        self._log(Log.DEBUG, "mydir = %s" % self.mydir)


    def _WorkloadBuild(self):
        self._log(Log.DEBUG, "setting up all module config file in %s" % self.mydir)
        null = os.open("/dev/null", os.O_RDWR)
        if self._logging:
            out = self.open_logfile("kcompile-build.stdout")
            err = self.open_logfile("kcompile-build.stderr")
        else:
            out = err = null

        # clean up from potential previous run
        try:
            ret = subprocess.call(["make", "-C", self.mydir, "mrproper", "allmodconfig"], 
                                  stdin=null, stdout=out, stderr=err)
            if ret:
                raise rtevalRuntimeError(self, "kcompile setup failed: %d" % ret)
        except KeyboardInterrupt, m:
            self._log(Log.DEBUG, "keyboard interrupt, aborting")
            return
        self._log(Log.DEBUG, "ready to run")
        os.close(null)
        if self._logging:
            os.close(out)
            os.close(err)
        self._setReady()


    def __calc_numjobs(self):
        mult = int(self._cfg.setdefault('jobspercore', 1))
        mem = self.memsize[0]
        if self.memsize[1] == 'KB':
            mem = mem / (1024.0 * 1024.0)
        elif self.memsize[1] == 'MB':
            mem = mem / 1024.0
        elif self.memsize[1] == 'TB':
            mem = mem * 1024
        ratio = float(mem) / float(self.num_cpus)
        if ratio > 1.0:
            njobs = self.num_cpus * mult
        else:
            self._log(Log.DEBUG, "Low memory system (%f GB/core)! Dropping jobs to one per core" % ratio)
            njobs = self.num_cpus
        return njobs


    def _WorkloadPrepare(self):
        self.__nullfd = os.open("/dev/null", os.O_RDWR)
        if self._logging:
            self.__outfd = self.open_logfile("kcompile.stdout")
            self.__errfd = self.open_logfile("kcompile.stderr")
        else:
            self.__outfd = self.__errfd = self.__nullfd

        self.jobs = self.__calc_numjobs()
        self._log(Log.DEBUG, "starting loop (jobs: %d)" % self.jobs)
        self.args = ["make", "-C", self.mydir,
                     "-j%d" % self.jobs ]
        self.__kcompileproc = None


    def _WorkloadTask(self):
        if not self.__kcompileproc or self.__kcompileproc.poll() is not None:
            # If kcompile has not been kicked off yet, or have completed,
            # restart it
            self._log(Log.DEBUG, "Kicking off kcompile: %s" % " ".join(self.args))
            self.__kcompileproc = subprocess.Popen(self.args,
                                                   stdin=self.__nullfd,
                                                   stdout=self.__outfd,
                                                   stderr=self.__errfd)


    def WorkloadAlive(self):
        # Let _WorkloadTask() kick off new runs, if it stops - thus
        # kcompile will always be alive
        return True


    def _WorkloadCleanup(self):
        self._log(Log.DEBUG, "out of stopevent loop")
        if self.__kcompileproc.poll() == None:
            self._log(Log.DEBUG, "killing compile job with SIGTERM")
            os.kill(self.__kcompileproc.pid, SIGTERM)
        self.__kcompileproc.wait()
        os.close(self.__nullfd)
        del self.__nullfd
        if self._logging:
            os.close(self.__outfd)
            del self.__outfd
            os.close(self.__errfd)
            del self.__errfd
        del self.__kcompileproc
        self._setFinished()



def ModuleParameters():
    return {"tarball":   {"descr": "Source tar ball",
                         "metavar": "TARBALL"},
            "jobspercore": {"descr": "Number of working threads per core",
                            "default": 2,
                            "metavar": "NUM"}
            }



def create(config, logger):
    return Kcompile(config, logger)
