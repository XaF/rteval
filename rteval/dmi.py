#!/usr/bin/python -tt
#
#   dmi.py - class to wrap DMI Table information
#
#   Copyright 2009   Clark Williams <williams@redhat.com>
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
import subprocess
sys.pathconf = "."
import xmlout
import libxml2
import libxslt
import dmidecode

class DMIinfo(object):
    '''class used to obtain DMI info via python-dmidecode'''

    def __init__(self, config):
        self.version = '0.3'
        self.smbios = None
        self.sharedir = config.installdir

        self.dmixml = dmidecode.dmidecodeXML()
        self.smbios = dmidecode.dmi.replace('SMBIOS ', '').replace(' present', '')

        xsltdoc = self.__load_xslt('rteval_dmi.xsl')
        self.xsltparser = libxslt.parseStylesheetDoc(xsltdoc)


    def __load_xslt(self, fname):
        if os.path.exists(fname):
            return libxml2.parseFile(fname)
        elif os.path.exists(self.sharedir + '/' + fname):
            return libxml2.parseFile(self.sharedir + '/' + fname)
        else:
            raise RuntimeError, 'Could not locate XSLT template for DMI data (%s)' % fname

    def genxml(self, xml):
        self.dmixml.SetResultType(dmidecode.DMIXML_DOC)
        resdoc = self.xsltparser.applyStylesheet(self.dmixml.QuerySection('all'), None)
        node = resdoc.getRootElement().copyNode(1)
        node.newProp("DMIinfo_version", self.version)
        xml.AppendXMLnodes(node)


if __name__ == '__main__':
    from pprint import pprint
    
    d = DMIinfo('.')
    x = xmlout.XMLOut('dmi_test', "0.0")
    x.NewReport()
    d.genxml(x)
    x.close()
    x.Write('-')
