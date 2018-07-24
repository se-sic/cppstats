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


# modules from the std-library
import csv
import os
import re
import sys
import xmlrpclib
from argparse import ArgumentParser, RawTextHelpFormatter


# #################################################
# path adjustments, so that all imports can be done relative to these paths

__lib_subfolder = "lib"
sys.path.append(os.path.abspath(__lib_subfolder))  # lib subfolder


# #################################################
# external modules

# enums
from enum import Enum
 # python-lxml module
from lxml import etree
# pyparsing module
import pyparsing as pypa
pypa.ParserElement.enablePackrat() # speed up parsing
sys.setrecursionlimit(8000)        # handle larger expressions


# #################################################
# config:
__outputfile = "cppstats_featurelocations.csv"
__listoffeaturesfile = "listoffeatures.csv"


# #################################################
# constants:

# namespace-constant for src2srcml
_cppnscpp = 'http://www.srcML.org/srcML/cpp'
__cppnsdef = 'http://www.srcML.org/srcML/src'
__cpprens = re.compile('{(.+)}(.+)')

# conditionals - necessary for parsing the right tags
__conditionals = ['if', 'ifdef', 'ifndef']
__conditionals_elif = ['elif']
__conditionals_else = ['else']
__conditionals_endif = ['endif']
__conditionals_all = __conditionals + __conditionals_elif + \
                     __conditionals_else
__macro_define = ['define']
__macrofuncs = {}  # functional macros like: "GLIBVERSION(2,3,4)",
# used as "GLIBVERSION(x,y,z) 100*x+10*y+z"
__curfile = ''  # current processed xml-file
__defset = set()  # macro-objects
__defsetf = dict()  # macro-objects per file

# collected statistics
class __statsorder(Enum):
    FILENAME = 0    # name of the file
    LINE_START = 1  # starting line of an #ifdef block
    LINE_END = 2    # ending line of an #ifdef block (ends either at #else,
                    #  #elif, or #endif on same level)
    TYPE = 3        # either #if, #elif, or #else
    EXPRESSION = 4  # the presence condition stated in the #ifdef
    CONSTANTS = 5   # all configuration constants used in the presence condition


##################################################
# class FeatureLocation


class FeatureLocation:
    ''' A feature location consists of a filename, a start and end line,
    the type of #ifdef used (#if, #else, #elif), the presence condition
    as well as all used configuration constants.'''

    def __init__(self, filename, startline, endline, type, expression):
        global _cppnscpp  # scrml namespace tag
        namespace = '{' + _cppnscpp + '}'
        typeWithoutNamespace = '#' + type.replace(namespace, "")

        self.filename = filename # TODO use relative paths here!
        self.startline = startline
        self.endline = endline
        self.type = typeWithoutNamespace
        self.expression = expression
        self.constants = set()

    def __str__(self):
        constants = ";".join(sorted(self.constants))
        outList = (self.filename, self.startline, self.endline, self.type,
                   self.expression, constants)
        return ",".join(map(str, outList))

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        if isinstance(other, FeatureLocation):
            return self.__hash__() == other.__hash__()
        else:
            return False

    def __ne__(self, other):
        return (not self.__eq__(other))

    def getCSVList(self):
        returnList = []

        returnList.append(self.filename)
        returnList.append(self.startline)
        returnList.append(self.endline)
        returnList.append(self.type)
        returnList.append(self.expression)

        constants = ";".join(sorted(self.constants))
        returnList.append(constants)

        return returnList


##################################################
# helper functions, constants and errors


