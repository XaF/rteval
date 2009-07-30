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
import hashlib
import StringIO
import types

class XMLSQLparser(object):
    "Class for parsing XML into SQL using an XSLT template for mapping data fields"

    def __init__(self, xslt, xml):
        self.xml = self.__get_xml_data(xml)

        # Verify that this is a valid rteval XML file
        try:
            ver = float(self.xml.xpathEval('/rteval/@version')[0].content)
            if ver < 0.8:
                raise Exception, 'Unsupported rteval XML version'
        except Exception, err:
            raise Exception, 'Input file was unparsable or not a valid rteval XML file (%s)' % str(err)

        xsltdoc = self.__get_xml_data(xslt)
        self.parser = libxslt.parseStylesheetDoc(xsltdoc)


    def __get_xml_data(self, input):
        if hasattr(input, '__module__') and (input.__module__ == 'libxml2') and hasattr(input, 'get_type'):
            if input.get_type() == 'document_xml':
                # It's an XML document, use it directly
                return input
            elif input.get_type() == 'element':
                # It's an XML node, create a document and set node as root
                xmldoc = libxml2.newDoc("1.0")
                xmldoc.setRootElement(input)
                return xmldoc
        elif type(input) == types.StringType:
            # It's a string, assume a file name
            return libxml2.parseFile(input)

        # If invalid input ...
        raise AttributeError, "Unknown input type for XML/XSLT data (not a filename, xmlDoc or xmlNode)"


    def __xmlNode2string(self, node):
        doc = libxml2.newDoc('1.0')
        doc.setRootElement(node)

        iobuf = StringIO.StringIO()
        xmlbuf = libxml2.createOutputBuffer(iobuf, 'UTF-8')
        doc.saveFileTo(xmlbuf, 'UTF-8')
        retstr = iobuf.getvalue()
        del doc
        del xmlbuf
        del iobuf
        return retstr


    def GetSQLdata(self, tbl, rterid=None, syskey=None, report_filename=None):
        params = { 'table': '"%s"' % tbl,
                   'rterid': rterid and '"%i"' % rterid,
                   'syskey': syskey and '"%i"' % syskey,
                   'report_filename': report_filename and '"%s"' % report_filename }
        resdoc = self.parser.applyStylesheet(self.xml, params)

        # Extract fields, and make sure they are ordered/sorted by the fid attribute
        fields = []
        tmp_fields = {}
        for f in resdoc.xpathEval('/sqldata/fields/field'):
            tmp_fields[int(f.prop('fid'))] = f.content

        for f in range(0, len(tmp_fields)):
            fields.append(tmp_fields[f])

        # Extract values, make sure they are in the same order as the field values
        records = []
        for r in resdoc.xpathEval('/sqldata/records/record'):
            rvs = {}
            for v in r.xpathEval('value'):
                if v.prop('type') == 'xmlblob':
                    fieldval = self.__xmlNode2string(v.children)
                elif v.prop('isnull') == '1':
                    fieldval = None
                else:
                    fieldval = v.content

                if v.hasProp('hash') and fieldval is not None:
                    try:
                        hash = getattr(hashlib, v.prop('hash'))
                    except AttributeError:
                        raise Exception, 'Unsuported hash algoritm: %s' % v.prop('hash')

                    rvs[int(v.prop('fid'))] = hash(fieldval).hexdigest()
                else:
                    rvs[int(v.prop('fid'))] = fieldval

            # Make sure the field values are in the correct order
            vls = []
            for v in range(0, len(rvs)):
                vls.append(rvs[v])

            # Append all these field values as a record
            records.append(vls)

        result = { 'table': resdoc.xpathEval('/sqldata/@table')[0].content,
                   'fields': fields, 'records': records}

        # Extract the key field being returned from INSERT statements, if set
        try:
            retkey = resdoc.xpathEval('/sqldata/@key')
            if retkey and retkey[0] and retkey[0].content:
                result['returning'] = retkey[0].content
        except:
            pass

        resdoc.freeDoc()
        return result

