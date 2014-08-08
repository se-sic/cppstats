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
from argparse import ArgumentParser, RawTextHelpFormatter  # for parameters to this script
from collections import OrderedDict  # for ordered dictionaries

# #################################################
# path adjustments, so that all imports can be done relative to these paths

__analysis_lib_subfolder = "lib"
__analysis_scripts_subfolder = "analyses"

sys.path.append(os.path.abspath(__analysis_lib_subfolder))  # lib subfolder
sys.path.append(os.path.abspath(__analysis_scripts_subfolder))  # analysis scripts

# #################################################
# imports from subfolders

# different kinds of analyses are imported later within the corresponding classes
import cpplib.cpplib as cpplib


# #################################################
# global constants

__inputlist_default = "cppstats_input.txt"


# #################################################
# platform specific preliminaries

# cf. https://docs.python.org/2/library/sys.html#sys.platform
__platform = sys.platform.lower()

__iscygwin = False
if (__platform.startswith("cygwin")):
    __iscygwin = True
elif (__platform.startswith("darwin") or __platform.startswith("linux")):
    pass
else:
    print "Your system '" + __platform + "' is not supported right now."


# #################################################
# helper functions

def notify(message):
    if (__iscygwin):
        return

        # FIXME enable notifications again!
        # import pynotify  # for system notifications
        #
        # pynotify.init("cppstats")
        # notice = pynotify.Notification(message)
        # notice.show()


# #################################################
# abstract analysis thread

class AbstractAnalysisThread(object):
    '''This class analyzes a whole project according to the given kind of analysis in an independent thread.'''
    __metaclass__ = ABCMeta

    def __init__(self, options, inputfolder=None, inputfile=None):
        self.options = options
        self.notrunnable = False

        if (inputfolder):
            self.file = None
            self.folder = os.path.join(inputfolder, self.getPreparationFolder())
            self.project = os.path.basename(self.folder)

        elif (inputfile):
            self.file = inputfile
            self.outfile = self.options.outfile
            self.project = os.path.basename(self.file)

            # get full path of temp folder for
            import tempfile
            tmpfolder = tempfile.mkdtemp(suffix=self.getPreparationFolder())
            self.tmpfolder = tmpfolder
            self.folder = os.path.join(tmpfolder, self.getPreparationFolder())
            os.makedirs(self.folder)  # create the folder actually

            self.resultsfile = os.path.join(self.tmpfolder, self.getResultsFile())

        else:
            self.notrunnable = True


    def startup(self):
        # LOGGING
        notify("starting '" + self.getName() + "' preparations:\n " + self.project)
        print "# starting '" + self.getName() + "' preparations: " + self.project

    def teardown(self):
        # LOGGING
        notify("finished '" + self.getName() + "' preparations:\n " + self.project)
        print "# finished '" + self.getName() + "' preparations: " + self.project

    def run(self):

        if (self.notrunnable):
            print "ERROR: No single file or input list of projects given!"
            return

        self.startup()

        # copy srcml inputfile to tmp folder again and analyze project there!
        if (self.file):
            currentFile = os.path.join(self.folder, self.project)
            if (not currentFile.endswith(".xml")):
                currentFile += ".xml"
            shutil.copyfile(self.file, currentFile)

        # for all files in the self.folder (only C and H files)
        self.analyze(self.folder)

        # copy main results file from tmp folder to destination, if given
        if (self.file and self.resultsfile != self.outfile):
            shutil.copyfile(self.resultsfile, self.outfile)

        self.teardown()

    @classmethod
    @abstractmethod
    def getName(cls):
        pass

    @classmethod
    @abstractmethod
    def getPreparationFolder(self):
        pass

    @classmethod
    @abstractmethod
    def getResultsFile(self):
        pass

    @classmethod
    @abstractmethod
    def addCommandLineOptions(cls, optionParser):
        pass

    @abstractmethod
    def analyze(self):
        pass


# #################################################
# analysis-thread implementations

class GeneralAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "general"

    @classmethod
    def getPreparationFolder(self):
        return "_cppstats"

    @classmethod
    def getResultsFile(self):
        import general

        return general.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        import general

        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        general.addCommandLineOptions(group)

    def analyze(self, folder):
        import general

        general.apply(folder, self.options)


class DisciplineAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "discipline"

    @classmethod
    def getPreparationFolder(self):
        return "_cppstats_discipline"

    @classmethod
    def getResultsFile(self):
        import discipline

        return discipline.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        import discipline

        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        discipline.addCommandLineOptions(group)

    def analyze(self, folder):
        import discipline

        discipline.DisciplinedAnnotations(folder, self.options)


class FeatureLocationsAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "featurelocations"

    @classmethod
    def getPreparationFolder(self):
        return "_cppstats_featurelocations"

    @classmethod
    def getResultsFile(self):
        import featurelocations

        return featurelocations.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        import featurelocations

        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        featurelocations.addCommandLineOptions(group)

    def analyze(self, folder):
        import featurelocations

        featurelocations.apply(folder, self.options)


class DerivativeAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "derivative"

    @classmethod
    def getPreparationFolder(self):
        return "_cppstats_discipline"

    @classmethod
    def getResultsFile(self):
        import derivative

        return derivative.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        import derivative

        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        derivative.addCommandLineOptions(group)

    def analyze(self, folder):
        import derivative

        derivative.apply(folder)


class InteractionAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "interaction"

    @classmethod
    def getPreparationFolder(self):
        return "_cppstats_discipline"

    @classmethod
    def getResultsFile(self):
        import interaction

        return interaction.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        import interaction

        title = "Options for analyses '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        interaction.addCommandLineOptions(group)

    def analyze(self, folder):
        import interaction

        interaction.apply(folder, self.options)


# #################################################
# collection of analysis threads

# add all subclass of AbstractAnalysisThread as available analysis kinds
__analysiskinds = []
for cls in AbstractAnalysisThread.__subclasses__():
    entry = (cls.getName(), cls)
    __analysiskinds.append(entry)

# exit, if there are no analysis threads available
if (len(__analysiskinds) == 0):
    print "ERROR: No analysis tasks found! Revert your changes or call the maintainer."
    print "Exiting now..."
    sys.exit(1)

__analysiskinds = OrderedDict(__analysiskinds)


def getKinds():
    return __analysiskinds


# #################################################
# main method


def applyFile(kind, inputfile, options):
    kinds = getKinds()

    # get proper preparation thread and call it
    threadClass = kinds[kind]
    thread = threadClass(options, inputfile=inputfile)
    thread.run()


def getFoldersFromInputListFile(inputlist):
    ''' This method reads the given inputfile line-wise and returns the read lines without line breaks.'''

    file = open(inputlist, 'r')  # open input file
    folders = file.read().splitlines()  # read lines from file without line breaks
    file.close()  # close file

    folders = filter(lambda f: not f.startswith("#"), folders)  # remove commented lines
    folders = filter(os.path.isdir, folders)  # remove all non-directories
    folders = map(os.path.normpath, folders) # normalize paths for easier transformations

    return folders


def applyFolders(kind, inputlist, options):
    kinds = getKinds()

    # get the list of projects/folders to process
    folders = getFoldersFromInputListFile(inputlist)

    # for each folder:
    for folder in folders:
        # start preparations for this single folder

        # get proper preparation thread and call it
        threadClass = kinds[kind]
        thread = threadClass(options, inputfolder=folder)
        thread.run()


def applyFoldersAll(inputlist, options):
    kinds = getKinds()
    for kind in kinds.keys():
        applyFolders(kind, inputlist, options)


if __name__ == '__main__':
    kinds = getKinds()

    # #################################################
    # options parsing

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)

    # kinds
    kindgroup = parser.add_mutually_exclusive_group(required=False)
    kindgroup.add_argument("--kind", choices=kinds.keys(), dest="kind",
                           default=kinds.keys()[0], metavar="<K>",
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
                            help="a srcML file IN that is analyzed, the analysis results are written to OUT"
                                 "\n(--list is the default)")

    parser.add_argument_group("Possible Kinds of Analyses <K>".upper(), ", ".join(kinds.keys()))


    # add options for each analysis kind
    for cls in kinds.values():
        cls.addCommandLineOptions(parser)

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
        options.infile = os.path.normpath(os.path.abspath(options.inputfile[0]))  # IN
        options.outfile = os.path.normpath(os.path.abspath(options.inputfile[1]))  # OUT

        # check if inputfile exists
        if (not os.path.isfile(options.infile)):
            print "ERROR: input file '{}' cannot be found!".format(options.infile)
            sys.exit(1)

        applyFile(options.kind, options.infile, options)

    elif (options.inputlist):
        # handle --list argument
        options.inputlist = os.path.normpath(os.path.abspath(options.inputlist))  # LIST

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