def returnFileNames(folder, extfilt=['.xml']):
    '''This function returns all files of the input folder <folder>
    and its subfolders.'''
    filesfound = list()

    if os.path.isdir(folder):
        wqueue = [os.path.abspath(folder)]

        while wqueue:
            currentfolder = wqueue[0]
            wqueue = wqueue[1:]
            foldercontent = os.listdir(currentfolder)
            tmpfiles = filter(lambda n: os.path.isfile(
                os.path.join(currentfolder, n)), foldercontent)
            tmpfiles = filter(lambda n: os.path.splitext(n)[1] in extfilt,
                              tmpfiles)
            tmpfiles = map(lambda n: os.path.join(currentfolder, n),
                           tmpfiles)
            filesfound += tmpfiles
            tmpfolders = filter(lambda n: os.path.isdir(
                os.path.join(currentfolder, n)), foldercontent)
            tmpfolders = map(lambda n: os.path.join(currentfolder, n),
                             tmpfolders)
            wqueue += tmpfolders

    return filesfound


##################################################
# parsing methods


def _collectDefines(d):
    """This functions adds all defines to a set.
    e.g. #define FEAT_WIN
    also #define FEAT_WIN 12
    but not #define GLIBCVER(x,y,z) ...
    """
    __defset.add(d[0])
    if __defsetf.has_key(__curfile):
        __defsetf[__curfile].add(d[0])
    else:
        __defsetf[__curfile] = set([d[0]])
    return d


# possible operands:
#   - hexadecimal number
#   - decimal number
#   - identifier
#   - macro function, which is basically expanded via #define
#     to an expression
__numlitl = pypa.Literal('l').suppress() | pypa.Literal('L').suppress()
__numlitu = pypa.Literal('u').suppress() | pypa.Literal('U').suppress()

__string = pypa.QuotedString('\'', '\\')

__hexadec = \
    pypa.Literal('0x').suppress() + \
    pypa.Word(pypa.hexnums). \
        setParseAction(lambda t: str(int(t[0], 16))) + \
    pypa.Optional(__numlitu) + \
    pypa.Optional(__numlitl) + \
    pypa.Optional(__numlitl)

__integer = \
    pypa.Optional('~') + \
    pypa.Word(pypa.nums + '-').setParseAction(lambda t: str(int(t[0]))) + \
    pypa.Optional(pypa.Suppress(pypa.Literal('U'))) + \
    pypa.Optional(pypa.Suppress(pypa.Literal('L'))) + \
    pypa.Optional(pypa.Suppress(pypa.Literal('L')))

__identifier = \
    pypa.Word(pypa.alphanums + '_' + '-' + '@' + '$').setParseAction(_collectDefines)
__arg = pypa.Word(pypa.alphanums + '_')
__args = __arg + pypa.ZeroOrMore(pypa.Literal(',').suppress() + \
                                 __arg)
__fname = pypa.Word(pypa.alphas, pypa.alphanums + '_')
__function = pypa.Group(__fname + pypa.Literal('(').suppress() + \
                        __args + pypa.Literal(')').suppress())


