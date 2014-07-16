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
from optparse import OptionParser, OptionGroup  # for parameters to this script
from collections import OrderedDict

# #################################################
# path adjustments, so that all imports can be done relative to these paths

__preparation_scripts_subfolder = "preparation"
__preparation_lib_subfolder = "lib"

sys.path.append(os.path.abspath(__preparation_lib_subfolder))  # lib subfolder
sys.path.append(os.path.abspath(__preparation_scripts_subfolder))  # preparation scripts

# #################################################
# imports from subfolders

# for rewriting of #ifdefs to "if defined(..)"
# for turning multiline macros to oneliners
# for deletion of include guards in H files
import rewriteIfdefs, rewriteMultilineMacros, deleteIncludeGuards

import cpplib.cpplib as cpplib


# #################################################
# global constants

__inputfile_default = "cppstats_input.txt"
_filepattern_c = ('.c', '.C')
_filepattern_h = ('.h', '.H')
_filepattern = _filepattern_c + _filepattern_h

# FIXME do preliminaries
# echo '### preliminaries ...'
#
# case `uname -s` in
# Linux|linux) s2sml=src2srcml.linux; sml2s=srcml2src.linux;;
# Darwin|darwin) s2sml=src2srcml.osx; sml2s=srcml2src.osx;;
# *) echo '### program src2srcml missing'
# echo '    see: http://www.sdml.info/projects/srcml/trunk/'
# exit 1;;
# esac
#
# which python > /dev/null
# if [ $? -ne 0 ]; then
# echo '### programm python missing!'
# 	echo '    see: http://www.python.org/'
# 	exit 1
# fi
#
# which astyle > /dev/null
# if [ $? -ne 0 ]; then
# 	echo '### programm astyle missing!'
# 	echo '    see: http://astyle.sourceforge.net/'
# 	exit 1
# fi
#
# which xsltproc > /dev/null
# if [ $? -ne 0 ]; then
# 	echo '### programm xsltproc missing!'
# 	echo '    see: http://www.xmlsoft.org/XSLT/xsltproc2.html'
# 	exit 1
# fi


# #################################################
# helper functions

def notify(message):
    pynotify.init("cppstats")
    notice = pynotify.Notification(message)
    notice.show()
    return


# function for ignore pattern
def filterForCFiles(dirpath, contents):
    mylist = [filename for filename in contents if
              not filename.endswith(_filepattern) and
              not os.path.isdir(os.path.join(dirpath, filename))
    ]
    return mylist


def getPreparationScript(filename):
    return os.path.join(__preparation_scripts_subfolder, filename)


def runBashCommand(command, shell=False, stdout=None):
    # split command if not a list/tuple is given already
    if type(command) is str:
        command = command.split()

    process = subprocess.Popen(command, shell=shell, stdout=stdout)
    output = process.communicate()[0]
    # TODO do something with the output


# TODO http://stackoverflow.com/questions/2369440/how-to-delete-all-blank-lines-in-the-file-with-the-help-of-python/2369538#2369538
def replaceMultiplePatterns(replacements, infile, outfile):
    with open(infile, "rb") as source:
        with open(outfile, "w") as target:
            data = source.read()
            for pattern, replacement in replacements.iteritems():
                data = re.sub(pattern, replacement, data, flags=re.MULTILINE)
            target.write(data)


def stripEmptyLinesFromFile(infile, outfile):
    with open(infile, "rb") as source:
        with open(outfile, "w") as target:
            for line in source:
                if line.strip():
                    target.write(line)


def silentlyRemoveFile(filename):
    try:
        os.remove(filename)
    except OSError as e:  # this would be "except OSError, e:" before Python 2.6
        if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
            raise  # re-raise exception if a different error occured


# #################################################
# abstract preparation thread

