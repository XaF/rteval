#!/usr/bin/python -tt
import os
import sys

class XMLOut(object):
    '''Class to create XML output'''
    def __init__(self, filename, encoding='UTF-8', standalone=True):
        self.filename = filename
        self.encoding = encoding
        if standalone:
            self.standalone = 'yes'
        else:
            self.standalone = 'no'
        self.indent = 0
        self.indentchar = '\t'
        self.blocktags = []
        self.handle = open(filename, 'w')
        self.handle.write('<?xml version="1.0" encoding="%s" standalone="%s"?>\n'
                          % (self.encoding, self.standalone))

    def close(self):
        if self.indent:
            raise RuntimeError, "XMLOut: open blocks at close: %s" % " ".join(self.blocktags)
        self.handle.close()

    def __del__(self):
        if self.indent != 0:
            raise RuntimeError, "XMLOut: open blocks at close: %s" % " ".join(self.blocktags)

    def __indent(self):
        return self.indentchar * self.indent

    def __attributes(self, attributes):
        astr = ''
        if attributes:
            if isinstance(attributes, dict):
                for a in attributes.keys():
                    astr = astr + ' %s="%s"' % (a, attributes[a])
            elif isinstance(attributes, list) or isinstance(attributes, tuple):
                astr = ' ' + ' '.join(attributes)
        return astr

    def openblock(self, tag, attributes=None):
        astr = self.__attributes(attributes)
        self.handle.write('%s<%s%s>\n' % (self.__indent(), tag, astr))
        self.indent += 1
        self.blocktags.append(tag)

    def closeblock(self):
        self.indent -= 1
        tag = self.blocktags.pop()
        self.handle.write('%s</%s>\n' % (self.__indent(), tag))

    def taggedvalue(self, tag, value, attributes=None):
        astr = self.__attributes(attributes)
        self.handle.write('%s<%s%s>%s</%s>\n' % (self.__indent(), tag, astr, value, tag))


if __name__ == '__main__':
    x = XMLOut('test.xml')
    x.openblock('test', {'version':"1.0"})
    x.taggedvalue('foo', 'bar')
    x.taggedvalue('baz', 'frooble', {'version':'1.0'})
    x.closeblock()
    x.close()
