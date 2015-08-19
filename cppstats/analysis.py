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
from argparse import ArgumentParser, RawTextHelpFormatter  # for parameters to this script
from collections import OrderedDict  # for ordered dictionaries

# #################################################
# imports from subfolders

import cppstats, cli

# import different kinds of analyses
from analyses import general, generalvalues, discipline, featurelocations, derivative, interaction


# #################################################
# global constants



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
        notify("starting '" + self.getName() + "' analysis:\n " + self.project)
        print "# starting '" + self.getName() + "' analysis: " + self.project

    def teardown(self):

        # delete temp folder for file-based preparation
        if (self.file):
            shutil.rmtree(self.tmpfolder)

        # LOGGING
        notify("finished '" + self.getName() + "' analysis:\n " + self.project)
        print "# finished '" + self.getName() + "' analysis: " + self.project

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
        return general.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        general.addCommandLineOptions(group)

    def analyze(self, folder):
        general.apply(folder, self.options)


class GeneralValuesAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "generalvalues"

    @classmethod
    def getPreparationFolder(self):
        return "_cppstats"

    @classmethod
    def getResultsFile(self):
        return generalvalues.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        generalvalues.addCommandLineOptions(group)

    def analyze(self, folder):
        generalvalues.apply(folder, self.options)


class DisciplineAnalysisThread(AbstractAnalysisThread):
    @classmethod
    def getName(cls):
        return "discipline"

    @classmethod
    def getPreparationFolder(self):
        return "_cppstats_discipline"

    @classmethod
    def getResultsFile(self):
        return discipline.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        discipline.addCommandLineOptions(group)

    def analyze(self, folder):
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
        return featurelocations.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        featurelocations.addCommandLineOptions(group)

    def analyze(self, folder):
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
        return derivative.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        title = "Options for analysis '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        derivative.addCommandLineOptions(group)

    def analyze(self, folder):
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
        return interaction.getResultsFile()

    @classmethod
    def addCommandLineOptions(cls, optionParser):
        title = "Options for analyses '" + cls.getName() + "'"
        group = optionParser.add_argument_group(title.upper())
        interaction.addCommandLineOptions(group)

    def analyze(self, folder):
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

    #TODO log removed folders

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


def main():
    kinds = getKinds()

    # #################################################
    # options parsing

    options = cli.getOptions(kinds, step=cli.steps.ANALYSIS)

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

if __name__ == '__main__':
    main()
