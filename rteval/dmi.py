#!/usr/bin/python -tt

import sys
import os
import subprocess
sys.pathconf = "."
import xmlout

typenames = {
    0:"BIOS Information",
    1:"System Information",
    2:"Base Board Information",
    3:"Chassis Information",
    4:"Processor Information",
    5:"Memory Controller Information",
    6:"Memory Module Information",
    7:"Cache Information",
    8:"Port Connector Information",
    9:"System Slots",
    10:"On Board Devices Information",
    11:"OEM Strings",
    12:"System Configuration Options",
    13:"BIOS Language Information",
    14:"Group Associations",
    15:"System Event Log",
    16:"Physical Memory Array",
    17:"Memory Device",
    18:"32-bit Memory Error Information",
    19:"Memory Array Mapped Address",
    20:"Memory Device Mapped Address",
    21:"Built-in Pointing Device",
    22:"Portable Battery",
    23:"System Reset",
    24:"Hardware Security",
    25:"System Power Controls",
    26:"Voltage Probe",
    27:"Cooling Device",
    28:"Temperature Probe",
    29:"Electrical Current Probe",
    30:"Out-of-Band Remote Access",
    31:"Boot Integrity Services (BIS) Entry Point",
    32:"System Boot Information",
    33:"64-bit Memory Error Information",
    34:"Management Device",
    35:"Management Device Component",
    36:"Management Device Threshold Data",
    37:"Memory Channel",
    38:"IPMI Device Information",
    39:"System Power Supply",
    40:"Additional Information",
    41:"Onboard Devices Extended Information",
    126:"Inactive",
    127:"End-of-Table",
}

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
                            {'handle':d['dmi_handle'], 
                             'type':d['dmi_type'], 
                             'description':typenames[int(d['dmi_type'])],
                             'size':d['dmi_size']
                             })
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