class AbstractPreparationThread(threading.Thread):
    '''This class prepares a single folder according to the given kind of preparation in an independent thread.'''
    __metaclass__ = ABCMeta
    sourcefolder = "source"

    def __init__(self, folder):
        threading.Thread.__init__(self)
        self.folder = folder
        self.folderBasename = os.path.basename(os.path.normpath(self.folder))
        self.source = os.path.join(folder, self.sourcefolder)

        # get full path of subfolder
        self.subfolder = os.path.join(self.folder, self.getSubfolder())


    def startup(self):
        # LOGGING
        notify("starting preparation: " + self.folderBasename)
        print "# prepare " + self.folderBasename

    def teardown(self):
        # LOGGING
        notify("finished preparation: " + self.folderBasename)

    def run(self):
        self.startup()

        # copy C and H files to self.subfolder
        self.copyToSubfolder()

        # for all files in the self.subfolder (only C and H files)
        for root, subFolders, files in os.walk(self.subfolder):
            for file in files:
                f = os.path.join(root, file)
                self.prepareFile(f)

        self.teardown()

    def copyToSubfolder(self):

        # TODO debug
        # echo '### preparing sources ...'
        # echo '### copying all-files to one folder ...'

        # delete folder if already existing
        if os.path.isdir(self.subfolder):
            shutil.rmtree(self.subfolder)

        # copy all C and H files recursively to the subfolder
        shutil.copytree(self.source, self.subfolder, ignore=filterForCFiles)

    @classmethod
    @abstractmethod
    def getName(cls):
        pass

    @abstractmethod
    def getSubfolder(self):
        pass

    @abstractmethod
    def prepareFile(self):
        pass

    # TODO refactor such that file has not be opened several times! (__currentfile)
    # TODO introduce counter for backup files for __currentfile
    def rewriteMultilineMacros(self, filename):

        tmp = filename + "tmp.txt"

        shutil.copyfile(filename, filename + ".bak01")  # backup file

        # turn multiline macros to oneliners
        shutil.move(filename, tmp)  # move for script
        rewriteMultilineMacros.translate(tmp, filename)  # call function

        os.remove(tmp)  # remove temp file

    def formatCode(self, filename):
        shutil.copyfile(filename, filename + ".bak02")  # backup file

        # call astyle to format file in Java-style
        runBashCommand("astyle --style=java " + filename)

        # try remove astyle backup file
        silentlyRemoveFile(filename + ".orig")

    def deleteComments(self, filename):

        tmp = filename + "tmp.xml"
        tmp_out = filename + "tmp_out.xml"

        shutil.copyfile(filename, filename + ".bak03")  # backup file

        # call src2srcml to transform code to xml
        # subprocess.call(["./src2srcml.linux", "--language=C", filename, "-o " + tmp])
        runBashCommand("./lib/srcml/src2srcml.linux --language=C " + filename + " -o " + tmp)

        # delete all comments in the xml and write to another file
        runBashCommand("xsltproc -o " + tmp_out + " " + getPreparationScript("deleteComments.xsl") + " " + tmp)

        # re-transform the xml to a normal source file
        # subprocess.call(["./srcml2src.linux", tmp_out, "-o " + filename])
        runBashCommand("./lib/srcml/srcml2src.linux " + tmp_out + " -o " + filename)

        # delete temp files
        os.remove(tmp)
        os.remove(tmp_out)

        # TODO implement getLib(path)
        # TODO support different systems than Linux!
        # Linux|linux) s2sml=src2srcml.linux; sml2s=srcml2src.linux;;
        # Darwin|darwin) s2sml=src2srcml.osx; sml2s=srcml2src.osx;;

    def deleteWhitespace(self, filename):
        """deletes leading, trailing and inter (# ... if) whitespaces,
        replaces multiple whitespace with a single space"""
        tmp = filename + "tmp.txt"

        shutil.copyfile(filename, filename + ".bak04")  # backup file

        # replace patterns with replacements
        replacements = {
            '^[ \t]+': '',  # leading whitespaces
            '[ \t]+$': '',  # trailing whitespaces
            '^#[ \t]+': '#',  # inter (# ... if) whitespaces
            '\t': ' ',  # tab to space
            '[ \t]{2,}': ' '  # multiple whitespace to one space

        }
        replaceMultiplePatterns(replacements, filename, tmp)

        # move temp file to output file
        shutil.move(tmp, filename)

    def rewriteIfdefsAndIfndefs(self, filename):
        tmp = filename + "tmp.txt"

        shutil.copyfile(filename, filename + ".bak06")  # backup file

        # rewrite #if(n)def ... to #if (!)defined(...)
        d = rewriteIfdefs.rewriteFile(filename, open(tmp, 'w'))

        # move temp file to output file
        shutil.move(tmp, filename)

    def removeIncludeGuards(self, filename):
        # include guards only exist in H files, otherwise return
        _, extension = os.path.splitext(filename)
        if (extension not in _filepattern_h):
            return

        tmp = filename + "tmp.txt"

        shutil.copyfile(filename, filename + ".bak07")  # backup file

        # delete include guards
        deleteIncludeGuards.apply(filename, open(tmp, 'w'))

        # move temp file to output file
        shutil.move(tmp, filename)

    def removeOtherPreprocessor(self, filename):
        tmp = filename + "tmp.txt"

        shutil.copyfile(filename, filename + ".bak08")  # backup file

        # delete other preprocessor statements than #ifdefs
        cpplib._filterAnnotatedIfdefs(filename, tmp)

        # move temp file to output file
        shutil.copyfile(tmp, filename)

    def deleteEmptyLines(self, filename):
        tmp = filename + "tmp.txt"

        shutil.copyfile(filename, filename + ".bak09")  # backup file

        # remove empty lines
        stripEmptyLinesFromFile(filename, tmp)

        # move temp file to output file
        shutil.move(tmp, filename)

    def transformFileToSrcml(self, filename):
        source = filename
        dest = filename + ".xml"

        # TODO other platforms for srcml transformations
        # FIXME encapsulate srcml calls in method!
        runBashCommand("./lib/srcml/src2srcml.linux --language=C " + source + " -o " + dest)
        # FIXME incorporate "|| rm ${f}.xml" from bash


