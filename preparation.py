#!/usr/bin/python
# -*- coding: utf-8 -*-

# #################################################
# imports from the std-library

import os, sys, platform
import shutil  # for copying files and folders
import errno  # for error/exception handling
import threading  # for parallelism
import subprocess  # for calling other commands
import re  # for regular expressions
from abc import ABCMeta, abstractmethod  # abstract classes
from argparse import ArgumentParser, RawTextHelpFormatter  # for parameters to this script
from collections import OrderedDict

# #################################################
# path adjustments

__preparation_scripts_subfolder = "preparations"
__preparation_lib_subfolder = "lib"
__preparation_lib_srcml_subfolder = "srcml"

sys.path.append(os.path.abspath(__preparation_lib_subfolder))  # lib subfolder
sys.path.append(os.path.abspath(__preparation_scripts_subfolder))  # preparation scripts


def getPreparationScript(filename):
    return os.path.join(__preparation_scripts_subfolder, filename)


def getLib(path):
    return os.path.abspath(os.path.join(__preparation_lib_subfolder, path))


# #################################################
# platform specific preliminaries

# cf. https://docs.python.org/2/library/sys.html#sys.platform
__platform = sys.platform.lower()

__iscygwin = False
if (__platform.startswith("linux")):
    __s2sml_executable = "src2srcml.linux"
    __sml2s_executable = "srcml2src.linux"
elif (__platform.startswith("darwin")):
    __s2sml_executable = "src2srcml.osx"
    __sml2s_executable = "srcml2src.osx"
elif (__platform.startswith("cygwin")) :
    __s2sml_executable = "win/src2srcml.exe"
    __sml2s_executable = "win/srcml2src.exe"
    __iscygwin = True
else:
    print "Your system '" + __platform + "' is not supported by SrcML right now."

_s2sml = getLib(os.path.join(__preparation_lib_srcml_subfolder, __s2sml_executable))
_sml2s = getLib(os.path.join(__preparation_lib_srcml_subfolder, __sml2s_executable))


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
# echo '    see: http://www.python.org/'
# exit 1
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
    if (__iscygwin):
        return

    import pynotify  # for system notifications

    pynotify.init("cppstats")
    notice = pynotify.Notification(message)
    notice.show()


# function for ignore pattern
def filterForFiles(dirpath, contents, pattern=_filepattern):
    mylist = [filename for filename in contents if
              not filename.endswith(pattern) and
              not os.path.isdir(os.path.join(dirpath, filename))
    ]
    return mylist


def runBashCommand(command, shell=False, stdout=None):
    # split command if not a list/tuple is given already
    if type(command) is str:
        command = command.split()

    process = subprocess.Popen(command, shell=shell, stdout=stdout)
    out, err = process.communicate() # TODO do something with the output
    process.wait()


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


def getCygwinPath(filename):
    return subprocess.check_output(['cygpath', '-m', filename]).strip()

def src2srcml(src, srcml):
    global _s2sml

    if (__iscygwin):
        src = getCygwinPath(src)
        #srcml = getCygwinPath(srcml)
        _s2sml = getCygwinPath(_s2sml)

    runBashCommand(_s2sml + " --language=C " + src, stdout = open(srcml, 'w+'))# + " -o " + srcml)
    # FIXME incorporate "|| rm ${f}.xml" from bash


def srcml2src(srcml, src):

    if (__iscygwin) :
        global _sml2s
        src = getCygwinPath(src)
        srcml = getCygwinPath(srcml)
        _sml2s = getCygwinPath(_sml2s)

    runBashCommand(_sml2s + " " + srcml, stdout = open(src, 'w+'))# + " -o " + src)


# #################################################
# abstract preparation thread

