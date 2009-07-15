import xmlrpclib
import libxml2
import StringIO
import bz2
import base64
import platform

class rtevalclient:
    """
    rtevalclient is a library for sending rteval reports to an rteval server via XML-RPC.
    """
    def __init__(self, url="http://localhost:65432/rteval/API1", hostn = None):
        self.srv = xmlrpclib.ServerProxy(url)
        if hostn is None:
            self.hostname = platform.node()
        else:
            self.hostname = hostn


    def SendReport(self, xmldoc):
        if xmldoc.type != 'document_xml':
            raise Exception, "Input is not XML document"

        fbuf = StringIO.StringIO()
        xmlbuf = libxml2.createOutputBuffer(fbuf, 'UTF-8')
        doclen = xmldoc.saveFileTo(xmlbuf, 'UTF-8')

        compr = bz2.BZ2Compressor(9)
        compr.compress(fbuf.getvalue())
        data = base64.b64encode(compr.flush())
        print "rtevalclient::SendReport() - Sending %i bytes (XML document length: %i bytes, compression ratio: %.02f%%)" % (len(data), doclen, (1-(float(len(data)) / float(doclen)))*100 )
        return self.srv.SendReport(self.hostname, data)


    def SendDataAsFile(self, fname, data, decompr = False):
        compr = bz2.BZ2Compressor(9)
        compr.compress(data)
        comprdata = base64.b64encode(compr.flush())
        return self.srv.StoreRawFile(self.hostname, fname, comprdata, decompr)


    def SendFile(self, fname, decompr = False):
        f = open(fname, "r")
        srvname = self.SendDataAsFile(fname, f.read(), decompr)
        f.close()
        return srvname

