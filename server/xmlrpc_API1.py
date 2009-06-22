import bz2
import base64
import libxml2

class rteval_service:
    def __init__(self, logger=None):
        self.decompr = bz2.BZ2Decompressor()
        self.log = logger

    def SendReport(self, xmlb64):
        xmldoc = libxml2.parseDoc(self.decompr.decompress(base64.b64decode(xmlb64)))
        xmldoc.saveFormatFileEnc('-','UTF-8',1)
        return "OK"
