import sys
import os
import time
import glob
import subprocess
from signal import SIGTERM
sys.pathconf = "."
import load
import xmlout

kernel_prefix="linux-2.6"

class Kcompile(load.Load):
    def __init__(self, source=None, dir=None, debug=False, num_cpus=1):
        load.Load.__init__(self, "kcompile", source, dir, 
                           debug, num_cpus)

    def setup(self):
        # check for existing directory
        kdir=None
        names=os.listdir(self.dir)
        for d in names:
            if d.startswith(kernel_prefix):
                kdir=d
                break
        if kdir == None:
            self.debug("unpacking kernel tarball")
            tarargs = ['tar', '-C', self.dir, '-x']
            if self.source.endswith(".bz2"):
                tarargs.append("-j")
            elif self.source.endswith(".gz"):
                tarargs.append("-z")
            tarargs.append("-f")
            tarargs.append(self.source)
            try:
                subprocess.call(tarargs)
            except:
                self.debug("untar'ing kernel self.source failed!")
                sys.exit(-1)
            names = os.listdir(self.dir)
            for d in names:
                self.debug("kcompile: checking %s\n" % d)
                if d.startswith(kernel_prefix):
                    kdir=d
                    break
        if kdir == None:
            raise RuntimeError, "Can't find kernel directory!"
        self.mydir = os.path.join(self.dir, kdir)
        self.debug("kcompile: mydir = %s\n" % self.mydir)

    def build(self):
        self.debug("kcompile setting up all module config file in %s" % self.mydir)
        null = os.open("/dev/null", os.O_RDWR)
        # clean up from potential previous run
        try:
            ret = subprocess.call(["make", "-C", self.mydir, "distclean", "allmodconfig"], 
                                  stdin=null, stdout=null, stderr=null)
            if ret:
                raise RuntimeError, "kcompile setup failed: %d" % ret
        except KeyboardInterrupt, m:
            self.debug("keyboard interrupt, kcompile aborted")
            return
        self.debug("kcompile ready to run")
        self.ready = True

    def runload(self):
        null = os.open("/dev/null", os.O_RDWR)
        self.debug("starting kcompile loop (jobs: %d)" % self.num_cpus)
        self.args = ["make", "-C", self.mydir, 
                     "-j%d" % self.num_cpus, 
                     "clean", "bzImage", "modules"]
        p = subprocess.Popen(self.args, 
                             stdin=null,stdout=null,stderr=null)
        while not self.stopevent.isSet():
            time.sleep(1.0)
            if p.poll() != None:
                p.wait()
                self.debug("restarting compile job")
                p = subprocess.Popen(self.args,
                                     stdin=null,stdout=null,stderr=null)
        self.debug("stopping kcompile")
        os.kill(p.pid, SIGTERM)

    def genxml(self, x):
        x.openblock('kcompile')
        x.taggedvalue('command_line', ' '.join(self.args))
        x.closeblock()

def create(dir, source, debug, num_cpus):
    tarball = glob.glob("%s*" % os.path.join(source,kernel_prefix))[0]
    return Kcompile(tarball, dir, debug, num_cpus)
    
