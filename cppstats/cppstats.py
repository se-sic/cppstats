#!/usr/bin/env python
# -*- coding: utf-8 -*-
# cppstats is a suite of analyses for measuring C preprocessor-based
# variability in software product lines.
# Copyright (C) 2014-2015 University of Passau, Germany
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#
# Contributors:
#     Claus Hunsen <hunsen@fim.uni-passau.de>
#     Andreas Ringlstetter <andreas.ringlstetter@gmail.com>


# #################################################
# imports from the std-library

import os
import sys
import shutil  # for copying files and folders
import errno  # for error/exception handling
import threading  # for parallelism
import subprocess  # for calling other commands
import re  # for regular expressions
from abc import ABCMeta, abstractmethod  # abstract classes
#import pynotify  # for system notifications
from argparse import ArgumentParser, RawTextHelpFormatter  # for parameters to this script
from collections import OrderedDict  # for ordered dictionaries
import tempfile # for temporary files

# #################################################
# imports from subfolders

# import different kinds of analyses
import cli, preparation, analysis


# #################################################
# version number

__version__ = "v0.9.3"

def version() :
    return "cppstats " + __version__


# #################################################
# collection of analyses

# add all kinds of analyses: (name -> (preparation, analysis))
__kinds = []
__kinds.append(('general', ('general', 'general')))
__kinds.append(('generalvalues', ('general', 'generalvalues')))
__kinds.append(('discipline', ('discipline', 'discipline')))
__kinds.append(('featurelocations', ('featurelocations', 'featurelocations')))
__kinds.append(('derivative', ('discipline', 'derivative')))
__kinds.append(('interaction', ('discipline', 'interaction')))


# exit, if there are no analysis threads available
if (len(__kinds) == 0) :
    print "ERROR: No analyses available! Revert your changes or call the maintainer."
    print "Exiting now..."
    sys.exit(1)

__kinds = OrderedDict(__kinds)


# #################################################
# main method


def applyFile(kind, infile, outfile, options):

    tmpfile = tempfile.mkstemp(suffix=".xml")[1] # temporary srcML file

    # preparation
    options.infile = infile
    options.outfile = tmpfile
    preparation.applyFile(kind, options.infile, options)

    # analysis
    options.infile = tmpfile
    options.outfile = outfile
    analysis.applyFile(kind, options.infile, options)

    # delete temp file
    os.remove(tmpfile)

def applyFolders(option_kind, inputlist, options):
    kind = __kinds.get(option_kind)
    preparationKind = kind[0]
    analysisKind = kind[1]

    preparation.applyFolders(preparationKind, inputlist, options)
    analysis.applyFolders(analysisKind, inputlist, options)

def applyFoldersAll(inputlist, options):
    for kind in __kinds.keys():
        applyFolders(kind, inputlist, options)


def main():
    # #################################################
    # options parsing

    options = cli.getOptions(__kinds, step = cli.steps.ALL)

    # #################################################
    # main

    if (options.inputfile):

        # split --file argument
        options.infile = os.path.normpath(os.path.abspath(options.inputfile[0])) # IN
        options.outfile = os.path.normpath(os.path.abspath(options.inputfile[1])) # OUT

        # check if inputfile exists
        if (not os.path.isfile(options.infile)):
            print "ERROR: input file '{}' cannot be found!".format(options.infile)
            sys.exit(1)

        applyFile(options.kind, options.infile, options.outfile, options)

    elif (options.inputlist):
        # handle --list argument
        options.inputlist = os.path.normpath(os.path.abspath(options.inputlist)) # LIST

        # check if list file exists
        if (not os.path.isfile(options.inputlist)):
            print "ERROR: input file '{}' cannot be found!".format(options.inputlist)
            sys.exit(1)

        if (options.allkinds):
            applyFoldersAll(options.inputlist, options)
        else:
            applyFolders(options.kind, options.inputlist, options)

    else:
        print "This should not happen! No input file or list of projects given!"
        sys.exit(1)

if __name__ == '__main__':
    main()
