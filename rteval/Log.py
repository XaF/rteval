#
#   Copyright 2012 - 2013   David Sommerseth <davids@redhat.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#   For the avoidance of doubt the "preferred form" of this code is one which
#   is in an open unpatent encumbered format. Where cryptographic key signing
#   forms part of the process of creating an executable the information
#   including keys needed to generate an equivalently functional executable
#   are deemed to be part of the source code.
#

import sys

class Log(object):
    NONE   = 0
    ALWAYS = 0
    INFO   = 1<<0
    WARN   = 1<<1
    ERR    = 1<<2
    DEBUG  = 1<<3


    def __init__(self, logfile=None):
        if logfile is not None:
            self.__logfile = open(logfile, "w")
        else:
            self.__logfile = sys.stdout
        self.__logverb = self.INFO


    def __logtype_str(self, ltype):
        if ltype == self.ALWAYS:
            return ""
        if ltype == self.INFO:
            return "[INFO] "
        elif ltype == self.WARN:
            return "[WARNING] "
        elif ltype == self.ERR:
            return "[ERROR] "
        elif ltype == self.DEBUG:
            return "[DEBUG] "


    def SetLogVerbosity(self, logverb):
        self.__logverb = logverb


    def log(self, logtype, msg):
        if (logtype & self.__logverb) or logtype == self.ALWAYS:
            self.__logfile.write("%s%s\n" %
                                 (self.__logtype_str(logtype),
                                  msg)
                                 )



def unit_test(rootdir):
    from itertools import takewhile, count

    logtypes = (Log.ALWAYS, Log.INFO, Log.WARN, Log.ERR, Log.DEBUG)
    logtypes_s = ("ALWAYS", "INFO", "WARN", "ERR", "DEBUG")

    def test_log(l, msg):
        for lt in logtypes:
            l.log(lt, msg)

    def run_log_test(l):
        for lt in range(min(logtypes), max(logtypes)*2):
            test = ", ".join([logtypes_s[logtypes.index(i)] for i in [p for p in takewhile(lambda x: x <= lt, (2**i for i in count())) if p & lt]])
            print "Testing verbosity flags set to: (%i) %s" % (lt, test)
            msg = "Log entry when verbosity is set to %i [%s]" % (lt, test)
            l.SetLogVerbosity(lt)
            test_log(l, msg)
            print "-"*20

    try:
        print "** Testing stdout"
        l = Log()
        run_log_test(l)

        print "** Testing file logging - using test.log"
        l = Log("test.log")
        run_log_test(l)

        return 0
    except Exception, e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        print "** EXCEPTION %s", str(e)
        return 1



if __name__ == '__main__':
    unit_test(None)

