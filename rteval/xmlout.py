#!/usr/bin/python -tt
import os
import sys
import xml.dom.ext
import xml.dom.minidom


class XMLOut(object):
    '''Class to create XML output'''
    def __init__(self, roottag, attr, encoding='UTF-8'):
        self.xmldoc = xml.dom.minidom.Document()

        self.xmlroot = self.xmldoc.createElement(roottag)
        self.__add_attributes(self.xmlroot, attr)
        self.currtag = self.xmlroot
        self.level = 0
        self.closed = False
        self.encoding = encoding


    def __add_attributes(self, node, attr):
        if attr is not None:
            for k, v in attr.iteritems():
                node.setAttribute(k, str(v))


    def close(self):
        if self.level > 0:
            raise RuntimeError, "XMLOut: open blocks at close"
        self.xmldoc.appendChild(self.currtag)
        self.closed = True


    def Write(self, file, xslt = None):
        if not self.closed:
            raise RuntimeError, "XMLOut: XML file is not closed"

        if xslt == None:
            # If no XSLT template is give, write raw XML
            file.write(self.xmldoc.toxml(encoding=self.encoding))
            return


    def __del__(self):
        if self.level > 0:
            raise RuntimeError, "XMLOut: open blocks at close"


    def openblock(self, tagname, attributes=None):
        ntag = self.xmldoc.createElement(tagname);
        self.__add_attributes(ntag, attributes)
        self.currtag.appendChild(ntag)
        self.currtag = ntag
        self.level += 1


    def closeblock(self):
        if self.level == 0:
            raise RuntimeError, "XMLOut: no open tags to close"
        self.currtag = self.currtag.parentNode
        self.level -= 1


    def taggedvalue(self, tag, value, attributes=None):
        ntag = self.xmldoc.createElement(tag)
        self.__add_attributes(ntag, attributes)
        ntag.appendChild(self.xmldoc.createTextNode(str(value)))
        self.currtag.appendChild(ntag)



if __name__ == '__main__':
    x = XMLOut('rteval', {'version':"1.0"})
    x.openblock('test', {'testattr': "yes", 'works': "hopefully"})
    x.taggedvalue('foo', 'bar')
    x.taggedvalue('baz', 'frooble', {'version':'1.0'})
    x.openblock('subtag', {'level': "1"})
    x.openblock('subtag', {'level': "2"})
    x.taggedvalue('value','another value')
    x.closeblock()
    x.closeblock()
    x.closeblock()
    x.close()
    x.Write(sys.stdout)
