#!/usr/bin/env python

from multiprocessing import Process, Lock

import smtplib
import poplib
import imaplib
import os
import sys
import types
import threading
import subprocess
from ConfigParser import ConfigParser, NoOptionError
from email.parser import Parser
from datetime import datetime
from Users import Users
from FilterList import FilterList
from unbuffered import Unbuffered

def is_enabled(switch):
    return "no" != switch.lower()
#def

class msh:
    def __init__(self, config_path):
        if not os.path.exists(config_path):
            raise ValueError("Can't find config file \"" + config_path + "\"")
        #if

        sys.stdout = Unbuffered(sys.stdout)
        sys.stderr = Unbuffered(sys.stderr)

        self.__config = ConfigParser()
        self.__config.read(config_path)
        self.__active_mails_count = 0
        self.__send_lock = Lock()

        self.__users_db = Users(self.get_param_str('Main', 'ACCESS_FILE_PATH'))
        self.__whitelist = FilterList(self.get_param_str('Main', 'WHITELIST_SENDERS'))
        self.__blacklist = FilterList(self.get_param_str('Main', 'BLACKLIST_SENDERS'))
    #def


    def _send_response(self, email_from, msg):
        self.__send_lock.acquire()
        if not msg is None:
            print "[%s] Sending response to '%s'" % (datetime.today().strftime('%d/%m/%y %H:%M'), email_from)
            recipients = [email_from, self.get_param_str('Mail', 'SEND_COPY_TO')]
            message = "%s%s%s\n%s" % ('From: %s \n' % (self.get_param_str('Main', 'BOT_NAME')),
                                      'To: %s \n' % (email_from),
                                      'Subject: Report %s \n' % (datetime.today().strftime('%d/%m/%y %H:%M')),
                                       msg)

            if is_enabled(self.get_param_str("Mail", "USE_SSL")):
                session = smtplib.SMTP_SSL(self.get_param_str("Mail", "SMTP_SERVER"),
                                           self.get_param_int("Mail", "SMTP_SSL_PORT")))
            else:
                session = smtplib.SMTP(self.get_param_str("Mail", "SMTP_SERVER"),
                                       self.get_param_int("Mail", "SMTP_PORT"))
            #if
            if is_enabled(self.get_param_str("Debug", "NETWORK_COMM_LOGGING")):
                session.set_debuglevel(100)
            #if
            session.login(self.get_param_str("Mail", "EMAIL_USER"),
                          self.get_param_str("Mail", "EMAIL_PASS"))
            session.sendmail(self.get_param_str("Mail", "EMAIL_USER"),
                             recipients,
                             message)
            session.quit()
        #if
        self.__send_lock.release()
    #def

    def _check_pop(self):
        print "[%s] Going to get messages by POP" % (datetime.today().strftime('%d/%m/%y %H:%M'))
        if is_enabled(self.get_param_str("Mail", "USE_SSL")):
            session = poplib.POP3_SSL(self.get_param_str("Mail", "POP_SERVER"),
                                      self.get_param_int("Mail", "POP_SSL_PORT"))
        else:
            session = poplib.POP3(self.get_param_str("Mail", "POP_SERVER"),
                                  self.get_param_int("Mail", "POP_PORT"))
        #if
        if is_enabled(self.get_param_str("Debug", "NETWORK_COMM_LOGGING")):
            session.set_debuglevel(100)
        #if

        try:
            session.user(self.get_param_str("Mail", "EMAIL_USER"))
            session.pass_(self.get_param_str("Mail", "EMAIL_PASS"))
        except poplib.error_proto as e:
            sys.stderr.write("Got an error while conencting to POP server: '%s'\n"  % (e))
            return False
        #try

        numMessages = len(session.list()[1])
        for i in range(numMessages):
            m_parsed = Parser().parsestr("\n".join(session.top(i+1, 0)[1]))

            if self.get_param_str('Main', 'SUBJECT_CODE_PHRASE') == m_parsed['subject']:
                #Looks like valid cmd for bot, continue
                if self._process_msg("\n".join(session.retr(i+1)[1])):
                    session.dele(i+1)
                #if
            #if
        #for

        session.quit()
    #def

    def _check_imap(self):
        print "[%s] Going to get messages by IMAP" % (datetime.today().strftime('%d/%m/%y %H:%M'))
        if is_enabled(self.get_param_str("Mail", "USE_SSL")):
            session = imaplib.IMAP4_SSL(self.get_param_str("Mail", "IMAP_SERVER"),
                                        self.get_param_int("Mail", "IMAP_SSL_PORT"))
        else:
            session = imaplib.IMAP4(self.get_param_str("Mail", "IMAP_SERVER"),
                                    self.get_param_int("Mail", "IMAP_PORT"))
        #if
        if is_enabled(self.get_param_str("Debug", "NETWORK_COMM_LOGGING")):
            session.debug = 100
        #if

        try:
            session.login(self.get_param_str("Mail", "EMAIL_USER"),
                          self.get_param_str("Mail", "EMAIL_PASS"))
        except imaplib.IMAP4.error as e:
            sys.stderr.write("Got an error while connecting to IMAP server: '%s'\n" % (e))
            return False
        #try

        session.select(self.get_param_str('Mail', 'IMAP_MAILBOX_NAME'))
        typ, data = session.search(None,
                                   'SUBJECT', self.get_param_str("Main", "SUBJECT_CODE_PHRASE"))
        #                          'UNSEEN')
        if not data[0] is None:
            for num in data[0].split():
                typ, data = session.fetch(num, '(RFC822)')
                if self._process_msg(data[0][1]):
                   session.store(num, '+FLAGS', '\\Deleted')
        #          session.store(num, '+FLAGS', '\\Seen')
                #if
            #for
        #if
        session.expunge()
        session.close()
        session.logout()
    #def

    def _process_msg(self, raw_email):
        if not type(raw_email) is types.StringType:
            return True
        #if

        m_parsed = Parser().parsestr(raw_email)
        m_from = m_parsed['from']

        if self.__active_mails_count > self.get_param_int('Main', 'NUMBER_OF_PROCESSING_THREADS'):
            print "[%s] All processing threads are busy. Will try in next iteratio" % (datetime.today().strftime('%d/%m/%y %H:%M'))
            return False
        #if

        print "[%s] Processing message from user '%s'" % (datetime.today().strftime('%d/%m/%y %H:%M'), m_from)

        #check it in white/black lists
        if not self.__whitelist.has_elem(m_from, is_enabled(self.get_param_str('Main', 'USE_REGEXP_IN_FILTERING'))):
            print "Got command from unknown email (%s)" % (m_from)
            return True
        #if
        if self.__blacklist.has_elem(m_from, is_enabled(self.get_param_str('Main', 'USE_REGEXP_IN_FILTERING'))):
            print "Got command from blacklisted email (%s)" % (m_from)
            return True
        #if

        self.__active_mails_count += 1

        for m_body in self._get_payload_from_msg(m_parsed):
            if self._check_user(m_body[0]):
                for i in xrange(1, len(m_body)):
                    #self._thread_routine(ddm_from, m_body[i].strip())
                    Process(target=self._thread_routine, args=(m_from, m_body[i].strip())).start()
                #for
            else:
                print "Received an incorrect pair of user+password!"
            #if
        #for
        return True
    #def

    def _get_payload_from_msg(self, parsed_email):
        """
        Generator for extracting all message boundles from email
        """
        if parsed_email.is_multipart():
            for msg_from_multipart in parsed_email.get_payload():
                # proccesing recursively all multipart messages
                for sub_msg in self._get_payload_from_msg(msg_from_multipart):
                    yield sub_msg
                #for
            #for
        else:
            yield parsed_email.get_payload().split("\n")
        #if
    #def

    def _thread_routine(self, m_from, command):
        self._send_response(m_from, self._perform_user_cmd(command))

        self.__active_mails_count -= 1
    #def

    def _check_user(self, credentials_str):
        try:
            user, passwd  = credentials_str.strip().split(":")
            return self.__users_db.check(user, passwd)
        except ValueError:
            return False;
        #try
    #def

    def _perform_user_cmd(self, command):
        if 0 >= len(command):
            return None
        #if
        print "[%s] Going to process command '%s'" % (datetime.today().strftime('%d/%m/%y %H:%M'), command)
        get_rev = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        get_rev.wait()

        buff = "[%s] %s \r\n" % (datetime.today().strftime('%d/%m/%y %H:%M'), command)

        for str in get_rev.stdout.readlines():
            buff += str
        #for

        buff += "retcode = %d\r\n" % get_rev.returncode

        return buff
    #def

    def check_for_new_commands(self):
        print "[%s] Checking for new commands\n" % (datetime.today().strftime('%d/%m/%y %H:%M'))
        if is_enabled(self.get_param_str('Mail', 'USE_IMAP')):
            return self._check_imap()
        else:
            return self._check_pop()
        #if
    #def

    def add_new_user(self, user, passwd):
        return self.__users_db.add(user, passwd)
    #def

    def _get_param(self, sect, param):
        res = None
        try:
            res = self.__config.get(sect, param)
        except NoOptionError as e:
            sys.stderr.write("%s\n" % (str(e)))
        #try
        return res
    #def

    def get_param_int(self, sect, param):
        res = 0
        try:
            res = int(self._get_param(sect, param))
        except ValueError as e:
            sys.stderr.write("%s\n" % (str(e)))
        except TypeError as e:
            sys.stderr.write("%s\n" % (str(e)))
        #try
        return res
    #def

    def get_param_str(self, sect, param):
        return self._get_param(sect, param)
    #def
#class

