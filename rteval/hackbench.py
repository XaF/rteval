#  
#   hackbench.py - class to manage an instance of hackbench load
#
#   Copyright 2009,2010   Clark Williams <williams@redhat.com>
#   Copyright 2009,2010   David Sommerseth <davids@redhat.com>
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
    def __init__(self, params={}):
        load.Load.__init__(self, "hackbench", params)

    def __del__(self):
        null = open("/dev/null", "w")
        subprocess.call(['killall', '-9', 'hackbench'], 
                        stdout=null, stderr=null)
        os.close(null)

    def setup(self):
        'calculate arguments based on input parameters'
        mult = int(self.params.setdefault('jobspercore', 2))
        self.jobs = self.num_cpus * mult
        self.datasize = self.params.setdefault('datasize', '128')
        self.workunit = self.params.setdefault('workunit', 'thread')
        if self.workunit.startswith('thread'):
            workarg = '-T'
        else:
            workarg = '-P'
        self.args = ['hackbench',  workarg, 
                     '-g', str(self.jobs), 
                     '-l', str(self.num_cpus * 256), 
                     '-s', self.datasize,
                     ]

    def build(self):
        self.ready = True

    def runload(self):
        null = os.open("/dev/null", os.O_RDWR)
        if self.logging:
            out = self.open_logfile("hackbench.stdout")
            err = self.open_logfile("hackbench.stderr")
        else:
            out = err = null
        self.debug("starting loop (jobs: %d)" % self.jobs)

        while not self.stopevent.isSet():
            p = subprocess.Popen(self.args, stdin=out, stdout=out, stderr=err)
            time.sleep(1.0)
            if p.poll() != None:
                p.wait()
        self.debug("stopping")
        if p.poll() == None:
            os.kill(p.pid, SIGKILL)
        p.wait()
        self.debug("returning from runload()")
        os.close(null)
        if self.logging:
            os.close(out)
            os.close(err)

    def genxml(self, x):
        x.taggedvalue('command_line', ' '.join(self.args), {'name':'hackbench'})

def create(params = {}):
    return Hackbench(params)
