#
#   rteval - script for evaluating platform suitability for RT Linux
#
#           This program is used to determine the suitability of
#           a system for use in a Real Time Linux environment.
#           It starts up various system loads and measures event
#           latency while the loads are running. A report is generated
#           to show the latencies encountered during the run.
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
import os, sys
import ConfigParser
from Log import Log


def default_config_search(relative_path, verifdef=os.path.isdir):
    ConfigDirectories=[
            os.path.join(os.path.expanduser("~" + \
                    (os.getenv('SUDO_USER') or os.getenv('USER'))), '.rteval'),
            '/etc/rteval',
            '/usr/share/rteval'
            ]

    if os.path.dirname(os.path.abspath(__file__)) != '/usr/share/rteval':
        ConfigDirectories = [
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rteval')
                ] + ConfigDirectories

        for path in ConfigDirectories:
            if verifdef(os.path.join(path, *relative_path)):
                return os.path.join(path, *relative_path)

    return False


# HACK: A temporary hack to try to figure out where the install dir is.
typical_install_paths = ('/usr/bin','/usr/local/bin')
try:
    if typical_install_paths.index(os.path.dirname(os.path.abspath(sys.argv[0]))):
        installdir = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        installdir = '/usr/share/rteval'

except ValueError:
    installdir = '/usr/share/rteval'

default_config = {
    'rteval': {
        'quiet'      : False,
        'verbose'    : False,
        'keepdata'   : True,
        'debugging'  : False,
        'duration'   : '60',
        'sysreport'  : False,
        'reportdir'  : None,
        'reportfile' : None,
        'workdir'    : os.getcwd(),
        'installdir' : installdir,
        'srcdir'     : default_config_search(['loadsource']),
        'xmlrpc'     : None,
        'xslt_report': default_config_search(['rteval_text.xsl'], os.path.isfile),
        'report_interval': '600',
        'logging'    : False,
        }
    }


class rtevalCfgSection(object):
    def __init__(self, section_cfg):
        if type(section_cfg) is not dict:
            raise TypeError('section_cfg argument is not a dict variable')

        self.__dict__['_rtevalCfgSection__cfgdata'] = section_cfg
        self.__dict__['_rtevalCfgSection__iter_list'] = None


    def __str__(self):
        "Simple method for dumping config when object is used as a string"
        if len(self.__cfgdata) == 0:
            return "# empty"
        return "\n".join(["%s: %s" % (k,v) for k,v in self.__cfgdata.items()]) + "\n"


    def __setattr__(self, key, val):
        self.__cfgdata[key] = val


    def __getattr__(self, key):
        if key in self.__cfgdata.keys():
            return self.__cfgdata[key]
        return None


    def items(self):
        return self.__cfgdata.items()


    def __iter__(self):
        "Initialises the iterator loop"
        self.__dict__['_rtevalCfgSection__iter_list'] = self.__cfgdata.keys()
        return self


    def next(self):
        "Function used by the iterator"

        if not self.__dict__['_rtevalCfgSection__iter_list'] \
                or len(self.__dict__['_rtevalCfgSection__iter_list']) == 0:
            raise StopIteration
        else:
            elmt = self.__dict__['_rtevalCfgSection__iter_list'].pop()

            # HACK: This element shouldn't really appear here ... why!??!
            while (elmt == '_rtevalCfgSection__cfgdata') and \
                    (len(self.__dict__['_rtevalCfgSection__iter_list']) > 0):
                elmt = self.__dict__['_rtevalCfgSection__iter_list'].pop()

            return (elmt, self.__cfgdata[elmt])


    def has_key(self, key):
        "has_key() wrapper for the configuration data"
        return self.__cfgdata.has_key(key)


    def keys(self):
        "keys() wrapper for configuration data"
        return self.__cfgdata.keys()


    def setdefault(self, key, defvalue):
        if not self.__cfgdata.has_key(key):
            self.__cfgdata[key] = defvalue
        return self.__cfgdata[key]


    def update(self, newdict):
        if type(newdict) is not dict:
            raise TypeError('update() method expects a dict as argument')

        for key, val in newdict.iteritems():
            self.__cfgdata[key] = val


    def wipe(self):
        self.__cfgdata = {}



