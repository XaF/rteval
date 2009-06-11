#!/usr/bin/python -tt

import sys
import os
import subprocess
sys.pathconf = "."
import xmlout

class DMIinfo(object):
    '''class used to obtain DMI info via python-dmidecode'''

    def __init__(self):
        self.version = '0.2'
        self.smbios = None

        import dmidecode
        self.dmixml = dmidecode.dmidecodeXML()
        self.smbios = dmidecode.dmi.replace('SMBIOS ', '').replace(' present', '')

    def genxml(self, xml):
        dmidata_n = self.dmixml.QuerySection('all')
        node = xml.AppendXMLnodes(dmidata_n)
        node.newProp("rteval_DMIinfoVersion", self.version)

if __name__ == '__main__':
    from pprint import pprint
    
    d = DMIinfo()
    x = xmlout.XMLOut('dmi_test', "0.0")
    x.NewReport()
    d.genxml(x)
    x.close()
    x.Write('-')
