#!/usr/bin/env python

import os, sys, time, getpass
from daemon import Daemon
from msh import msh

class mshDaemon(Daemon):
    """
    MailShell Daemon
    """
    def adduser(self):
        """
        Simple prompt to add new users
        """
        m = msh(os.path.join(sys.path[0], 'config.cfg'))

        username = raw_input('Enter user name: ')
        pw1 = getpass.getpass()
        pw2 = getpass.getpass("Confirm password: ")

        if pw1 == pw2:
            m.add_new_user(username, pw1)
            print 'User was succesfully added.'
        else:
            print 'Error: you provided different passwords'
    #def

    def singlerun(self):
        m = msh(os.path.join(sys.path[0], 'config.cfg'))
        m.check_for_new_commands()
    #def

    def run(self):
        """
        The main routine
        """
        m = msh(os.path.join(sys.path[0], 'config.cfg'))
        while True:
            m.check_for_new_commands()
            time.sleep(m.get_param_int('Main', 'INTERVAL_TO_CHECK_IN_SEC'))
        #while
    #def
#class

def usage():
    print "usage: %s start|stop|restart|adduser|singlerun" % sys.argv[0]
    sys.exit(2)
#def

if __name__ == "__main__":
    daemon = mshDaemon('/tmp/msh_daemon.pid',
                        stdout=os.path.join(sys.path[0], 'run_log'),
                        stderr=os.path.join(sys.path[0], 'error_log'))

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'adduser' == sys.argv[1]:
            daemon.adduser()
        elif 'singlerun' == sys.argv[1]:
            daemon.singlerun()
        else:
            print "Unknown command"
            usage()
        #if
        sys.exit(0)
    else:
        usage()
    #if
#main

