#!/usr/bin/env python

class Unbuffered:
    """
    Class for wrapping any stram and doung flush after every write.
    Helpful for logging in file
    """
    def __init__(self, stream):
         self.stream = stream
    #def

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    #def

    def __getattr__(self, attr):
        return getattr(self.stream, attr)
    #def

#class
