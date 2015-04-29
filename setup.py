#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#   Copyright 2009-2013   Clark Williams <williams@redhat.com>
#   Copyright 2009-2013   David Sommerseth <davids@redhat.com>
#   Copyright 2013-2015   Raphaël Beamonte <raphael.beamonte@gmail.com>
#
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

from distutils.sysconfig import get_python_lib
from distutils.core import setup
from os.path import isfile, join, dirname
from re import search
import glob, os, sys, shutil, gzip



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
shutil.copy('rteval-cmd', 'dist/rteval')

# Hack to avoid importing libxml2 and a lot of other stuff
# when getting the rteval version.  These are modules which
# might not be available on the build box.
shutil.copy('rteval/version.py', 'dist/__init__.py')
from dist import RTEVAL_VERSION

# Copy the paths.py file to dist directory, this file must
# be copied as it will be modified with the paths of the
# current installation
shutil.copy('rteval/paths.py', 'dist/paths.py')

# Compress the man page, so distutil will only care for the compressed file
mangz = gzip.GzipFile('dist/rteval.8.gz', 'w', 9)
man = open('doc/rteval.8', 'r')
mangz.writelines(man)
man.close()
mangz.close()


# Do the distutils stuff
install = setup(name="rteval",
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
                        "rteval.sysinfo"
            ],
            package_dir = { "rteval": "rteval",
                            "rteval.modules": "rteval/modules",
                            "rteval.modules.loads": "rteval/modules/loads",
                            "rteval.modules.measurement": "rteval/modules/measurement",
                            "rteval.sysinfo": "rteval/sysinfo"
            },
            data_files = [("share/rteval", ["rteval/rteval_dmi.xsl",
                                            "rteval/rteval_histogram_raw.xsl",
                                            "rteval/rteval_text.xsl"]),
                          ("/etc", ["rteval.conf"]),
                          ("share/man/man8", ["dist/rteval.8.gz"])
            ],
            scripts = ["dist/rteval"]
)

# Get install information to update the paths.py file
install_info = install.get_command_obj("install")
if install_info.install_base is not None:
    print "updating paths.py variables"
    if not install.dry_run:
        DIR =  {'CONF':     '/etc',
                'SCRIPTS':  install_info.install_scripts,
                'DATA':     install_info.install_data,
                'LIB':      install_info.install_lib
        }
        # Open the file to write new paths.py
        new_pathspy = open(join(DIR['LIB'], 'rteval', 'paths.py'), 'w')
        # Open the original paths.py file
        old_pathspy = open(join(dirname(__file__), 'rteval', 'paths.py'))

        # Run line by line to change the values of the variables only
        for line in old_pathspy:
            m = search( "(?P<before>(?:.*[\s\t]|)RTEVAL_DIR_(?P<var>CONF|" \
                    +   "SCRIPTS|DATA|LIB)[\s\t]*=[\s\t]*)(?P<quote>['\"]).*" \
                    +   "(?P=quote)(?P<after>.*)$", line)
            # If this line contains one of our variables, replace it
            if m:
                line = m.group('before')    + m.group('quote') \
                    +  DIR[m.group('var')]  + m.group('quote') \
                    +  m.group('after')     + "\n"
            # Put the line, modified or not, in the file
            new_pathspy.write(line)

        # Close the files
        old_pathspy.close()
        new_pathspy.close()


# Clean-up from our little hack
os.unlink('dist/rteval')
os.unlink('dist/rteval.8.gz')
os.unlink('dist/__init__.py')
os.unlink('dist/__init__.pyc')

if distcreated:
    try:
        os.rmdir('dist')
    except OSError:
        # Ignore any errors
        pass
