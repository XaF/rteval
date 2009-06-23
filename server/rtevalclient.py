import xmlrpclib
import libxml2
import StringIO
import bz2
import base64

class rtevalclient:
    # FIXME: better setup of host to connect to
    def __init__(self, url="http://localhost:65432/rteval/API1"):
        self.srv = xmlrpclib.ServerProxy(url)


    def SendReport(self, xmldoc):
        # FIXME: Check if xmldoc really is an XMLdoc
        fbuf = StringIO.StringIO()
        xmlbuf = libxml2.createOutputBuffer(fbuf, 'UTF-8')
        xmldoc.saveFileTo(xmlbuf, 'UTF-8')

        compr = bz2.BZ2Compressor(9)
        compr.compress(fbuf.getvalue())
        data = base64.b64encode(compr.flush())
        print "Sending %i bytes" % len(data)
        return self.srv.SendReport(data)


    def SendDataAsFile(self, fname, data, decompr = False):
        compr = bz2.BZ2Compressor(9)
        compr.compress(data)
        comprdata = base64.b64encode(compr.flush())
        return self.srv.StoreRawFile(fname, comprdata, decompr)


    def SendFile(self, fname, decompr = False):
        f = open(fname, "r")
        srvname = self.SendDataAsFile(fname, f.read(), decompr)
        f.close()
        return srvname

