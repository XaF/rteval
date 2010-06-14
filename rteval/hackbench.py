#  
#   hackbench.py - class to manage an instance of hackbench load
#
#   Copyright 2009   Clark Williams <williams@redhat.com>
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
import glob
import subprocess
from signal import SIGTERM
from signal import SIGKILL
sys.pathconf = "."
import load

class Hackbench(load.Load):
    def __init__(self, builddir=None, srcdir=None, debug=False, num_cpus=1, params={}):
        load.Load.__init__(self, "hackbench", builddir, srcdir, debug, num_cpus, params)

    def __del__(self):
        null = open("/dev/null", "w")
        subprocess.call(['killall', '-9', 'hackbench'], 
                        stdout=null, stderr=null)
        os.close(null)

    def setup(self):
        # find our tarball
        if self.params.has_key('source'):
            self.source = os.path.join(self.srcdir, self.params.source)
            if not os.path.exists(self.source):
                raise RuntimeError, "hackbench: source %s does not exist!" % self.source
        else:
            tarfiles = glob.glob(os.path.join(self.srcdir, "hackbench*"))
            if len(tarfiles):
                self.source = tarfiles[0]
        # check for existing directory
        self.mydir = os.path.join(self.builddir, "hackbench")
        if not os.path.exists(self.mydir):
            self.debug("setting up hackbench self.source")
            tarargs = ['tar', '-C', self.builddir, '-x']
            if self.source.endswith(".bz2"):
                tarargs.append("-j")
            elif self.source.endswith(".gz"):
                tarargs.append("-z")
            tarargs.append("-f")
            tarargs.append(self.source)

            self.debug("unpacking %s into %s" % (self.source, self.mydir))
            try:
                subprocess.call(tarargs)
            except:
                print "untar'ing hackbench failed!"
                sys.exit(-1)
            if not os.path.exists(self.mydir):
                raise RuntimeError, 'no hackbench directory!'
        mult = 1
        if self.params.has_key('jobspercore'):
            mult = int(self.params.jobspercore)
        self.jobs = self.num_cpus * mult
            

    def build(self):
        self.debug("building")
        null = os.open("/dev/null", os.O_RDWR)
        # clean up from potential previous run
        exe = os.path.join(self.mydir, "hackbench")
        if os.path.exists(exe):
            os.remove(exe)
        subprocess.call(["make", "-C", self.mydir],  
                             stdin=null, stdout=null, stderr=null)
        self.debug("built")
        self.exe = os.path.join(self.mydir, "hackbench")
        if not os.path.exists(self.exe):
            raise RuntimeError, "Can't find hackbench executable: %s" % self.exe
        self.args = [self.exe, str(self.jobs)]
        self.ready = True
        os.close(null)

    def runload(self):
        null = os.open("/dev/null", os.O_RDWR)
        self.debug("starting loop (jobs: %d)" % self.jobs)
        p = subprocess.Popen(self.args, stdin=null,stdout=null,stderr=null)
        while not self.stopevent.isSet():
            time.sleep(1.0)
            if p.poll() != None:
                p.wait()
                p = subprocess.Popen(self.args,stdin=null,stdout=null,stderr=null)
        self.debug("stopping")
        if p.poll() == None:
            os.kill(p.pid, SIGKILL)
        p.wait()
        self.debug("returning from runload()")
        os.close(null)

    def genxml(self, x):
        x.taggedvalue('command_line', ' '.join(self.args), {'name':'hackbench'})

def create(builddir, srcdir, debug, num_cpus, params = {}):
    return Hackbench(builddir, srcdir, debug, num_cpus, params)