class rtevalConfig(object):
    "Config parser for rteval"

    def __init__(self, initvars = None, logger = None):
        self.__config_data = {}
        self.__config_files = []
        self.__logger = logger

        # Import the default config first
        for sect, vals in default_config.items():
            self.__update_section(sect, vals)

        # Set the runtime provided init variables
        if initvars:
            if type(initvars) is not dict:
                raise TypeError('initvars argument is not a dict variable')

            for sect, vals in initvars.items():
                self.__update_section(sect, vals)


    def __update_section(self, section, newvars):
        if not section or not newvars:
            return

        if not self.__config_data.has_key(section):
            self.__config_data[section] = rtevalCfgSection(newvars)
        else:
            self.__config_data[section].update(newvars)


    def __str__(self):
        "Simple method for dumping config when object is used as a string"
        ret = ""
        for sect in self.__config_data.keys():
            ret += "[%s]\n%s\n" % (sect, str(self.__config_data[sect]))
        return ret


    def __info(self, str):
        if self.__logger:
            self.__logger.log(Log.INFO, str)


    def __find_config(self):
        "locate a config file"

        for f in ('rteval.conf', '/etc/rteval.conf'):
            p = os.path.abspath(f)
            if os.path.exists(p):
                self.__info("found config file %s" % p)
                return p
        raise RuntimeError, "Unable to find configfile"


    def Load(self, fname = None, append = False):
        "read and parse the configfile"

        try:
            cfgfile = fname or self.__find_config()
        except:
            self.__info("no config file")
            return

        if self.ConfigParsed(cfgfile) is True:
            # Don't try to reread this file if it's already been parsed
            return

        self.__info("reading config file %s" % cfgfile)
        ini = ConfigParser.ConfigParser()
        ini.optionxform = str
        ini.read(cfgfile)

        # wipe any previously read config info
        if not append:
            for s in self.__config_data.keys():
                self.__config_data[s].wipe()

        # copy the section data into the __config_data dictionary
        for s in ini.sections():
            cfg = {}
            for (k,v) in ini.items(s):
                cfg[k] = v.split('#')[0].strip()

            self.__update_section(s, cfg)


        # Register the file as read
        self.__config_files.append(cfgfile)
        return cfgfile


    def ConfigParsed(self, fname):
        "Returns True if the config file given by name has already been parsed"
        return self.__config_files.__contains__(fname)


    def UpdateFromOptionParser(self, parser):
        "Parse through the command line options and update the appropriate config settings"

        last_sect = None
        for sk,v in sorted(vars(parser.values).items()):
            # optparse key template: {sectionname}___{key}
            k = sk.split('___')
            if k[0] != last_sect:
                # If the section name changed, retrieve the section variables
                try:
                    sect = self.GetSection(k[0])
                except KeyError:
                    # If section does not exist, create it
                    self.AppendConfig(k[0], {k[1]: v})
                    sect = self.GetSection(k[0])

                last_sect = k[0]

            setattr(sect, k[1], v)


    def AppendConfig(self, section, cfgvars):
        "Add more config parameters to a section.  cfgvars must be a dictionary of parameters"
        self.__update_section(section, cfgvars)


    def HasSection(self, section):
        return self.__config_data.has_key(section)


    def GetSection(self, section):
        try:
            # Return a new object with config settings of a given section
            return self.__config_data[section]
        except KeyError, err:
            raise KeyError("The section '%s' does not exist in the config file" % section)


def unit_test(rootdir):
    try:
        l = Log()
        l.SetLogVerbosity(Log.INFO)
        cfg = rtevalConfig(logger=l)
        cfg.Load(os.path.join(rootdir, 'rteval.conf'))
        print cfg
        return 0
    except Exception, e:
        print "** EXCEPTION %s", str(e)
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(unit_test('..'))
