# -*- coding: utf-8 -*-
#!/usr/bin/python -tt
import os
import sys
import libxml2

class XMLOut(object):
    '''Class to create XML output'''
    def __init__(self, roottag, attr, encoding='UTF-8'):
        self.encoding = encoding
        self.xmldoc = libxml2.newDoc("1.0")
        self.xmlroot = libxml2.newNode(roottag)
        self.__add_attributes(self.xmlroot, attr)
        self.currtag = self.xmlroot
        self.level = 0
        self.closed = False


    def __encode(self, value):
        if type(value) is unicode:
            val = value
        elif type(value) is str:
            val = unicode(value)
        else:
            val = unicode(str(value))

        # libxml2 uses UTF-8 internally and must have
        # all input as UTF-8.
        return val.encode('utf-8')


    def __add_attributes(self, node, attr):
        if attr is not None:
            for k, v in attr.iteritems():
                node.newProp(k, self.__encode(v))


    def close(self):
        if self.closed:
            raise RuntimeError, "XMLOut: XML document already closed"
        if self.level > 0:
            raise RuntimeError, "XMLOut: open blocks at close"
        self.xmldoc.setRootElement(self.xmlroot)
        self.closed = True


    def Write(self, filename, xslt = None):
        if not self.closed:
            raise RuntimeError, "XMLOut: XML document is not closed"

        if xslt == None:
            # If no XSLT template is give, write raw XML
            self.xmldoc.saveFormatFileEnc(filename, self.encoding, 1)
            return

    def __del__(self):
        if self.level > 0:
            raise RuntimeError, "XMLOut: open blocks at close"


    def openblock(self, tagname, attributes=None):
        ntag = libxml2.newNode(tagname);
        self.__add_attributes(ntag, attributes)
        self.currtag.addChild(ntag)
        self.currtag = ntag
        self.level += 1


    def closeblock(self):
        if self.level == 0:
            raise RuntimeError, "XMLOut: no open tags to close"
        self.currtag = self.currtag.get_parent()
        self.level -= 1


    def taggedvalue(self, tag, value, attributes=None):
        ntag = self.currtag.newTextChild(None, tag, self.__encode(value))
        self.__add_attributes(ntag, attributes)


if __name__ == '__main__':
    x = XMLOut('test_xml', {'version':"1.0"})
    x.openblock('test', {'testattr': "yes", 'works': "hopefully"})
    x.taggedvalue('foo', 'bar')
    x.taggedvalue('baz', 'frooble', {'attrvalue':"1.0"})
    x.openblock('subtag', {'level': 1})
    x.openblock('subtag', {'level': 2})
    x.taggedvalue('value','another value')
    x.closeblock()
    x.closeblock()
    x.closeblock()
    x.taggedvalue('node2',u'yet another value \xe6\xf8', {'shortvalue': "yav"})
    x.close()
    x.Write("-")
