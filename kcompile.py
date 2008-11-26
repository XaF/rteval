import sys
import os
import time
import glob
import subprocess
from signal import SIGTERM
sys.pathconf = "."
import load

class Kcompile(load.Load):
    def __init__(self, source=None, dir=None):
        load.Load.__init__(self, "kcompile", source, dir)

    def setup(self):
        # check for existing directory
        kdir=None
        names=os.listdir(self.dir)
        for d in names:
            if d.startswith("linux-2.6"):
                kdir=d
                break
        if kdir == None:
            print "unpacking kernel tarball"
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
                print "untar'ing kernel self.source failed!"
                sys.exit(-1)
            names = os.listdir('.')
            for d in names:
                print "kcompile: checking %s\n" % d
                if d.startswith("linux-2.6"):
                    kdir=d
                    break
        if kdir == None:
            raise RuntimeErrr, "Can't find kernel directory!"
        self.mydir = os.path.join(self.dir, kdir)

    def build(self):
        print "kcompile setting up all module config file in %s" % os.getcwd()
        null = os.open("/dev/null", os.O_RDWR)
        # clean up from potential previous run
        subprocess.call(["make", "-C", self.mydir, "distclean", "allmodconfig"], 
                        stdin=null, stdout=null, stderr=null)
        print "kcompile ready to run"

    def runload(self):
        null = os.open("/dev/null", os.O_RDWR)
        print "starting kcompile loop"
        args = ["make", "-C", self.mydir, "clean", "bzImage", "modules"]
        p = subprocess.Popen(args, stdin=null,stdout=null,stderr=null)
        while not self.stopevent.isSet():
            time.sleep(1.0)
            if p.poll() != None:
                p.wait()
                p = subprocess.Popen(args,stdin=null,stdout=null,stderr=null)
        print "stopping kcompile"
        os.kill(p.pid, SIGTERM)

    
def create(dir, source):
    print "looking for tarball in %s" % source
    tarball = glob.glob("%s/linux-2.6*" % source)[0]
    return Kcompile(tarball, dir)
    
