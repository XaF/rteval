import sys
import os
import time
import glob
import subprocess
from signal import SIGTERM
sys.pathconf = "."
import load

class Hackbench(load.Load):
    def __init__(self, source=None, dir=None):
        load.Load.__init__(self, "hackbench", source, dir)

    def setup(self):
        # check for existing directory
        self.mydir = os.path.join(self.dir, "hackbench")
        if not os.path.exists(self.mydir):
            print "setting up hackbench self.source"
            tarargs = ['tar', '-C', self.dir, '-x']
            if self.source.endswith(".bz2"):
                tarargs.append("-j")
            elif self.source.endswith(".gz"):
                tarargs.append("-z")
            tarargs.append("-f")
            tarargs.append(self.source)

            print "unpacking %s into %s" % (self.source, self.dir)
            try:
                subprocess.call(tarargs)
            except:
                print "untar'ing hackbench failed!"
                sys.exit(-1)
            if not os.path.exists(self.mydir):
                raise RuntimeError, 'no hackbench directory!'

    def build(self):
        print "building hackbench"
        null = os.open("/dev/null", os.O_RDWR)
        # clean up from potential previous run
        if os.path.exists("hackbench"):
            os.remove("hackbench")
        subprocess.check_call(["make", "-C", self.mydir], 
                              stdin=null, stdout=null, stderr=null)
        print "hackbench built"

    def runload(self):
        exe = os.path.join(self.mydir, "hackbench")
        if not os.path.exists(exe):
            print "Can't find hackbench exe!"
            return
        null = os.open("/dev/null", os.O_RDWR)
        print "starting hackbench loop in %s" % os.getcwd()
        args = [exe, "20"]
        p = subprocess.Popen(args, stdin=null,stdout=null,stderr=null)
        while not self.stopevent.isSet():
            time.sleep(1.0)
            if p.poll() != None:
                p.wait()
                p = subprocess.Popen(args,stdin=null,stdout=null,stderr=null)
                print "restarting hackbench load"
        print "stopping hackbench"
        os.kill(p.pid, SIGTERM)

    
def create(dir, source):
    tarball = glob.glob("%s/hackbench*" % source)[0]
    return Hackbench(tarball, dir)
