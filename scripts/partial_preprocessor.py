#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on Jun 30, 2010

@author: joliebig
'''
#FIXME move this script to another folder!
from lib.cpplib.cpplib import _filterAnnotatedIfdefs
from optparse import OptionParser
import sys

class PartialPreprocessor:
    def __init__(self):
        oparser = OptionParser()
        oparser.add_option('-i', '--inputfile', dest='ifile',
                help='input file (mandatory)')
        oparser.add_option('-o', '--outputfile', dest='ofile',
                help='output file (mandatory)')
        (self.opts, self.args) = oparser.parse_args()

        if not self.opts.ifile or not self.opts.ofile:
            oparser.print_help()
            sys.exit(-1)

        _filterAnnotatedIfdefs(self.opts.ifile, self.opts.ofile)


##################################################
if __name__ == '__main__':
    PartialPreprocessor()
