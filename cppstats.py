#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
import pynotify  # for system notifications
from argparse import ArgumentParser, RawTextHelpFormatter  # for parameters to this script
from collections import OrderedDict  # for ordered dictionaries
import tempfile # for temporary files

# #################################################
# path adjustments, so that all imports can be done relative to these paths

__cppstats_lib_subfolder = "lib"

sys.path.append(os.path.abspath(__cppstats_lib_subfolder))  # lib subfolder

# #################################################
# imports from subfolders

# import different kinds of analyses
import preparation, analysis

import cpplib.cpplib as cpplib


# #################################################
# global constants

__inputlist_default = "cppstats_input.txt"


# #################################################
# collection of analyses

# add all kinds of analyses: (name -> (preparation, analysis))
__kinds = []
__kinds.append(('general', ('general', 'general')))
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

def applyFolders(option_kind, inputlist, options):
    kind = __kinds.get(option_kind)
    preparationKind = kind[0]
    analysisKind = kind[1]

    preparation.applyFolders(preparationKind, inputlist, options)
    analysis.applyFolders(analysisKind, inputlist, options)

def applyFoldersAll(inputlist, options):
    for kind in __kinds.keys():
        applyFolders(kind, inputlist, options)


if __name__ == '__main__':

    # #################################################
    # options parsing

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)

    # kinds
    kindgroup = parser.add_mutually_exclusive_group(required=False)
    kindgroup.add_argument("--kind", choices=__kinds.keys(), dest="kind",
                           default=__kinds.keys()[0], metavar="<K>",
                           help="the preparation to be performed [default: %(default)s]")
    kindgroup.add_argument("-a", "--all", action="store_true", dest="allkinds", default=False,
                           help="perform all available kinds of preparation [default: %(default)s]")

    # input 1
    inputgroup = parser.add_mutually_exclusive_group(required=False)  # TODO check if True is possible some time...
    inputgroup.add_argument("--list", type=str, dest="inputlist", metavar="LIST",
                            nargs="?", default=__inputlist_default, const=__inputlist_default,
                            help="a file that contains the list of input projects/folders [default: %(default)s]")
    # input 2
    inputgroup.add_argument("--file", type=str, dest="inputfile", nargs=2, metavar=("IN", "OUT"),
                            help="a source file IN that is prepared and analyzed, the analysis results are written to OUT"
                                 "\n(--list is the default)")

    # no backup files
    parser.add_argument("--nobak", action="store_true", dest="nobak", default=False,
                        help="do not backup files during preparation [default: %(default)s]")

    parser.add_argument_group("Possible Kinds of Analyses <K>".upper(), ", ".join(__kinds.keys()))

    # add options for each analysis kind
    for kind in __kinds.values():
        analysisPart = kind[1]
        analysisThread = analysis.getKinds().get(analysisPart)
        analysisThread.addCommandLineOptions(parser)

    # parse options
    options = parser.parse_args()

    # constraints
    if (options.allkinds == True and options.inputfile):
        print "Using all kinds of preparation for a single input and output file is weird!"
        sys.exit(1)

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
