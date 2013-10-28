__author__ = 'jha5cn'

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings' # points to your settings.py file

from djftpd import create_django_ftpserver

## {{{ http://code.activestate.com/recipes/66012/ (r1)
def do_fork(method_to_deamonize):
    # do the UNIX double-fork magic, see Stevens' "Advanced
    # Programming in the UNIX Environment" for details (ISBN 0201563177)
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError, e:
        print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent, print eventual PID before
            print "Daemon PID %d" % pid
            sys.exit(0)
    except OSError, e:
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    # start the daemon main loop
    method_to_deamonize()
    ## end of http://code.activestate.com/recipes/66012/ }}}

def start_server():
    ftpd = create_django_ftpserver()
    ftpd.serve_forever()

do_fork(start_server)
