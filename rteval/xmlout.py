# -*- coding: utf-8 -*-
#!/usr/bin/python -tt
import os
import sys
import libxml2
import libxslt
import codecs


class XMLOut(object):
    '''Class to create XML output'''
    def __init__(self, roottag, version, attr = None, encoding='UTF-8'):
        self.encoding = encoding
        self.roottag = self.__fixtag(roottag)
        self.rootattr = attr
        self.version = version
        self.status = 0    # 0 - no report created/loaded, 1 - new report, 2 - loaded report, 3 - XML closed


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


    def __fixtag(self, tagname):
        tmp = tagname.replace(' ', '_')
        return tmp.replace('\t', '_')

    def close(self):
        if self.status == 0:
            raise RuntimeError, "XMLOut: No XML document is created nor loaded"
        if self.status == 3:
            raise RuntimeError, "XMLOut: XML document already closed"
        if self.level > 0:
            raise RuntimeError, "XMLOut: open blocks at close"

        if self.status == 1: # Only set the root node in the doc on created reports (NewReport called)
            self.xmldoc.setRootElement(self.xmlroot)
        self.status = 3


    def NewReport(self):
        if self.status != 0 and self.status != 3:
            raise RuntimeError, "XMLOut: Cannot start a new report without closing the currently opened one"

        if self.status == 3:
            self.xmldoc.freeDoc() # Free the report from memory if we have one already

        self.xmldoc = libxml2.newDoc("1.0")
        self.xmlroot = libxml2.newNode(self.roottag)
        self.__add_attributes(self.xmlroot, {'version': self.version})
        self.__add_attributes(self.xmlroot, self.rootattr)
        self.currtag = self.xmlroot
        self.level = 0
        self.status = 1


    def LoadReport(self, filename, validate_version = False):
        if self.status == 3:
            self.xmldoc.freeDoc() # Free the report from memory if we have one already

        self.xmldoc = libxml2.parseFile(filename)
        if self.xmldoc.name != filename:
            self.status = 3
            raise RuntimeError, "XMLOut: Loading report failed"

        root = self.xmldoc.children
        if root.name != self.roottag:
            self.status = 3
            raise RuntimeError, "XMLOut: Loaded report is not a valid %s XML file" % self.roottag

        if validate_version is True:
            ver = root.hasProp('version')

            if ver is None:
                self.status = 3
                raise RuntimeError, "XMLOut: Loaded report is missing version attribute in root node"

            if ver.getContent() != self.version:
                self.status = 3
                raise RuntimeError, "XMLOut: Loaded report is not of version %s" % self.version

        self.status = 2 # Confirm that we have loaded a report from file

    def Write(self, filename, xslt = None):
        if self.status != 2 and self.status != 3:
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
        if self.status != 1:
            raise RuntimeError, "XMLOut: openblock() cannot be called before NewReport() is called"
        ntag = libxml2.newNode(self.__fixtag(tagname));
        self.__add_attributes(ntag, attributes)
        self.currtag.addChild(ntag)
        self.currtag = ntag
        self.level += 1


    def closeblock(self):
        if self.status != 1:
            raise RuntimeError, "XMLOut: closeblock() cannot be called before NewReport() is called"
        if self.level == 0:
            raise RuntimeError, "XMLOut: no open tags to close"
        self.currtag = self.currtag.get_parent()
        self.level -= 1


    def taggedvalue(self, tag, value, attributes=None):
        if self.status != 1:
            raise RuntimeError, "XMLOut: taggedvalue() cannot be called before NewReport() is called"
        ntag = self.currtag.newTextChild(None, self.__fixtag(tag), self.__encode(value))
        self.__add_attributes(ntag, attributes)


if __name__ == '__main__':
    x = XMLOut('rteval', '0.6', None, 'UTF-8')
    x.NewReport()
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
    print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
    x.LoadReport("latency.xml", True)
    x.Write("-")
    x.Write("-", "rteval_text.xsl")