class NoEquivalentSigError(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return ("No equivalent signature found!")


class IfdefEndifMismatchError(Exception):
    def __str__(self):
        return ("Ifdef and endif do not match!")


def _parseFeatureSignatureAndRewrite(sig):
    """This function parses a given feature-signature and rewrites
    the signature according to the given __pt mapping.
    """
    # this dictionary holds all transformations of operators from
    # the origin (cpp) to the compare (language)
    # e.g. in cpp && stands for the 'and'-operator.
    # the equivalent in maple (which is used for comparison)
    # is '&and'
    # if no equivalence can be found a name rewriting is done
    # e.g. 'defined'
    __pt = {
        #'defined' : 'defined_',
        'defined': '',
        '!': '&not',
        '&&': '&and',
        '||': '&or',
        '<': '<',
        '>': '>',
        '<=': '<=',
        '>=': '>=',
        '==': '=',
        '!=': '!=',
        '*': '*',  # needs rewriting with parenthesis
        '/': '/',
        '%': '',  # needs rewriting a % b => modp(a, b)
        '+': '+',
        '-': '-',
        '&': '',  # needs rewriting a & b => BitAnd(a, b)
        '|': '',  # needs rewriting a | b => BitOr(a, b)
        '>>': '>>',  # needs rewriting a >> b => a / (2^b)
        '<<': '<<',  # needs rewriting a << b => a * (2^b)
    }

    def _rewriteOne(param):
        """This function returns each one parameter function
        representation for maple."""
        if param[0][0] == '!':
            ret = __pt[param[0][0]] + '(' + str(param[0][1]) + ')'
        if param[0][0] == 'defined':
            ret = __pt[param[0][0]] + str(param[0][1])
        return ret


    def _rewriteTwo(param):
        """This function returns each two parameter function
        representation for maple."""
        # rewriting rules
        if param[0][1] == '%':
            return 'modp(' + param[0][0] + ',' + param[0][2] + ')'

        ret = ' ' + __pt[param[0][1]] + ' '
        ret = '(' + ret.join(map(str, param[0][0::2])) + ')'

        if param[0][1] in ['<', '>', '<=', '>=', '!=', '==']:
            ret = '(true &and ' + ret + ')'
        return ret

    operand = __string | __hexadec | __integer | \
              __function | __identifier
    compoperator = pypa.oneOf('< > <= >= == !=')
    calcoperator = pypa.oneOf('+ - * / & | << >> %')
    expr = pypa.operatorPrecedence(operand, [
        ('defined', 1, pypa.opAssoc.RIGHT, _rewriteOne),
        ('!', 1, pypa.opAssoc.RIGHT, _rewriteOne),
        (calcoperator, 2, pypa.opAssoc.LEFT, _rewriteTwo),
        (compoperator, 2, pypa.opAssoc.LEFT, _rewriteTwo),
        ('&&', 2, pypa.opAssoc.LEFT, _rewriteTwo),
        ('||', 2, pypa.opAssoc.LEFT, _rewriteTwo),
    ])

    try:
        rsig = expr.parseString(sig)[0]
    except pypa.ParseException, e:
        print('ERROR (parse): cannot parse sig (%s) -- (%s)' %
              (sig, e.col))
        return sig
    except RuntimeError:
        print('ERROR (time): cannot parse sig (%s)' % (sig))
        return sig
    except ValueError, e:
        print('ERROR (parse): cannot parse sig (%s) ~~ (%s)' %
              (sig, e))
        return sig
    return ''.join(rsig)


def _collapseSubElementsToList(node):
    """This function collapses all subelements of the given element
    into a list used for getting the signature out of an #ifdef-node."""
    # get all descendants - recursive - children, children of children ...
    itdesc = node.itertext()

    # iterate over the elemtents and add them to a list
    return ''.join([it for it in itdesc])


def _parseAndAddDefine(node):
    """This function extracts the identifier and the corresponding
    expansion from define macros. Later on these are used in conditionals
    in order to make them comparable."""

    define = _collapseSubElementsToList(node)

    # match only macro functions, no macro objects
    anytext = pypa.Word(pypa.printables)
    macrodef = pypa.Literal('#define').suppress() + __function + anytext

    try:
        res = macrodef.parseString(define)
    except pypa.ParseException:
        return

    iden = ''.join(map(str, res[0]))
    expn = res[-1]
    para = res[1:-1]
    __macrofuncs[iden] = (para, expn)


##################################################
# #ifdef-related functions


def _getMacroSignature(ifdefnode):
    """This function gets the signature of an ifdef or corresponding macro
    out of the xml-element and its descendants. Since the macros are held
    inside the xml-representation in an own namespace, all descendants
    and their text corresponds to the macro-signature.
    """
    # get either way the expr-tag for if and elif
    # or the name-tag for ifdef and ifndef,
    # which are both the starting point for signature
    # see the srcml.dtd for more information
    nexpr = []
    res = ''
    _, tag = __cpprens.match(ifdefnode.tag).groups()

    # get either the expr or the name tag,
    # which is always the second descendant
    if (tag in ['if', 'elif', 'ifdef', 'ifndef']):
        nexpr = [itex for itex in ifdefnode.iterdescendants()]
        if (len(nexpr) == 1):
            res = nexpr[0].tail
        else:
            nexpr = nexpr[1]
            res = ''.join([token for token in nexpr.itertext()])
    return res


def _getFeatureSignature(condinhist):
    """This method returns a feature signature that belongs to the
    current history of conditional inclusions held in condinhist."""
    # we need to rewrite the elements before joining them to one
    # signature; reason is elements like else or elif, which mean
    # basically invert the fname found before
    # rewritelist = [(tag, fname, <invert true|false>)]
    rewritelist = [None] * len(condinhist)
    cur = -1

    for tag, fname in condinhist:
        cur += 1
        if tag == 'if':
            rewritelist[cur] = (tag, fname, False)
        if tag in ['elif', 'else']:
            (t, f, _) = rewritelist[cur - 1]
            rewritelist[cur - 1] = (t, f, True)
            rewritelist[cur] = (tag, fname, False)

    fsig = ''

    for (tag, fname, invert) in rewritelist:
        if invert:
            fname = '!(' + fname + ')'
        if fsig == '':
            fsig = fname
            continue
        if tag == 'else':
            continue
        if tag in ['if', 'elif']:
            fsig = '(' + fsig + ') && (' + fname + ')'
            continue
    return fsig


def _getFeatures(root, featlocations):
    """This function returns all features in the source-file.
    A feature is defined as an enframement of soure-code. The frame
    consists of an ifdef (conditional) and an endif-macro. The function
    returns a tuple with the following format:
    ({<feature signature>: (<feature depth>, [<feature code>])},
     {<feature signature>: [<feature tags-enclosed>]},
     [(<feature signature>, (<start>, <end>))])

    feature elements: Every feature element reflects one part of a
    feature withing the whole source-code, that is framed by contional
    and endif-macros.

    featuresgrinner: All tags from the feature elements (see above).
    featuresgrouter: All tags from the elements arround the feature.
    """

    def _wrapGrOuterUp(fouter, featuresgrouter, eelem):
        itouter = fouter[-1]  # feature surround tags
        fouter = fouter[:-1]

        for i in xrange(0, len(itouter)):
            sig = itouter[i][0]
            elem = itouter[i][1]

            # start of next location is the end of the current one,
            # or else the #endif in eelem
            end = itouter[i + 1][1] if (i < len(itouter) - 1) else eelem

            featuresgrouter.append((sig, elem, end))
        return (fouter, featuresgrouter)


    def _wrapFeatureUp(features, featuresgrinner, fcode, flist, finner):
        # wrap up the feature
        if (not flist):
            raise IfdefEndifMismatchError()
        itsig = flist[-1]  # feature signature
        flist = flist[:-1]
        itcode = fcode[-1]  # feature code
        itcode = itcode.replace('\n\n', '\n')
        itcode = itcode[1:]  # itcode starts with '\n'; del
        fcode = fcode[:-1]
        itinner = finner[-1]  # feature enclosed tags
        finner = finner[:-1]

        # handle the feature code
        if (features.has_key(itsig)):
            features[itsig][1].append(itcode)
        else:
            features[itsig] = (len(flist) + 1, [itcode])

        # handle the inner granularity
        featuresgrinner.append((itsig, itinner))
        return (features, featuresgrinner, fcode, flist, finner)

    features = {}  # see above; return value
    featuresgrinner = []  # see above; return value
    featuresgrouter = []  # see above; return value
    flist = []  # holds the features in order
    # list empty -> no features to parse
    # list used as a stack
    # last element = top of stack;
    # and the element we currently
    # collecting source-code lines for
    fouter = []  # holds the xml-nodes of the ifdefs/endifs
    # in order like flist
    fcode = []  # holds the code of the features in
    # order like flist
    finner = []  # holds the tags of the features in
    # order like flist
    condinhist = []  # order of the conditional includes
    # with feature names
    parcon = False  # parse-conditional-flag
    parend = False  # parse-endif-flag
    _ = 0  # else and elif depth

    # iterate over all tags separately <start>- and <end>-tag
    for event, elem in etree.iterwalk(root, events=("start", "end")):
        ns, tag = __cpprens.match(elem.tag).groups()

        # handling conditionals
        # hitting on conditional-macro
        if ((tag in __conditionals_all)
            and (event == 'start')
            and (ns == _cppnscpp)):  # check the cpp:namespace
            parcon = True

        # hitting next conditional macro; any of ifdef, else or elif
        if ((tag in __conditionals_all)
            and (event == 'end')
            and (ns == _cppnscpp)):  # check the cpp:namespace
            parcon = False

            # with else or elif we finish up the last if, therefor
            # we can applicate the wrapup
            if ((tag in __conditionals_else)
                or (tag in __conditionals_elif)):
                (features, featuresgrinner,
                 fcode, flist, finner) = _wrapFeatureUp(features,
                                                        featuresgrinner, fcode, flist, finner)

            fname = _getMacroSignature(elem)
            if fname:
                condinhist.append((tag, fname))
            else:
                condinhist.append((tag, ''))

            fsig = _getFeatureSignature(condinhist)
            if (tag in __conditionals): fouter.append([])
            fouter[-1] += ([(fsig, elem)])
            flist.append(fsig)
            fcode.append('')
            finner.append([])

        # hitting end-tag of elif-macro
        if ((tag in __conditionals_elif)
            and (event == 'end')
            and (ns == _cppnscpp)):
            parcon = False

        # hitting end-tag of define-macro
        if ((tag in __macro_define) \
                    and (event == 'end') \
                    and (ns == _cppnscpp)):
            _parseAndAddDefine(elem)

        # iterateting in subtree of conditional-node
        if parcon:
            continue

        # handling endif-macro
        # hitting an endif-macro start-tag
        if ((tag in __conditionals_endif) \
                    and (event == "start") \
                    and (ns == _cppnscpp)):  # check the cpp:namespace
            parend = True

        # hitting the endif-macro end-tag
        if ((tag in __conditionals_endif) \
                    and (event == "end") \
                    and (ns == _cppnscpp)):  # check the cpp:namespace
            parend = False

            (features, featuresgrinner, fcode, flist, finner) = \
                _wrapFeatureUp(features, featuresgrinner,
                               fcode, flist, finner)
            (fouter, featuresgrouter) = _wrapGrOuterUp(fouter,
                                                       featuresgrouter, elem)

            # transform feature locations and append them to global list
            for (asig, aselem, aeelem) in featuresgrouter:
                floc = FeatureLocation(__curfile, aselem.sourceline - 1, aeelem.sourceline - 1,
                                       aselem.tag, asig)
                featlocations.add(floc)

            while (condinhist[-1][0] != 'if'):
                condinhist = condinhist[:-1]
            condinhist = condinhist[:-1]

        # iterating the endif-node subtree
        if parend:
            continue

        # collect the source-code of the feature
        if (len(flist)):
            if ((event == "start") and (elem.text)):
                fcode[-1] += elem.text
            if ((event == "end") and (elem.tail)):
                fcode[-1] += elem.tail

            if (ns == __cppnsdef or tag not in __conditionals_all):
                finner[-1].append((tag, event, elem.sourceline))

    if (flist):
        raise IfdefEndifMismatchError()

    return (features, featuresgrinner, featuresgrouter)


def _getFeaturesAtLocations(flocations, defines):
    """TODO"""

    sigs = [x.expression for x in flocations]

    for d in defines:
        dre = re.compile(r'\b' + d + r'\b')  # using word boundaries
        vec = map(lambda s: not dre.search(s) is None, sigs)

        for floc, contained in zip(flocations, vec):
            if (contained):
                floc.constants.add(d)


##################################################
# output file


def _prologCSV(folder, file, headings):
    """prolog of the CSV-output file
    no corresponding _epilogCSV."""
    fd = open(os.path.join(folder, file), 'w')
    fdcsv = csv.writer(fd, delimiter=',')
    fdcsv.writerow(["sep=,"])
    fdcsv.writerow(headings)
    return (fd, fdcsv)


##################################################
# main method

def resetModule() :
    global __macrofuncs, __defset, __defsetf
    __macrofuncs = {}       # functional macros like: "GLIBVERSION(2,3,4)",
                            # used as "GLIBVERSION(x,y,z) 100*x+10*y+z"
    __defset = set()        # macro-objects
    __defsetf = dict()      # macro-objects per file


def apply(folder, options):
    """This function applies the analysis to all xml-files in that
    directory and take the results and joins them together. Results
    are getting written into the fdcsv-file."""
    # overall status variables
    resetModule()

    featlocations = set()  # list of feature locations of class FeatureLocation

    # outputfile
    fd, fdcsv = _prologCSV(os.path.join(folder, os.pardir), __outputfile, __statsorder.__members__.keys())

    # list-of-features file
    loffheadings = ['FILENAME', 'CONSTANTS']
    loffrow = [None]*len(loffheadings)
    loffhandle, loffwriter = _prologCSV(os.path.join(folder, os.pardir), __listoffeaturesfile, loffheadings)

    # preparations for file-loop
    global __curfile
    files = returnFileNames(folder, ['.xml'])
    files.sort()
    fcount = 0
    ftotal = len(files)

    #TODO rewrite comment! get statistics for all files; write results into csv
    # and merge the features
    for file in files:
        __curfile = file

        try:
            tree = etree.parse(file)
        except etree.XMLSyntaxError:
            print("ERROR: cannot parse (%s). Skipping this file." % os.path.join(folder, file))
            continue

        root = tree.getroot()
        try:
            (features, _, _) = _getFeatures(root, featlocations)
        except IfdefEndifMismatchError:
            print("ERROR: ifdef-endif mismatch in file (%s)" % (os.path.join(folder, file)))
            continue

        # parse features and get all defined configuration constants
        for (sig, (depth, code)) in features.iteritems():
            psig = _parseFeatureSignatureAndRewrite(sig)

        # file successfully parsed
        fcount += 1
        print('INFO: parsing file (%5d) of (%5d) -- (%s).' % (fcount, ftotal, os.path.join(folder, file)))

        # print features for this file to list-of-features file
        featureslist = list(__defsetf[__curfile]) \
            if __defsetf.has_key(__curfile) else '' # list of features within the current file
        listoffeaturesstring = ';'.join(sorted(featureslist)) # sort and join
        loffwriter.writerow([__curfile, listoffeaturesstring]) # write row to file


    # collect feature locations and consisting used features
    featurelocations = list(featlocations)
    featurelocations.sort(key=lambda x: (x.filename, x.startline))
    _getFeaturesAtLocations(featurelocations, list(__defset))

    # print each feature location as one line into output file
    for floc in featurelocations:

        #adjust file name if wanted
        if options.filenamesRelative : # relative file name (root is project folder (not included in path))
            floc.filename = os.path.relpath(floc.filename, folder)

        if options.filenames == options.FILENAME_SRCML : # cppstats file names
            pass # nothing to do here, as the file path is the cppstats path by default
        if options.filenames == options.FILENAME_SOURCE : # source file name
            floc.filename = floc.filename.replace(".xml", "").replace("/_cppstats/", "/source/", 1)

        # print floc information to CSV file
        row = floc.getCSVList()
        fdcsv.writerow(row)

    # close output files
    fd.close() # __outputfile
    loffhandle.close() # __listoffeaturesfile



# ##################################################
# add command line options

def addCommandLineOptionsMain(optionparser):
    ''' add command line options for a direct call of this script'''
    optionparser.add_argument("--folder", dest="folder",
                  help="input folder [default=.]", default=".")


def addCommandLineOptions(optionparser):
    pass


# ################################################
# path of the main output file

def getResultsFile():
    return __outputfile


##################################################
if __name__ == '__main__':

    ##################################################
    # options parsing
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    addCommandLineOptionsMain(parser)
    addCommandLineOptions(parser)

    options = parser.parse_args()

    folder = os.path.abspath(options.folder)

    if (os.path.isdir(folder)):
        apply(folder)
    else:
        sys.exit(-1)
