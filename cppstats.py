#!/usr/bin/python
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

__inputfile_default = "cppstats_input.txt"


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
# options parsing

parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
parser.add_argument("--kind", choices=__kinds.keys(), dest="kind",
                  default=__kinds.keys()[0], metavar="<K>",
                  help="the analysis to be performed (including preparation) [default: %(default)s]")
parser.add_argument("--input", type=str, dest="inputfile", default=__inputfile_default, metavar="FILE",
                  help="a FILE that contains the list of input projects/folders \n[default: %(default)s]")
parser.add_argument("--all", action="store_true", dest="allkinds", default=False,
                  help="perform all available kinds of analysis \n(overrides the --kind parameter) [default: %(default)s]")
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


# #################################################
# main method


def apply(preparationKind, analysisKind, inputfile, options):

    preparation.apply(preparationKind, inputfile, options)
    analysis.apply(analysisKind, inputfile, options)


def applyAll(inputfile):
    for kind in __analysiskinds.keys():
        apply(kind, inputfile)


if __name__ == '__main__':

    kind = __kinds.get(options.kind)
    preparationKind = kind[0]
    analysisKind = kind[1]

    apply(preparationKind, analysisKind, options.inputfile, options)
