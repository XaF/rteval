import os
import bz2
import base64
import libxml2
import string
import inspect

from pprint import pprint
class rteval_service():
    def __init__(self, logger=None):
        self.log = logger

        # Some defaults
        self.dataroot = "rtevald"
        self.fnametrans = string.maketrans("/\\", "::") # replace path delimiters in filenames


    def __mkdatadir(self, dirpath):
        startdir = os.getcwd()
        for dir in dirpath.split("/"):
            if not os.path.exists(dir):
                os.mkdir(dir, 0700)
            os.chdir(dir)
        os.chdir(startdir)


    def __getfilename(self, dir, fname, comp):
        idx = 0
        if comp:
            filename = "%s/%s/%s.bz2" % (self.dataroot, dir, fname.translate(self.fnametrans))
        else:
            filename = "%s/%s/%s" % (self.dataroot, dir, fname.translate(self.fnametrans))

        while 1:
            if not os.path.exists(filename):
                return filename
            idx += 1
            if comp:
                filename = "%s/%s/%s-{%i}.bz2" % (self.dataroot, dir, fname.translate(self.fnametrans), idx)
            else:
                filename = "%s/%s/%s-{%i}" % (self.dataroot, dir, fname.translate(self.fnametrans), idx)


    def _dispatch(self, method, params):
        # Call the method requested
        # FIXME: Improve checking for valid methods
        func = getattr(self, method)
        return func(*params)


    def SendReport(self, clientid, xmlbzb64):
        decompr = bz2.BZ2Decompressor()
        xmldoc = libxml2.parseDoc(decompr.decompress(base64.b64decode(xmlbzb64)))

        # Make sure we have a directory to write files into
        self.__mkdatadir(self.dataroot + '/reports/' + clientid)
        fname = self.__getfilename('reports/' + clientid,'report.xml', False)

        # FIXME:  Do something more clever with received XMLdoc, than to just dump the contents
        xmldoc.saveFormatFileEnc(fname,'UTF-8',1)
        return True


    def StoreRawFile(self, clientid, filename, bzb64data, decompdata):
        if decompdata is True:
            decompr = bz2.BZ2Decompressor()
            data = decompr.decompress(base64.b64decode(bzb64data))
        else:
            data = base64.b64decode(bzb64data)

        # Make sure we have a directory to write files into
        self.__mkdatadir(self.dataroot + '/uploads/' + clientid)

        # Get a unique filename, as close as possible to the input filename
        fname = self.__getfilename('uploads/' + clientid, filename, not decompdata)

        # Save and return filename used server side
        f = open(fname, "w")
        f.write(data)
        f.close()
        return fname
