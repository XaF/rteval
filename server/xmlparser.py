#
#   xmlparser.py
#   Library for parsing rteval XML files
#
#   Copyright 2009      David Sommerseth <davids@redhat.com>
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

import libxml2
import libxslt
import psycopg2
import hashlib
import StringIO

class rtevalXMLparser(object):
    "Class for parsing XML data from rteval runs"

    def __init__(self, fname):
        self.xml = libxml2.parseFile(fname)

        # Verify that this is a valid rteval XML file
        try:
            ver = float(self.xml.xpathEval('/rteval/@version')[0].content)
            if ver < 0.8:
                raise Exception, "Unsupported rteval XML version"
        except Exception, err:
            raise Exception, "Input file was unparsable or not a valid rteval XML file (%s)" % str(err)


    def GetSysID(self):
        try:
            uuid  = self.xml.xpathEval('/rteval/HardwareInfo/@SystemUUID')[0].content
            serno = self.xml.xpathEval('/rteval/HardwareInfo/@SerialNo')[0].content
        except:
            raise Exception, "Could not retrieve SystemUUID or SerialNo from XML data"

        return hashlib.sha1("%s:%s" % (uuid,serno)).hexdigest()


    def GetDMIdata(self):
        try:
            dmi = self.xml.xpathEval('/rteval/HardwareInfo')[0]
            if dmi == None:
                raise Exception, "Could not locate HardwareInfo in XML data"
        except:
            raise Exception, "Could not locate HardwareInfo in XML data"

        # Create a new XML document and put the /rteval/HardwareInfo as doc root
        doc = libxml2.newDoc("1.0")
        doc.setRootElement(dmi)
        
        # Dump this XMLdoc as a string
        fbuf = StringIO.StringIO()
        xmlbuf = libxml2.createOutputBuffer(fbuf, 'UTF-8')
        doc.saveFormatFileTo(xmlbuf, 'UTF-8', 0)
        retstr = fbuf.getvalue()
        doc.free()
        del xmlbuf
        del fbuf
        del doc

        # Return the information as a string
        return retstr

    def GetNodeName(self):
        try:
            nodename = self.xml.xpathEval('/rteval/uname/node')[0].content
        except Exception, err:
            raise Exception, "Could not retrieve node name (%s)" % str(err)

        return nodename

    def GetSQLdata_systems(self):
        return {"table": "systems",
                "columns": ["sysid","dmidata"],
                "values: ", [self.GetSysID(), self.GetDMIdata()]}

    def GetSQLdata_syshostname(self, syskey, ipaddr):
        return {"table": "systems",
                "columns": ["syskey", "hostname", "ipaddr"],
                "values: ", [syskey, self.GetNodeName, ipaddr]}

    

    
