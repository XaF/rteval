import sys
import os
import time
import glob
import subprocess
from signal import SIGTERM
sys.pathconf = "."
import load

def kcompilesetup(topdir,tarball):
    # check for existing directory
    kdir=None
    names=os.listdir(".")
    for d in names:
        if d.startswith("linux-2.6"):
            kdir=d
            break
    if kdir == None:
        print "unpacking kernel tarball"
        tarargs = "-x"
        if tarball.endswith(".bz2"):
            tarargs += "j"
        elif tarball.endswith(".gz"):
            tarargs += "z"
        tarargs += "f"
        try:
            subprocess.call(["tar", tarargs, tarball])
        except:
            print "untar'ing kernel tarball failed!"
            sys.exit(-1)
        names = os.listdir('.')
        for d in names:
            print "kcompile: checking %s\n" % d
            if d.startswith("linux-2.6"):
                kdir=d
                break
        if kdir == None:
            raise RuntimeErrr, "Can't find kernel directory!"
    return os.path.join(topdir, kdir)

def kcompilebuild(mydir):
    print "kcompile setting up all module config file in %s" % os.getcwd()
    null = os.open("/dev/null", os.O_RDWR)
    # clean up from potential previous run
    subprocess.call(["make", "-C", mydir, "distclean", "allmodconfig"], 
                          stdin=null, stdout=null, stderr=null)
    #subprocess.call(["make", "distclean", "allmodconfig"])
    print "kcompile ready to run"

def kcompilerun(mydir, stopevent):
    null = os.open("/dev/null", os.O_RDWR)
    print "starting kcompile loop"
    args = ["make", "-C", mydir, "clean", "bzImage", "modules"]
    p = subprocess.Popen(args, stdin=null,stdout=null,stderr=null)
    while not stopevent.isSet():
        time.sleep(1.0)
        if p.poll() != None:
            p.wait()
            p = subprocess.Popen(args,stdin=null,stdout=null,stderr=null)
    print "stopping kcompile"
    os.kill(p.pid, SIGTERM)

    
def create(dir, source):
    print "looking for tarball in %s" % source
    tarball = glob.glob("%s/linux-2.6*" % source)[0]
    return load.Load("kcompile", tarball, dir,
                     kcompilesetup, kcompilebuild, kcompilerun)
    
