#!/usr/bin/python -tt

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

    def __init__(self, sharedir):
        self.version = '0.3'
        self.smbios = None
        self.sharedir = sharedir

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
