import os
import bz2
import base64
import libxml2
import string
import inspect

from pprint import pprint
class rteval_service():
    def __init__(self, logger=None):
        self.decompr = bz2.BZ2Decompressor()
        self.log = logger

        # Some defaults
        self.dataroot = "rtevald/uploads"
        self.fnametrans = string.maketrans("/\\", "::") # replace path delimiters in filenames


    def __mkdatadir(self, dirpath):
        startdir = os.getcwd()
        for dir in dirpath.split("/"):
            if not os.path.exists(dir):
                os.mkdir(dir, 0700)
            os.chdir(dir)
        os.chdir(startdir)


    def __getfilename(self, fname, comp):
        idx = 0
        if comp:
            filename = "%s/%s.bz2" % (self.dataroot, fname.translate(self.fnametrans))
        else:
            filename = "%s/%s" % (self.dataroot, fname.translate(self.fnametrans))

        while 1:
            if not os.path.exists(filename):
                return filename
            idx += 1
            if comp:
                filename = "%s/%s-{%i}.bz2" % (self.dataroot, fname.translate(self.fnametrans), idx)
            else:
                filename = "%s/%s-{%i}" % (self.dataroot, fname.translate(self.fnametrans), idx)


    def _dispatch(self, method, params):
        # debugging
        pprint(method)
        pprint(params)
        print "-"*80

        # Call the method requested
        # FIXME: Improve checking for valid methods
        func = getattr(self, method)
        return func(*params)


    def SendReport(self, xmlbzb64):
        xmldoc = libxml2.parseDoc(self.decompr.decompress(base64.b64decode(xmlbzb64)))

        # FIXME:  Do something clever with received XMLdoc, than to just dump the contents
        xmldoc.saveFormatFileEnc('-','UTF-8',1)

        return True


    def StoreRawFile(self, filename, bzb64data, decomp):
        if decomp is True:
            data = self.decompr.decompress(base64.b64decode(bzb64data))
        else:
            data = base64.b64decode(bzb64data)

        # Make sure we have a directory to write files into
        self.__mkdatadir(self.dataroot)

        # Get a unique filename, as close as possible to the input filename
        fname = self.__getfilename(filename, not decomp)

        # Save and return filename used server side
        f = open(fname, "w")
        f.write(data)
        f.close()
        return fname
