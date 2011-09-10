#!/usr/bin/env python

import os
import csv
from hashlib import md5

class Users:
    def __init__(self, users_db_path):
        if users_db_path is None:
            raise ValueError("Passed null as users_db")
        #if

        self.__users = {}
        self.__users_db_path = users_db_path
        if os.path.exists(self.__users_db_path):
            self._load_db()
        else:
            print "Database is't exists '%s'" % (users_db_path)
        #if
    #def

    def _load_db(self):
        f = open(self.__users_db_path, 'rb')
        c_reader = csv.reader(f, delimiter=',')
        for line in c_reader:
            if not self.__users.has_key(line[0]):
                self.__users[line[0]] = line[1]
            #if
        #for
        f.close()
    #def

    def check(self, user, passwd):
        return self.__users.has_key(user) and self.__users[user] == md5(passwd).hexdigest()
    #def

    def add(self, user, passwd):
        if not self.__users.has_key(user):
            self.__users[user] = md5(passwd).hexdigest()
            f = open(self.__users_db_path, 'wb')
            for key in self.__users.keys():
                f.write("%s,%s\n" % (key, self.__users[key]))
            #for
            f.close()
        #if
    #def
#class

