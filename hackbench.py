import sys
import os
import time
import glob
import subprocess
from signal import SIGTERM
sys.pathconf = "."
import load

# hackbench load functions

def hacksetup(topdir, tarball):
    # check for existing directory
    hackdir="hackbench"
    if not os.path.exists(hackdir):
        print "setting up hackbench tarball"
        tarargs = "-x"
        if tarball.endswith(".bz2"):
            tarargs += "j"
        elif tarball.endswith(".gz"):
            tarargs += "z"
        tarargs += "f"

        print "unpacking %s in %s" % (tarball, os.getcwd())
        try:
            subprocess.call(["tar", tarargs, tarball])
        except:
            print "untar'ing hackbench failed!"
            sys.exit(-1)
        if not os.path.exists(hackdir):
            raise RuntimeError, 'no hackbench directory!'
    return os.path.join(topdir, hackdir)

def hackbuild(mydir):
    print "building hackbench"
    null = os.open("/dev/null", os.O_RDWR)
    # clean up from potential previous run
    if os.path.exists("hackbench"):
        os.remove("hackbench")
    subprocess.check_call(["make", "-C", mydir], 
                          stdin=null, stdout=null, stderr=null)
    print "hackbench built"

def hackrun(mydir, stopevent):
    if not os.path.exists("./hackbench"):
        print "Can't find hackbench exe!"
        return
    null = os.open("/dev/null", os.O_RDWR)
    print "starting hackbench loop in %s" % os.getcwd()
    args = [os.path.join(mydir, "hackbench"), "20"]
    p = subprocess.Popen(args, stdin=null,stdout=null,stderr=null)
    while not stopevent.isSet():
        time.sleep(1.0)
        if p.poll() != None:
            p.wait()
            p = subprocess.Popen(args,stdin=null,stdout=null,stderr=null)
    print "stopping hackbench"
    os.kill(p.pid, SIGTERM)

    
def create(dir, source):
    tarball = glob.glob("%s/hackbench*" % source)[0]
    return load.Load("hackbench", tarball, dir,
                     hacksetup, hackbuild, hackrun)
