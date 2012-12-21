#!/usr/bin/python
from distutils.sysconfig import get_python_lib
from distutils.core import setup
from os.path import isfile, join
import glob, os, shutil
from rteval import RTEVAL_VERSION


# Get PYTHONLIB with no prefix so --prefix installs work.
PYTHONLIB = join(get_python_lib(standard_lib=1, prefix=''), 'site-packages')

# Tiny hack to make rteval-cmd become a rteval when building/installing the package
try:
    os.mkdir('dist', 0755)
    distcreated = True
except OSError, e:
    if e.errno == 17:
        # If it already exists, ignore this error
        distcreated = False
    else:
        raise e
shutil.copy('rteval-cmd','dist/rteval')

setup(name="rteval",
      version = RTEVAL_VERSION,
      description = "Evaluate system performance for Realtime",
      author = "Clark Williams, David Sommerseth",
      author_email = "williams@redhat.com, davids@redhat.com",
      url = "https://git.kernel.org/?p=linux/kernel/git/clrkwllms/rteval.git;a=summary",
      license = "GPLv2",
      long_description =
"""\
The rteval script is used to judge the behavior of a hardware 
platform while running a Realtime Linux kernel under a moderate
to heavy load. 

Provides control logic for starting a system load and then running a 
response time measurement utility (cyclictest) for a specified amount
of time. When the run is finished, the sample data from cyclictest is
analyzed for standard statistical measurements (i.e mode, median, range,
mean, variance and standard deviation) and a report is generated. 
""",
      packages = ["rteval",
                  "rteval.modules",
                  "rteval.modules.loads",
                  "rteval.modules.measurement",
                  "rteval.sysinfo"],
      package_dir = { "rteval": "rteval",
                      "rteval.modules": "rteval/modules",
                      "rteval.modules.loads": "rteval/modules/loads",
                      "rteval.modules.measurement": "rteval/modules/measurement",
                      "rteval.sysinfo": "rteval/sysinfo"
                      },
      data_files = [("share/rteval", ["rteval/rteval_dmi.xsl",
                                      "rteval/rteval_histogram_raw.xsl",
                                      "rteval/rteval_text.xsl"]),
                    ("/etc", ["rteval.conf"])
                    ],
      scripts = ["dist/rteval"]
      )

# Clean-up from our little hack
os.unlink('dist/rteval')
if distcreated:
    try:
        os.rmdir('dist')
    except OSError:
        # Ignore any errors
        pass
