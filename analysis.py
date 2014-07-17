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

__preparation_scripts_subfolder = "analysis"
__preparation_lib_subfolder = "lib"

sys.path.append(os.path.abspath(__preparation_lib_subfolder))  # lib subfolder
sys.path.append(os.path.abspath(__preparation_scripts_subfolder))  # preparation scripts

# #################################################
# imports from subfolders

# FIXME what to import?
# import different kinds of analyses
# import general  #, discipline, featurelocations, interaction, derivative

import cpplib.cpplib as cpplib


# #################################################
# global constants

__inputfile_default = "cppstats_input.txt"


# #################################################
# helper functions

def notify(message):
    pynotify.init("cppstats")
    notice = pynotify.Notification(message)
    notice.show()
    return


# #################################################
# abstract preparation thread

class AbstractAnalysisThread(threading.Thread):
    '''This class analyzes a whole project according to the given kind of analysis in an independent thread.'''
    __metaclass__ = ABCMeta

    def __init__(self, folder):
        threading.Thread.__init__(self)
        self.folder = folder
        self.folderBasename = os.path.basename(os.path.normpath(self.folder))

        # get full path of subfolder
        self.subfolder = os.path.join(self.folder, self.getPreparationFolder())


    def startup(self):
        # LOGGING
        notify("starting analysis: " + self.folderBasename)
        print "# prepare " + self.folderBasename

    def teardown(self):
        # LOGGING
        notify("finished analysis: " + self.folderBasename)

    def run(self):
        self.startup()

        # for all files in the self.subfolder (only C and H files)
        folder = os.path.join(self.folder, self.getPreparationFolder())
        self.analyze(folder)

        self.teardown()

    @classmethod
    @abstractmethod
    def getName(cls):
        pass

    @abstractmethod
    def getPreparationFolder(self):
        pass

    @abstractmethod
    def analyze(self):
        pass

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        pass


# #################################################
# preparation-thread implementations

class GeneralAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "general"

    def getPreparationFolder(self):
        return "_cppstats"

    def analyze(self, folder):
        import general
        general.apply(folder, options)

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        import general
        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        general.addCommandLineOptions(group)


class DisciplineAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "discipline"

    def getPreparationFolder(self):
        return "_cppstats_discipline"

    def analyze(self, folder):
        import discipline
        discipline.DisciplinedAnnotations(folder, options)

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        import discipline
        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        discipline.addCommandLineOptions(group)


class FeatureLocationsAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "featurelocations"

    def getPreparationFolder(self):
        return "_cppstats_featurelocations"

    def analyze(self, folder):
        import featurelocations
        featurelocations.apply(folder)

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        import featurelocations
        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        featurelocations.addCommandLineOptions(group)


class DerivativeAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "derivative"

    def getPreparationFolder(self):
        return "_cppstats_discipline"

    def analyze(self, folder):
        import derivative
        derivative.apply(folder)

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        import derivative
        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        derivative.addCommandLineOptions(group)


class InteractionAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "interaction"

    def getPreparationFolder(self):
        return "_cppstats_discipline"

    def analyze(self, folder):
        import interaction
        interaction.apply(folder)

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        import interaction
        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        interaction.addCommandLineOptions(group)


# #################################################
# collection of preparation threads

# add all subclass of AbstractPreparationThread as available preparation kinds
__analysiskinds = []
for cls in AbstractAnalysisThread.__subclasses__():
    entry = (cls.getName(), cls)
    __analysiskinds.append(entry)

# exit, if there are no analysis threads available
if (len(__analysiskinds) == 0) :
    print "ERROR: No analysis tasks found! Revert your changes or call the maintainer."
    print "Exiting now..."
    sys.exit(1)

__analysiskinds = OrderedDict(__analysiskinds)


# #################################################
# options parsing

# TODO synthesis of preparation and analysis! (rewording help!)
parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
parser.add_argument("--kind", choices=__analysiskinds.keys(), dest="kind",
                  default=__analysiskinds.keys()[0], metavar="<K>",
                  help="the analysis to be performed [default: %(default)s]")
parser.add_argument("--input", type=str, dest="inputfile", default=__inputfile_default, metavar="FILE",
                  help="a FILE that contains the list of input projects/folders \n[default: %(default)s]")
parser.add_argument("--all", action="store_true", dest="allkinds", default=False,
                  help="perform all available kinds of analysis \n(overrides the --kind parameter) [default: %(default)s]")

parser.add_argument_group("Possible Kinds of Analyses <K>".upper(), ", ".join(__analysiskinds.keys()))


# add options for each analysis kind
for cls in __analysiskinds.values():
    cls.addCommandLineOptions(parser)

# parse options
options = parser.parse_args()


# #################################################
# main method

def getFoldersFromInputFile(inputfile):
    ''' This method reads the given inputfile line-wise and returns the read lines without line breaks.'''

    file = open(inputfile, 'r')  # open input file
    folders = file.read().splitlines()  # read lines from file without line breaks
    file.close()  # close file

    return folders


def apply(kind, inputfile):
    threads = []  # list of independent threads performing preparation steps

    # get the list of projects/folders to process
    folders = getFoldersFromInputFile(inputfile)

    # for each folder:
    for folder in folders:
        # start preparation for this single folder

        # print __preparationkinds[kind].__name__
        thread = __analysiskinds[kind](folder)  # get proper preparation thread and call it
        threads.append(thread)
        thread.start()

    # join threads here
    for t in threads:
        t.join()


def applyAll(inputfile):
    for kind in __analysiskinds.keys():
        apply(kind, inputfile)


if __name__ == '__main__':

    if (options.allkinds):
        applyAll(options.inputfile)
    else:
        apply(options.kind, options.inputfile)
