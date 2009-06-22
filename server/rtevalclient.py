import xmlrpclib
import libxml2
import StringIO
import bz2
import base64

class rtevalclient:
    def __init__(self, url="http://localhost:65432/rteval/API1"):
        self.srv = xmlrpclib.ServerProxy(url)
        self.compr = bz2.BZ2Compressor(9)

    def SendReport(self, xmldoc):
        fbuf = StringIO.StringIO()
        xmlbuf = libxml2.createOutputBuffer(fbuf, 'UTF-8')
        xmldoc.saveFileTo(xmlbuf, 'UTF-8')

        self.compr.compress(fbuf.getvalue())
        data = base64.b64encode(self.compr.flush())
        print "Sending %i bytes" % len(data)
        print "%s", data 
        res = self.srv.SendReport(data)
        print res
