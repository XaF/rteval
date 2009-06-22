import os
import sys
import signal
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from optparse import OptionParser

import xmlrpc_API1
from Logger import Logger

# Default values
PIDFILE="/var/run/rtevald.pid"
LISTEN="127.0.0.1"
PORT=65432

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/rteval/API1',)


class RTevald():
    def __init__(self, options, log):
        self.options = options
        self.log = log
        self.server = None

    def StartServer(self):
        # Create server
        self.server = SimpleXMLRPCServer((self.options.listen, self.options.port),
                                         requestHandler=RequestHandler)
        self.server.register_introspection_functions()

        # setup a class to handle requests
        self.server.register_instance(xmlrpc_API1.rteval_service(self.log))

        # Run the server's main loop
        self.log.Log("StartServer", "Listening on %s:%i" % (self.options.listen, self.options.port))
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.log.Log("StartServer", "Server caught SIGINT")
            pass
        finally:
            self.log.Log("StartServer", "Server stopped")



def daemonize(opts, logger):
    try:
        pid = os.fork()
    except OSError, e:
        raise Exception, "** ERROR: %d - %s" % (e.errno, e.strerror)

    if pid == 0: # Child
        signal.signal(signal.SIGHUP, signal.SIG_IGN) # Ignore SIGHUP

        try:
            pid2 = os.fork()
        except OSError, e:
            raise Exception, "** ERROR: %d - %s" % (e.errno, e.strerror)

        if pid2 == 0: # Child-child
            os.chdir("/tmp")  # Go to an available working dir
            os.umask(077)     # Make file created by child only readable by running user

            try:
                # Redirect stdin - do it before chroot, then we can access /dev/null
                devnull = open("/dev/null", "r")
                os.dup2(devnull.fileno(), sys.stdin.fileno())
            except Exception, e:
                logger.Log("daemonize", "** ERROR: %d - %s" % (e.errno, e.strerror))


            # Do chroot if requested
            if opts.chroot != None:
                os.chroot(opts.chroot)
                os.chdir("/")

            # Change UID/GID
            if opts.gid != None:
                os.setgid(opts.gid)
                os.setregid(opts.gid, opts.gid)

            if opts.uid != None:
                os.setuid(opts.uid)
                os.setreuid(opts.uid, opts.uid)

            # Redirect stdout and stderr to logger
            try:
                os.close(sys.stdout.fileno())
                os.close(sys.stderr.fileno())
                os.dup2(logger.LogFD(), sys.stdout.fileno())
                os.dup2(logger.LogFD(), sys.stderr.fileno())
            except Exception, e:
                logger.Log("daemonize", "** ERROR: %d - %s" % (e.errno, e.strerror))

            return 0
        else:
            logger.Log("daemonize", "rtevald pid %i" %pid2)
            # pid2 contains the child pid ... write this to the PID file
            pidfile = open(opts.pidfile, "w")
            pidfile.write("%i" % pid2)
            pidfile.close()
            os._exit(0) # Parent can now exit
    else:
        os._exit(0) # grand parent can also exit

    raise RuntimeError, "You shouldn't have arrived here ..."


pidfile = None
logger = None
rtevalserver = None

#
#  M A I N   F U N C T I O N
#

if __name__ == '__main__':
    parser = OptionParser(version="%prog v0.1")

    parser.add_option("-f", "--foreground", action="store_true", dest="foreground", default=False,
                      help="Do not run as a daemon")
    parser.add_option("-p", "--pid-file", action="store", dest="pidfile", default=PIDFILE,
                      help="Used when running as a daemon [default: %default]")
    parser.add_option("-u", "--uid", action="store", dest="uid", default=None, type="int",
                      help="Run process as UID [default: %default]")
    parser.add_option("-g", "--gid", action="store", dest="gid", default=None, type="int",
                      help="Run process as GID [default: %default]")
    parser.add_option("-C", "--chroot", action="store", dest="chroot", default=None,
                      help="Chroot the daemon")
    parser.add_option("-L", "--listen", action="store", dest="listen", default=LISTEN,
                      help="Which interface to listen to [default: %default]", metavar="IPADDR")
    parser.add_option("-P", "--port", action="store", type="int", dest="port", default=PORT,
                      help="Which port to listen to [default: %default]",  metavar="PORT")
    parser.add_option("-l", "--log", action="store", dest="logfile", default=None,
                      help="Where to log requests.", metavar="FILE")

    (options, args) = parser.parse_args()

    logger = Logger(options.logfile, "RTeval")
    pidfile = options.pidfile
    rtevalserver = RTevald(options, logger)

    if options.foreground == False:
        daemonize(options, logger)

    rtevalserver.StartServer()
