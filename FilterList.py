#!/usr/bin/env python

import re
import types

class FilterList:
    def __init__(self, str_list):
        if not str_list is None and type(str_list) is types.StringType:
            try:
                self.__list = str_list.lower().split(",")
            except ValueError:
                pass
            #try
        #if
    #def

    def has_elem(self, email, use_regexp):
        if type(use_regexp) is types.BooleanType and use_regexp:
            return self.has_elem_regexp(email.lower())
        else:
            return self.has_elem_simple(email.lower())
        #if
    #def

    def has_elem_simple(self, email):
        """
        Simple search function, checks for exact matching
        """
        try:
            self.__list.index(email)
            return True
        except ValueError:
            return False
        #try
    #def

    def has_elem_regexp(self, email):
        """
        More clever function, interpret current list as regexps.
        """
        for pattern in self.__list:
            if re.findall(pattern.replace('*','\S+'), email, re.I):
                # match!
                return True
            #if
        #for
        return False
    #def
#class