# #################################################
# preparation-thread implementations

class GeneralPreparationThread(AbstractPreparationThread):
    @classmethod
    def getName(cls):
        return "general"

    def getSubfolder(self):
        return "_cppstats"

    def prepareFile(self, filename):
        # multiline macros
        self.rewriteMultilineMacros(filename)

        # delete comments
        self.deleteComments(filename)

        # delete leading, trailing and inter (# ... if) whitespaces
        self.deleteWhitespace(filename)

        # rewrite #if(n)def ... to #if (!)defined(...)
        self.rewriteIfdefsAndIfndefs(filename)

        # removes include guards from H files
        self.removeIncludeGuards(filename)

        # delete empty lines
        self.deleteEmptyLines(filename)

        # transform file to srcml
        self.transformFileToSrcml(filename)


class DisciplinePreparationThread(AbstractPreparationThread):
    @classmethod
    def getName(cls):
        return "discipline"

    def getSubfolder(self):
        return "_cppstats_discipline"

    def prepareFile(self, filename):
        # multiline macros
        self.rewriteMultilineMacros(filename)

        # delete comments
        self.deleteComments(filename)

        # delete leading, trailing and inter (# ... if) whitespaces
        self.deleteWhitespace(filename)

        # rewrite #if(n)def ... to #if (!)defined(...)
        self.rewriteIfdefsAndIfndefs(filename)

        # removes include guards from H files
        self.removeIncludeGuards(filename)

        # removes other preprocessor than #ifdefs
        self.removeOtherPreprocessor(filename)

        # delete empty lines
        self.deleteEmptyLines(filename)

        # transform file to srcml
        self.transformFileToSrcml(filename)


class FeatureLocationsPreparationThread(AbstractPreparationThread):
    @classmethod
    def getName(cls):
        return "featurelocations"

    def getSubfolder(self):
        return "_cppstats_featurelocations"

    def prepareFile(self, filename):
        # multiline macros
        self.rewriteMultilineMacros(filename)

        # delete leading, trailing and inter (# ... if) whitespaces
        self.deleteWhitespace(filename)

        # rewrite #if(n)def ... to #if (!)defined(...)
        self.rewriteIfdefsAndIfndefs(filename)

        # TODO is this necessary?
        # removes other preprocessor than #ifdefs
        self.removeOtherPreprocessor(filename)

        # transform file to srcml
        self.transformFileToSrcml(filename)


class PrettyPreparationThread(AbstractPreparationThread):
    @classmethod
    def getName(cls):
        return "pretty"

    def getSubfolder(self):
        return "_cppstats_pretty2"

    def prepareFile(self, filename):
        # multiline macros
        self.rewriteMultilineMacros(filename)

        # format the code
        self.formatCode(filename)

        # delete comments
        self.deleteComments(filename)

        # delete empty lines
        self.deleteEmptyLines(filename)


# #################################################
# collection of preparation threads

# add all subclass of AbstractPreparationThread as available preparation kinds
# FIXME check if there are subclasses available
__preparationkinds = []
for cls in AbstractPreparationThread.__subclasses__():
    entry = (cls.getName(), cls)
    __preparationkinds.append(entry)

__preparationkinds = OrderedDict(__preparationkinds)

# #################################################
# options parsing

# FIXME port to argparse, since optparse is deprecated since 2.7
# TODO synthesis of preparation and analysis! (rewording help!)
parser = OptionParser()
parser.add_option("--kind", type="choice", choices=__preparationkinds.keys(), dest="kind",
                  default=__preparationkinds.keys()[0], metavar="<K>",
                  help="the preparation to be performed (should correspond to the analysis to be performed) [default: %default]")
parser.add_option("--input", type="string", dest="inputfile", default=__inputfile_default, metavar="FILE",
                  help="a FILE that contains the list of input projects/folders [default: %default]")
parser.add_option("-a", "--all", action="store_true", dest="allkinds", default=False,
                  help="perform all available kinds of preparation [default: %default]")

group = OptionGroup(parser, "Possible Kinds of Preparation <K>", ", ".join(__preparationkinds.keys()))
parser.add_option_group(group)

(options, args) = parser.parse_args()


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
        thread = __preparationkinds[kind](folder)  # get proper preparation thread and call it
        threads.append(thread)
        thread.start()

    # join threads here
    for t in threads:
        t.join()


def applyAll(inputfile):
    for kind in __preparationkinds.keys():
        apply(kind, inputfile)


if __name__ == '__main__':

    if (options.allkinds):
        applyAll(options.inputfile)
    else:
        apply(options.kind, options.inputfile)
