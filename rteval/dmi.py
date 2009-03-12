#!/usr/bin/python -tt

import sys
import os
import subprocess
sys.pathconf = "."
import xmlout

class DMIinfo(object):
    '''class used to obtain DMI info via the 'dmidecode' utility'''

    def __init__(self):
        self.dmi = None
        self.sections = ('bios', 'system', 'processor', 'baseboard',
                         'memory', 'cache', 'chassis', 'connector',
                         'slot')
        try:
            import dmidecode
            self.dmi = dmidecode.dmi
            self.section = {}
            for s in self.sections:
                self.section[s] = dmidecode.__dict__[s]()
        except:
            self.dmi = "no information available"


    def xmlformat(self, x, d, name=None):
        if not d: return
        if isinstance(d, dict):
            self.xmldict(x, d, name)
        elif isinstance(d, list):
            self.xmllist(x, d, name)
        else:
            if name:
                x.taggedvalue(name, d)
            else:
                x.taggedvalue('item', d)

    def xmllist(self, x, d, name=None):
        if name:
            x.openblock(name)
        for v in d:
            self.xmlformat(x, v)
        if name:
            x.closeblock()

    def xmldict(self, x, d, name=None):
        if name:
            if name.find('0x') != -1:
                x.openblock('Section', 
                            {'handle':d['dmi_handle'], 'type':d['dmi_type'], 'size':d['dmi_size']})
                del d['dmi_type']
                del d['dmi_handle']
                del d['dmi_size']
            else:
                x.openblock(name)

        for k in d.keys():
            if isinstance(d[k], dict):
                self.xmldict(x, d[k], k)
            elif isinstance(d[k], list):
                self.xmllist(x, d[k])
            else:
                x.taggedvalue(k, d[k])
        if name:
            x.closeblock()

    def genxml(self, xml):
        for s in self.sections:
            self.xmlformat(xml, self.section[s], s)
        xml.close()
        xml.Write('-')

if __name__ == '__main__':
    from pprint import pprint
    
    d = DMIinfo()
    x = xmlout.XMLOut('dmi', d.dmi)
    x.NewReport()
    d.genxml(x)
