#
#   dmi.py - class to wrap DMI Table information
#
#   Copyright 2009 - 2013   Clark Williams <williams@redhat.com>
#   Copyright 2009 - 2013   David Sommerseth <davids@redhat.com>
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
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#   For the avoidance of doubt the "preferred form" of this code is one which
#   is in an open unpatent encumbered format. Where cryptographic key signing
#   forms part of the process of creating an executable the information
#   including keys needed to generate an equivalently functional executable
#   are deemed to be part of the source code.
#

import sys, os
import libxml2, lxml.etree
from rteval import rtevalConfig, xmlout
from rteval.Log import Log

try:
    import dmidecode
    dmidecode_loaded = True
except:
    dmidecode_loaded = False
    pass

def ProcessWarnings():
    
    if not hasattr(dmidecode, 'get_warnings'):
        return

    warnings = dmidecode.get_warnings()
    if warnings == None:
        return

    for warnline in warnings.split('\n'):
        # Ignore these warnings, as they are "valid" if not running as root
        if warnline == '/dev/mem: Permission denied':
            continue
        if warnline == 'No SMBIOS nor DMI entry point found, sorry.':
            continue

        # All other warnings will be printed
        if len(warnline) > 0:
            print "** DMI WARNING ** %s" % warnline

    dmidecode.clear_warnings()


class DMIinfo(object):
    '''class used to obtain DMI info via python-dmidecode'''

    def __init__(self, config, logger):
        self.__version = '0.5'

        if not dmidecode_loaded:
            logger.log(Log.DEBUG|Log.WARN, "No dmidecode module found, ignoring DMI tables")
            self.__fake = True
            return

        self.__fake = False
        self.__dmixml = dmidecode.dmidecodeXML()

        self.__xsltparser = self.__load_xslt('rteval_dmi.xsl')


    def __load_xslt(self, fname):
        xsltfile = None
        if os.path.exists(fname):
            xsltfile = open(fname, "r")
        elif rtevalConfig.default_config_search([fname], os.path.isfile):
            xsltfile = open(rtevalConfig.default_config_search([fname], os.path.isfile), "r")

        if xsltfile:
            xsltdoc = lxml.etree.parse(xsltfile)
            ret = lxml.etree.XSLT(xsltdoc)
            xsltfile.close()
            return ret

        raise RuntimeError, 'Could not locate XSLT template for DMI data (%s)' % (self.sharedir + '/' + fname)


    def MakeReport(self):
        rep_n = libxml2.newNode("DMIinfo")
        rep_n.newProp("version", self.__version)
        if self.__fake:
            rep_n.addContent("No DMI tables available")
            rep_n.newProp("not_available", "1")
        else:
            self.__dmixml.SetResultType(dmidecode.DMIXML_DOC)
            dmiqry = xmlout.convert_libxml2_to_lxml_doc(self.__dmixml.QuerySection('all'))
            resdoc = self.__xsltparser(dmiqry)
            dmi_n = xmlout.convert_lxml_to_libxml2_nodes(resdoc.getroot())
            rep_n.addChild(dmi_n)
        return rep_n



def unit_test(rootdir):
    from pprint import pprint

    class unittest_ConfigDummy(object):
        def __init__(self, rootdir):
            self.config = {'installdir': '/usr/share/rteval'}
            self.__update_vars()

        def __update_vars(self):
            for k in self.config.keys():
                self.__dict__[k] = self.config[k]

    try:
        ProcessWarnings()
        if os.getuid() != 0:
            print "** ERROR **  Must be root to run this unit_test()"
            return 1

        log = Log()
        log.SetLogVerbosity(Log.DEBUG|Log.INFO)
        cfg = unittest_ConfigDummy(rootdir)
        d = DMIinfo(cfg, log)
        dx = d.MakeReport()
        x = libxml2.newDoc("1.0")
        x.setRootElement(dx)
        x.saveFormatFileEnc("-", "UTF-8", 1)
        return 0
    except Exception, e:
        print "** EXCEPTION: %s" % str(e)
        return 1

if __name__ == '__main__':
    sys.exit(unit_test('.'))