class AbstractPreparationThread(threading.Thread):
    '''This class prepares a single folder according to the given kind of preparations in an independent thread.'''
    __metaclass__ = ABCMeta
    sourcefolder = "source"

    def __init__(self, folder, options):
        threading.Thread.__init__(self)
        self.folder = folder
        self.options = options

        self.folderBasename = os.path.basename(os.path.normpath(self.folder))
        self.source = os.path.join(folder, self.sourcefolder)

        # get full path of subfolder
        self.subfolder = os.path.join(self.folder, self.getSubfolder())


    def startup(self):
        # LOGGING
        notify("starting '" + self.getName() + "' preparations:\n " + self.folderBasename)
        print "# starting '" + self.getName() + "' preparations: " + self.folderBasename

    def teardown(self):
        # LOGGING
        notify("finished '" + self.getName() + "' preparations:\n " + self.folderBasename)
        print "# finished '" + self.getName() + "' preparations: " + self.folderBasename

    def run(self):
        self.startup()

        # copy C and H files to self.subfolder
        self.copyToSubfolder()

        # for all files in the self.subfolder (only C and H files)
        for root, subFolders, files in os.walk(self.subfolder):
            for file in files:
                f = os.path.join(root, file)
                self.backupCounter = 0
                self.currentFile = f
                self.prepareFile()

        self.teardown()

    def copyToSubfolder(self):

        # TODO debug
        # echo '### preparing sources ...'
        # echo '### copying all-files to one folder ...'

        # delete folder if already existing
        if os.path.isdir(self.subfolder):
            shutil.rmtree(self.subfolder)

        # copy all C and H files recursively to the subfolder
        shutil.copytree(self.source, self.subfolder, ignore=filterForFiles)

    def backupCurrentFile(self):
        '''# backup file'''
        # TODO check if nobak exists first!
        if (not self.options.nobak):
            bak = self.currentFile + ".bak" + str(self.backupCounter)
            shutil.copyfile(self.currentFile, bak)
            self.backupCounter += 1

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
    def rewriteMultilineMacros(self):
        tmp = self.currentFile + "tmp.txt"

        self.backupCurrentFile()  # backup file

        # turn multiline macros to oneliners
        shutil.move(self.currentFile, tmp)  # move for script
        rewriteMultilineMacros.translate(tmp, self.currentFile)  # call function

        os.remove(tmp)  # remove temp file

    def formatCode(self):
        self.backupCurrentFile()  # backup file

        # call astyle to format file in Java-style
        runBashCommand("astyle --style=java " + self.currentFile)

        # try remove astyle backup file
        silentlyRemoveFile(self.currentFile + ".orig")

    def deleteComments(self):
        tmp = self.currentFile + "tmp.xml"
        tmp_out = self.currentFile + "tmp_out.xml"

        self.backupCurrentFile()  # backup file

        # call src2srcml to transform code to xml
        src2srcml(self.currentFile, tmp)

        # delete all comments in the xml and write to another file
        runBashCommand("xsltproc -o " + tmp_out + " " + getPreparationScript("deleteComments.xsl") + " " + tmp)

        # re-transform the xml to a normal source file
        srcml2src(tmp_out, self.currentFile)

        # delete temp files
        os.remove(tmp)
        os.remove(tmp_out)

    def deleteWhitespace(self):
        """deletes leading, trailing and inter (# ... if) whitespaces,
        replaces multiple whitespace with a single space"""
        tmp = self.currentFile + "tmp.txt"

        self.backupCurrentFile()  # backup file

        # replace patterns with replacements
        replacements = {
            '^[ \t]+': '',  # leading whitespaces
            '[ \t]+$': '',  # trailing whitespaces
            '^#[ \t]+': '#',  # inter (# ... if) whitespaces
            '\t': ' ',  # tab to space
            '[ \t]{2,}': ' '  # multiple whitespace to one space

        }
        replaceMultiplePatterns(replacements, self.currentFile, tmp)

        # move temp file to output file
        shutil.move(tmp, self.currentFile)

    def rewriteIfdefsAndIfndefs(self):
        tmp = self.currentFile + "tmp.txt"

        self.backupCurrentFile()  # backup file

        # rewrite #if(n)def ... to #if (!)defined(...)
        d = rewriteIfdefs.rewriteFile(self.currentFile, open(tmp, 'w'))

        # move temp file to output file
        shutil.move(tmp, self.currentFile)

    def removeIncludeGuards(self):
        # include guards only exist in H files, otherwise return
        _, extension = os.path.splitext(self.currentFile)
        if (extension not in _filepattern_h):
            return

        tmp = self.currentFile + "tmp.txt"

        self.backupCurrentFile()  # backup file

        # delete include guards
        deleteIncludeGuards.apply(self.currentFile, open(tmp, 'w'))

        # move temp file to output file
        shutil.move(tmp, self.currentFile)

    def removeOtherPreprocessor(self):
        tmp = self.currentFile + "tmp.txt"

        self.backupCurrentFile()  # backup file

        # delete other preprocessor statements than #ifdefs
        cpplib._filterAnnotatedIfdefs(self.currentFile, tmp)

        # move temp file to output file
        shutil.copyfile(tmp, self.currentFile)

    def deleteEmptyLines(self):
        tmp = self.currentFile + "tmp.txt"

        self.backupCurrentFile()  # backup file

        # remove empty lines
        stripEmptyLinesFromFile(self.currentFile, tmp)

        # move temp file to output file
        shutil.move(tmp, self.currentFile)

    def transformFileToSrcml(self):
        source = self.currentFile
        dest = self.currentFile + ".xml"

        # transform to srcml
        src2srcml(source, dest)


# #################################################
# preparation-thread implementations

