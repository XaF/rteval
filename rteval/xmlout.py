# -*- coding: utf-8 -*-
#!/usr/bin/python -tt
import os
import sys
import libxml2
import libxslt
import codecs

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


    def __del__(self):
        if self.level > 0:
            raise RuntimeError, "XMLOut: open blocks at close"
        self.xmldoc.freeDoc()


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
        else:
            # Load XSLT file and prepare the XSLT parser
            xsltdoc = libxml2.parseFile(xslt)
            parser = libxslt.parseStylesheetDoc(xsltdoc)

            # imitate libxml2's filename interpretation
            if filename != "-":
                dstfile = codecs.open(filename, "w", encoding=self.encoding)
            else:
                dstfile = sys.stdout
            #
            # Parse XML+XSLT and write the result to file
            #
            resdoc = parser.applyStylesheet(self.xmldoc, None)
            # Decode the result string according to the charset declared in the XSLT file
            xsltres = parser.saveResultToString(resdoc).decode(parser.encoding())
            #  Write the file with the requested output encoding
            dstfile.write(xsltres.encode(self.encoding))

            if dstfile != sys.stdout:
                dstfile.close()

            # Clean up
            resdoc.freeDoc()
            xsltdoc.freeDoc()


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
    x = XMLOut('rteval', {'version':"1.0"}, 'UTF-8')
    x.openblock('run_info', {'days': 0, 'hours': 0, 'minutes': 32, 'seconds': 18})
    x.taggedvalue('time', '11:22:33')
    x.taggedvalue('date', '2000-11-22')
    x.closeblock()
    x.openblock('uname')
    x.taggedvalue('node', u'testing - \xe6\xf8')
    x.taggedvalue('kernel', 'my_test_kernel', {'is_RT': 0})
    x.taggedvalue('arch', 'mips')
    x.closeblock()
    x.openblock('hardware')
    x.taggedvalue('cpu_cores', 2)
    x.taggedvalue('memory_size', 1024*1024*2)
    x.closeblock()
    x.openblock('loads', {'load_average': 3.29})
    x.taggedvalue('command_line','./load/loader --extreme --ultimate --threads 4096', {'name': 'heavyloader'})
    x.taggedvalue('command_line','dd if=/dev/zero of=/dev/null', {'name': 'lightloader'})
    x.closeblock()
    x.close()
    print "------------- XML OUTPUT ----------------------------"
    x.Write("-")
    print "------------- XSLT PARSED OUTPUT --------------------"
    x.Write("-", "rteval_text.xsl")