class GeneralPreparationThread(AbstractPreparationThread):
    @classmethod
    def getName(cls):
        return "general"

    def getSubfolder(self):
        return "_cppstats"

    def prepareFile(self):
        # multiline macros
        self.rewriteMultilineMacros()

        # delete comments
        self.deleteComments()

        # delete leading, trailing and inter (# ... if) whitespaces
        self.deleteWhitespace()

        # rewrite #if(n)def ... to #if (!)defined(...)
        self.rewriteIfdefsAndIfndefs()

        # removes include guards from H files
        self.removeIncludeGuards()

        # delete empty lines
        self.deleteEmptyLines()

        # transform file to srcml
        self.transformFileToSrcml()


class DisciplinePreparationThread(AbstractPreparationThread):
    @classmethod
    def getName(cls):
        return "discipline"

    def getSubfolder(self):
        return "_cppstats_discipline"

    def prepareFile(self):
        # multiline macros
        self.rewriteMultilineMacros()

        # delete comments
        self.deleteComments()

        # delete leading, trailing and inter (# ... if) whitespaces
        self.deleteWhitespace()

        # rewrite #if(n)def ... to #if (!)defined(...)
        self.rewriteIfdefsAndIfndefs()

        # removes include guards from H files
        self.removeIncludeGuards()

        # removes other preprocessor than #ifdefs
        self.removeOtherPreprocessor()

        # delete empty lines
        self.deleteEmptyLines()

        # transform file to srcml
        self.transformFileToSrcml()


class FeatureLocationsPreparationThread(AbstractPreparationThread):
    @classmethod
    def getName(cls):
        return "featurelocations"

    def getSubfolder(self):
        return "_cppstats_featurelocations"

    def prepareFile(self):
        # multiline macros
        self.rewriteMultilineMacros()

        # delete leading, trailing and inter (# ... if) whitespaces
        self.deleteWhitespace()

        # rewrite #if(n)def ... to #if (!)defined(...)
        self.rewriteIfdefsAndIfndefs()

        # transform file to srcml
        self.transformFileToSrcml()


class PrettyPreparationThread(AbstractPreparationThread):
    @classmethod
    def getName(cls):
        return "pretty"

    def getSubfolder(self):
        return "_cppstats_pretty"

    def prepareFile(self):
        # multiline macros
        self.rewriteMultilineMacros()

        # format the code
        self.formatCode()

        # delete comments
        self.deleteComments()

        # delete empty lines
        self.deleteEmptyLines()


# #################################################
# collection of preparation threads

# add all subclass of AbstractPreparationThread as available preparation kinds
__preparationkinds = []
for cls in AbstractPreparationThread.__subclasses__():
    entry = (cls.getName(), cls)
    __preparationkinds.append(entry)

# exit, if there are no preparation threads available
if (len(__preparationkinds) == 0):
    print "ERROR: No preparation tasks found! Revert your changes or call the maintainer."
    print "Exiting now..."
    sys.exit(1)
__preparationkinds = OrderedDict(__preparationkinds)

def getKinds():
    return __preparationkinds


# #################################################
# main method

def getFoldersFromInputFile(inputfile):
    ''' This method reads the given inputfile line-wise and returns the read lines without line breaks.'''

    file = open(inputfile, 'r')  # open input file
    folders = file.read().splitlines()  # read lines from file without line breaks
    file.close()  # close file

    return folders


def apply(kind, inputfile, options):
    kinds = getKinds()
    threads = []  # list of independent threads performing preparations steps

    # get the list of projects/folders to process
    folders = getFoldersFromInputFile(inputfile)

    # for each folder:
    for folder in folders:
        # start preparations for this single folder

        # print __preparationkinds[kind].__name__
        thread = kinds[kind](folder, options)  # get proper preparations thread and call it
        threads.append(thread)
        thread.start()

    # join threads here
    for t in threads:
        t.join()


def applyAll(inputfile, options):
    kinds = getKinds()
    for kind in kinds.keys():
        apply(kind, inputfile, options)


if __name__ == '__main__':
    kinds = getKinds()

    # #################################################
    # options parsing

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument("--kind", choices=kinds.keys(), dest="kind",
                        default=kinds.keys()[0], metavar="<K>",
                        help="the preparation to be performed [default: %(default)s]")
    parser.add_argument("--input", type=str, dest="inputfile", default=__inputfile_default, metavar="FILE",
                        help="a FILE that contains the list of input projects/folders [default: %(default)s]")
    parser.add_argument("-a", "--all", action="store_true", dest="allkinds", default=False,
                        help="perform all available kinds of preparation [default: %(default)s]")
    parser.add_argument("--nobak", action="store_true", dest="nobak", default=False,
                        help="do not backup files during preparation [default: %(default)s]")

    group = parser.add_argument_group("Possible Kinds of Preparation <K>", ", ".join(kinds.keys()))

    options = parser.parse_args()

    # #################################################
    # main

    if (options.allkinds):
        applyAll(options.inputfile, options)
    else:
        apply(options.kind, options.inputfile, options)
