#!/usr/bin/env python
# -*- coding: utf-8 -*-
# cppstats is a suite of analyses for measuring C preprocessor-based
# variability in software product lines.
# Copyright (C) 2011-2015 University of Passau, Germany
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
#     Jörg Liebig <joliebig@fim.uni-passau.de>
#     Claus Hunsen <hunsen@fim.uni-passau.de>


# modules from the std-library
import csv
import itertools
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
 # statistics module
from statlib import pstat
# pyparsing module
import pyparsing as pypa
pypa.ParserElement.enablePackrat() # speed up parsing
sys.setrecursionlimit(8000)        # handle larger expressions


##################################################
# config:
__outputfile = "cppstats_derivative.csv"

# error numbers:
__errorfexp = 0
__errormatch = []
##################################################


##################################################
# constants:
# namespace-constant for src2srcml
__cppnscpp = 'http://www.srcML.org/srcML/cpp'
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
__macrofuncs = {}       # functional macros like: "GLIBVERSION(2,3,4)",
                        # used as "GLIBVERSION(x,y,z) 100*x+10*y+z"
__curfile = ''          # current processed xml-file
__defset = set()        # macro-objects
__defsetf = dict()      # macro-objects per file

# collected statistics
class __statsorder(Enum):
    FILENAME = 0          # name of the file
    NUMANNOTATIONS = 1    # number of all annotations
    NOIANNOTATIONS = 2    # number of interacting annotations
                          # example: A&B&C&D --> A&B, B&C, B&D
                          # example: A&B&C&D -/> A&B, B&C, A&C

##################################################


##################################################
# helper functions, constants and errors
def returnFileNames(folder, extfilt = ['.xml']):
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

def uniqueItems(l):
    l = sorted(l)
    return list(k for k, _ in itertools.groupby(l))

def _flatten(l):
    """This function takes a list as input and returns a flatten version
    of the list. So all nested lists are unpacked and moved up to the
    level of the list."""
    i = 0
    while i < len(l):
        while isinstance(l[i], list):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i+1] = l[i]
        i += 1
    return l


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
        pypa.Word(pypa.hexnums).\
        setParseAction(lambda t: str(int(t[0], 16))) + \
        pypa.Optional(__numlitu) + \
        pypa.Optional(__numlitl) + \
        pypa.Optional(__numlitl)

__integer = \
        pypa.Optional('~') + \
        pypa.Word(pypa.nums+'-') + \
        pypa.Optional(__numlitu) + \
        pypa.Optional(__numlitl) + \
        pypa.Optional(__numlitl)

__identifier = \
        pypa.Word(pypa.alphanums+'_'+'-'+'@'+'$')   # @ not allowed but they do occur
__arg = pypa.Word(pypa.alphanums+'_')
__args = __arg + pypa.ZeroOrMore(pypa.Literal(',').suppress() + \
        __arg)
__fname = pypa.Word(pypa.alphas + '_' + '#', pypa.alphanums + '_' + '#')
__function = pypa.Group(__fname + pypa.Literal('(').suppress() + \
        __args + pypa.Literal(')').suppress())


class NoEquivalentSigError(Exception):
    def __init__(self):
        pass
    def __str__(self):
        return ("No equivalent signature found!")

class IfdefEndifMismatchError(Exception):
    def __init__(self):
        pass
    def __str__(self):
        return ("Ifdef and endif do not match!")

##################################################


def _collapseSubElementsToList(node):
    """This function collapses all subelements of the given element
    into a list used for getting the signature out of an #ifdef-node."""
    # get all descendants - recursive - children, children of children ...
    itdesc = node.itertext()

    # iterate over the elemtents and add them to a list
    return ''.join([it for it in itdesc])



def _parseFeatureSignature(sig):
    """This function parses a given feature-signature."""
    mal = set()

    def _rewriteOne(p): return ''
    def _rewriteTwo(p): return ''
    def _addIdentifier2Mal(p): mal.add(p[0])

    operand = __string | __hexadec | __function | __integer | \
    __identifier.setParseAction(_addIdentifier2Mal)
    compoperator = pypa.oneOf('< > <= >= == !=')
    calcoperator = pypa.oneOf('+ - * / % & | << >>')
    expr = pypa.operatorPrecedence(operand, [
        ('defined', 1, pypa.opAssoc.RIGHT, _rewriteOne),
        ('!',  1, pypa.opAssoc.RIGHT, _rewriteOne),
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
    return (mal, ''.join(rsig))


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


def _prologCSV(folder):
    """prolog of the CSV-output file
    no corresponding _epilogCSV."""
    fd = open(os.path.join(folder, __outputfile), 'w')
    fdcsv = csv.writer(fd, delimiter=',')
    fdcsv.writerow(__statsorder.__members__.keys())
    return (fd, fdcsv)


def _countNestedIfdefs(root):
    """This function counts the number of nested ifdefs (conditionals)
    within the source-file."""
    cncur = 0
    cnlist = []
    elements = [it for it in root.iterdescendants()]

    for elem in elements:
        ns, tag = __cpprens.match(elem.tag).groups()
        if ((tag in __conditionals_endif)
                and (ns == __cppnscpp)): cncur -= 1
        if ((tag in __conditionals)
                and (ns == __cppnscpp)):
            cncur += 1
            cnlist.append(cncur)

    if (len(cnlist) > 0):
        nnimax = max(cnlist)
        nnitmp = filter(lambda n: n > 0, cnlist)
        nnimean = pstat.stats.lmean(nnitmp)
    else:
        nnimax = 0
        nnimean = 0
    if (len(cnlist) > 1): nnistd = pstat.stats.lstdev(cnlist)
    else: nnistd = 0
    return (nnimax, nnimean, nnistd)


def _getFeatureSignature(condinhist):
    """This method returns a feature signature that belongs to the
    current history of conditional inclusions held in condinhist."""
    # we need to rewrite the elements before joining them to one
    # signature; reason is elements like else or elif, which mean
    # basically invert the fname found before
    # rewritelist = [(tag, fname, <invert true|false>)]
    rewritelist = [None]*len(condinhist)
    cur = -1

    for tag, fname in condinhist:
        cur += 1
        if tag == 'if':
            rewritelist[cur] = (tag, fname, False)
        if tag in ['elif', 'else']:
            (t, f, _) = rewritelist[cur-1]
            rewritelist[cur-1] = (t, f, True)
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


def _getASTHistory(node):
    """This function returns a list with a AST History until
    the given parameter node. The given node is the macro-conditional
    node itself. """
    ancs = [anc for anc in node.iterancestors()]
    asth = []

    for anc in ancs:
        _, tag = __cpprens.match(anc.tag).groups()
        asth.append(tag)
    return asth


def _getASTFuture(node):
    """This function returns a list with a AST Future beginning from
    the given parameter node. The given node is the macro-conditional
    node itself."""

    dess = []
    while (node is not None):
        dess += [sib for sib in node.itersiblings(preceding=False)]
        node = node.getparent()

    desh = []
    for des in dess:
        _, tag = __cpprens.match(des.tag).groups()
        desh.append(tag)
    return desh


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


def _getFeatures(root):
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
        itouter = fouter[-1]             # feature surround tags
        fouter = fouter[:-1]

        selem = itouter[0][1]
        for (sig, _) in itouter:
            featuresgrouter.append((sig, selem, eelem))
        return (fouter, featuresgrouter)


    def _wrapFeatureUp(features, featuresgrinner, fcode, flist, finner):
        # wrap up the feature
        if (not flist):
            raise IfdefEndifMismatchError()
        itsig = flist[-1]                # feature signature
        flist = flist[:-1]
        itcode = fcode[-1]               # feature code
        itcode = itcode.replace('\n\n', '\n')
        itcode = itcode[1:]              # itcode starts with '\n'; del
        fcode = fcode[:-1]
        itinner = finner[-1]             # feature enclosed tags
        finner = finner[:-1]

        # handle the feature code
        if (features.has_key(itsig)):
            features[itsig][1].append(itcode)
        else:
            features[itsig] = (len(flist)+1, [itcode])

        # handle the inner granularity
        featuresgrinner.append((itsig, itinner))
        return (features, featuresgrinner, fcode, flist, finner)

    features = {}           # see above; return value
    featuresgrinner = []    # see above; return value
    featuresgrouter = []    # see above; return value
    flist = []              # holds the features in order
                            # list empty -> no features to parse
                            # list used as a stack
                            # last element = top of stack;
                            # and the element we currently
                            # collecting source-code lines for
    fouter = []             # holds the xml-nodes of the ifdefs/endifs
                            # in order like flist
    fcode = []              # holds the code of the features in
                            # order like flist
    finner = []             # holds the tags of the features in
                            # order like flist
    condinhist = []         # order of the conditional includes
                            # with feature names
    parcon = False          # parse-conditional-flag
    parend = False          # parse-endif-flag
    _ = 0                   # else and elif depth

    # iterate over all tags separately <start>- and <end>-tag
    for event, elem in etree.iterwalk(root, events=("start", "end")):
        ns, tag = __cpprens.match(elem.tag).groups()

        # handling conditionals
        # hitting on conditional-macro
        if ((tag in __conditionals_all)
                and (event == 'start')
                and (ns == __cppnscpp)):    # check the cpp:namespace
            parcon = True

        # hitting next conditional macro; any of ifdef, else or elif
        if ((tag in __conditionals_all)
                and (event == 'end')
                and (ns == __cppnscpp)):    # check the cpp:namespace
            parcon = False

            # with else or elif we finish up the last if, therefor
            # we can applicate the wrapup
            if ((tag in __conditionals_else)
                    or (tag in __conditionals_elif)):
                (features, featuresgrinner,
                        fcode, flist, finner) = _wrapFeatureUp(features,
                        featuresgrinner, fcode, flist, finner)

            fname = _getMacroSignature(elem)
            if fname: condinhist.append((tag, fname))
            else: condinhist.append((tag, ''))

            fsig = _getFeatureSignature(condinhist)
            if (tag in __conditionals): fouter.append([])
            fouter[-1] += ([(fsig, elem)])
            flist.append(fsig)
            fcode.append('')
            finner.append([])

        # hitting end-tag of elif-macro
        if ((tag in __conditionals_elif)
                and (event == 'end')
                and (ns == __cppnscpp)):
            parcon = False

        # hitting end-tag of define-macro
        if ((tag in __macro_define) \
                and (event == 'end') \
                and (ns == __cppnscpp)):
            _parseAndAddDefine(elem)

        # iterateting in subtree of conditional-node
        if parcon:
            continue

        # handling endif-macro
        # hitting an endif-macro start-tag
        if ((tag in __conditionals_endif) \
                and (event == "start") \
                and (ns == __cppnscpp)):    # check the cpp:namespace
            parend = True

        # hitting the endif-macro end-tag
        if ((tag in __conditionals_endif) \
                and (event == "end") \
                and (ns == __cppnscpp)):    # check the cpp:namespace
            parend = False

            (features, featuresgrinner, fcode, flist, finner) = \
                _wrapFeatureUp(features, featuresgrinner,
                fcode, flist, finner)
            (fouter, featuresgrouter) = _wrapGrOuterUp(fouter,
            featuresgrouter, elem)

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


def _getOuterGranularity(fnodes):
    """This function determines and returns the outer granularity
    metrics for each feature. Therefore we get a list holding all
    features in order and their start and end node (conditionals)
    from the xml-tree."""
    grouter = list()

    for (sig, selem, _) in fnodes:
        tags = _getASTHistory(selem)[:-1]    # cut of unit-tag
        grouter.append((sig, tags, selem.sourceline))
    return grouter


def _getOuterGranularityStats(lgran):
    """This function determines the granularity level of the
    given lgran elements. We distinguish the following levels:
    - outer block gran (function, struct, union)
    - inner block gran (if, for, while, do)
    - expression gran (condition in if, for, while, do)
    - statement gran
    - parameter gran
    """
    gotopbgr = 0
    gofunbgr = 0
    gostrbrl = 0        # local
    gostrbrg = 0        # global
    goinnbgr = 0
    goexpbgr = 0
    gostmbgr = 0
    gopambgr = 0
    goerror  = 0

    for (_, gran, line) in lgran:
        if len(gran) == 0:
            gotopbgr += 1
            continue
        if gran[0] in ['block']:
            if len(gran) == 1:    # configure the method signature
                gofunbgr += 1
                continue
            if gran[1] in ['function', 'extern', 'block']:
                gofunbgr += 1
            elif gran[1] in ['struct', 'union',
                    'enum']:    # test_struct_union_enum.c
                if 'function' in gran[2:]: gostrbrl += 1
                else: gostrbrg += 1
            elif gran[1] in ['expr']:
                if 'function' in gran[2:]: gostrbrl += 1
                else: gostrbrg += 1
            elif gran[1] in ['while', 'for', 'then', 'do',
                    'else', 'switch', 'case', 'default']:
                goinnbgr += 1                # test_loop.c
            elif gran[1] in ['decl']:        # test_struct_union_enum.c
                if 'function' in gran[3:]: gostrbrl += 1
                else: gostrbrg += 1
            else:
                print('ERROR: gran (%s) at this '
                        'level unknown (line %s)' % (gran, line))
                goerror += 1
            continue
        elif gran[0] in ['expr']:
            if gran[1] in ['expr_stmt']:                # test_stmt.c
                gostmbgr += 1
            elif gran[1] in ['condition', 'return']:    # test_condition.c
                goexpbgr += 1
            elif gran[1] in ['argument']:               # test_call.c
                gostmbgr += 1
            elif gran[1] in ['block']:
                if 'function' in gran[2:]: gostrbrl += 1
                else: gostrbrg += 1
            elif gran[1] in ['init', 'index']:          # test_stmt.c
                gostmbgr += 1
            else:
                print('ERROR: gran (%s) at this level'
                        'unknown (line %s)' % (gran, line))
                goerror += 1
            continue
        elif gran[0] in ['while', 'do']:                # test_loop.c
            goinnbgr += 1
            continue
        elif gran[0] in ['expr_stmt'] and len(gran) == 1:
            gostmbgr += 1
            continue
        elif gran[:3] == ['expr_stmt', 'block', 'struct']:
            if 'function' in gran[2:]: gostrbrl += 1
            else: gostrbrg += 1
            continue
        elif gran[0] in ['decl_stmt']:            # test_stmt.c
            gostmbgr += 1
            continue
        elif gran[0] in ['condition']:            # test_condition.c
            goexpbgr += 1
            continue
        elif gran[0] in ['if', 'else', 'case', 'default',
                'then', 'for']:    # test_condition.c
            goinnbgr += 1
            continue
        elif gran[0] in ['parameter_list',
                'argument_list']:        # test_call.c
            gopambgr += 1
            continue
        elif gran[0] in ['argument'] and gran[1] in ['argument_list']:
            gostmbgr += 1
        elif gran[0] in ['init'] and gran[1] in ['decl']:    # test_stmt.c
            gostmbgr += 1
            continue
        elif gran[0] in ['function']:            # function prototype
            continue
        else:
            print('ERROR: outer granularity (%s, %s) not recognize!' % \
                    (gran, line))
            goerror += 1

    return (gotopbgr, gofunbgr, gostrbrl, gostrbrg,
            goinnbgr, goexpbgr, gostmbgr, gopambgr, goerror)


def _getInnerGranularityStats(igran):
    """This method returns a tuple with the information about the
    inner granularity. We distinguish the following granularities:
    - adding a named block, ... (a whole block with a name:
            function, type, ...)
    - adding a unnamed block, ... (a block without a name:
            if, while, for, ...)
    - adding a simple statement
    - adding a expression
    - adding a parameter
    """
    gmacrogr = 0
    ginablgr = 0
    giunblgr = 0
    giexpbgr = 0
    gistmbgr = 0
    gipambgr = 0
    gierror = 0

    skiptilltag = ''

    for (_, gran) in igran:
        for (tag, event, line) in gran:
            if (skiptilltag != ''):
                if (tag == skiptilltag[0]
                        and event == 'end'
                        and line == skiptilltag[2]):
                    skiptilltag = ''
                continue

            if tag in ['name', 'endif']: continue
            elif tag in ['define', 'directive', 'include',
                    'macro', 'undef']:
                gmacrogr += 1
            elif tag in ['struct', 'union', 'enum', 'function', 'extern',
                    'function_decl', 'decl_stmt', 'typedef']:
                ginablgr += 1
            elif tag in ['if', 'while', 'return', 'then',
                    'for', 'do', 'case', 'else', 'block']:
                giunblgr += 1
            elif tag in ['param', 'argument']:
                gipambgr += 1
            elif tag in ['expr']:
                giexpbgr += 1
            elif tag in ['condition']:
                giexpbgr += 1
            elif tag in ['expr_stmt', 'decl', 'init']:
                gistmbgr += 1
            else:
                print('ERROR: inner granularity (%s, %s, %s)) '
                        'not recognized!' % (tag, event, line))
                gierror += 1
                continue
            if event == 'start': skiptilltag = (tag, event, line)

    return (gmacrogr, ginablgr, giunblgr, giexpbgr, gistmbgr, gierror)


def _getFeatureStats(features):
    """This function determines and returns the following statistics
    about the features:
        - nof            # number of features
        - nod            # number of defines
        - lof            # lines of feature code (sum)
        - lofmin         # minimum line of feature code
        - lofmax         # maximum number of feature code lines
        - lofmean        # mean of feature code lines
        - lofstd         # std-deviation of feature code lines
    """
    lof = 0
    nod = 0
    lofmin = -1            # feature-code can be empty
    lofmax = 0
    lofmean = 0
    lofstd = 0
    nof = len(features.keys())
    tmp = [item for (_, item) in features.itervalues()]
    tmp = _flatten(tmp)
    floflist = map(lambda n: n.count('\n'), tmp)

    if (len(floflist)):
        lofmin = min(floflist)
        lofmax = max(floflist)
        lof = reduce(lambda m,n: m+n, floflist)
        lofmean = pstat.stats.lmean(floflist)

    if (len(floflist) > 1):
        lofstd = pstat.stats.lstdev(floflist)

    return (nof, nod, lof, lofmin, lofmax, lofmean, lofstd)


def _getFeaturesDepthOne(features):
    """This function returns all features that have the depth of one."""
    nof1 = filter(lambda (sig, (depth, code)): depth == 1, features.iteritems())
    return nof1


def _distinguishFeatures(features):
    """This function returns a tuple with dicts, each holding
    one type of feature. The determination is according to the
    given macro-signatures. Following differentiation according
    to the macro-signatures:
    1. "||" -> shared code
    2. "&&" -> derivative
    3. "||" & "&&" -> ??

    Further more a differentiation according to the feature-code
    is also done. We differ here:
    1. het -> all code feature code excerpts are different
    2. hom -> all feature code are the same
    3. hethome -> the feature code is a mix of both
    """

    def _compareFeatureCode(fcode):
        """This function compares the each part, of the code the
        belongs to a feature with all the other parts. We do this
        in order to find out, what kind of "introduction" is made
        at the feature signature points. For instance:
        """
        fcodes = set(fcode)

        if (len(fcodes) == 1 and len(fcode) > 1):
            return "hom"

        if (len(fcode) == len(fcodes)):
            return "het"

        if (len(fcode) > len(fcodes)):
            return "hethom"

    scode = {}
    deriv = {}
    desc = {}
    het = {}
    hom = {}
    hethom = {}

    for (key, (_, item)) in features.iteritems():
        # distinguish according to feature-signature
        # shared code
        if ('||' in key and (not '&&' in key)):
            scode[key] = item

        # derivative only &&
        if ('&&' in key and (not '||' in key)):
            deriv[key] = item

        # combination shared code and derivative
        if ('&&' in key and '||' in key):
            desc[key] = item

        # distinguish according to feature-code
        ret = _compareFeatureCode(item)
        if (ret == "het"):
            het[key] = item
        if (ret == "hom"):
            hom[key] = item
        if (ret == "hethom"):
            hethom[key] = item

    return (scode, deriv, desc, het, hom, hethom)


def _getNumOfDefines(defset):
    """This method returns the number of defines, that have the following
    structure:
    #define FEAT_A
    #define FEAT_B 5
    Both defines are macro-objects. macro-functions like the following
    are not considered.
    #define CHECKVERSION(x,y,z) x*100+y*10+z
    All determined elements are derived from the ifdef macros.
    """
    # basic operation of this function is to check __defset against
    # __macrofuncs
    funcmacros = __macrofuncs.keys()
    funcmacros = map(lambda n: n.split('(')[0], funcmacros)
    funcmacros = set(funcmacros)

    return len((defset - funcmacros))


def _getScatteringTanglingDegrees(sigs, defines):
    """This method returns the mean and the standard-deviation of
    defines according to the given mapping of a define to occurances
    in the signatures. The input is all feature-signatures and
    a all defines.

    The measurement of scattering and tangling degree is error-prone
    since a define that is used in conditional inclusions might not
    be defined at the moment of usage.
    """

    def __add(x, y):
        """This method is a helper function to add values
        of lists pairwise. See below for more information."""
        return x+y

    scat = list()           # relation define to signatures
    tang = [0]*len(sigs)    # signatures overall
    for d in defines:
        dre = re.compile(r'\b'+d+r'\b')        # using word boundaries
        vec = map(lambda s: not dre.search(s) is None, sigs)
        scat.append(vec.count(True))
        tang = map(__add, tang, vec)

    if (len(scat)): sdegmean = pstat.stats.lmean(scat)
    else: sdegmean = 0
    if (len(scat) > 1): sdegstd = pstat.stats.lstdev(scat)
    else: sdegstd = 0

    if (len(tang)): tdegmean = pstat.stats.lmean(tang)
    else: tdegmean = 0
    if (len(tang) > 1): tdegstd = pstat.stats.lstdev(tang)
    else: tdegstd = 0

    return (sdegmean, sdegstd, tdegmean, tdegstd)


def _getGranularityStats(fcodetags):
    """This method returns a tuple of NOO with decl_stmt, expr_stmt
    and signature changes.
    TODO which granularity to use?
    if   -> block
    for  -> block
    expr -> expression
    """
    _interestingtags = [
        'define',            # define statement
        'include',            # include statement
        'decl_stmt',        # declaration statement
        'expr_stmt',        # expression statement
        'function_decl',    # function declaration
        'parameter_list',    # parameter list
        'param',            # parameter
    ]
    _curskiptag = None        # holds the element we are going to skip for
    _skipedtags = []        # if we find one of the elements above, we
                            # start skipping the following tags, until
                            # the corresponding endtag is found; if we
                            # do not find the endtag, we are going to
                            # start analyzing the elements in _skipedtags
    granstats = dict()

    for tag in _interestingtags:
        granstats[tag] = 0

    for (_, ftagsl) in fcodetags:
        _curskiptag = None
        _skipedtags = []
        for (tag, _, sourceline) in ftagsl:
            if _curskiptag == None and tag in _interestingtags:
                _curskiptag = tag
                continue
            if _curskiptag != None and tag == _curskiptag:
                granstats[tag] = granstats[tag] + 1
                _curskiptag = None
                _skipedtags = []
                continue
            if _curskiptag != None:
                _skipedtags.append((tag, sourceline))
                continue
#        if _skipedtags != []:
#            print("ERROR: ", _skipedtags)
    return granstats


def _checkForEquivalentSig(l, sig):
    """This method takes a list of signatures and checks sig for an
    equivalent signature. If no equivalent signature is found this
    method raises an error."""

    def _checkSigEquivalence(sig1, sig2):
        """This function checks the equivalence of two signatures.
        It uses an xmlrpc-call on troi.fim.uni-passau.de."""
        global __errorfexp
        global __errormatch
        if not (sig1 and sig2):            # ommit empty signatures
            return False

        # TODO csp:
        # if options.str:
        return sig1 == sig2

    # _checkForEquivalentSig
    for it in l:
        if _checkSigEquivalence(it, sig):
            return it
    raise NoEquivalentSigError()


def prettyPrintSet(s):
    h = s.pop()
    r = str(h)

    for e in s: r += ','+str(e)
    return r


def resetModule() :
    global __macrofuncs, __defset, __defsetf
    __macrofuncs = {}       # functional macros like: "GLIBVERSION(2,3,4)",
                            # used as "GLIBVERSION(x,y,z) 100*x+10*y+z"
    __defset = set()        # macro-objects
    __defsetf = dict()      # macro-objects per file


def apply(folder):
    """This function applies the analysis to all xml-files in that
    directory and take the results and joins them together. Results
    are getting written into the fdcsv-file."""
    # overall status variables
    resetModule()

    sigmap = {}                # {<converted sig>: [<equivalent sigs>]}
    afeatures = {}            # identified features; {<sig>: ([flag], depth, [code])}

    def _mergeFeatures(ffeatures):
        """This function merges the, with the parameter given
        dictionary (ffeatures) to the afeatures (overall-features)."""
        for (sig, (depth, code)) in ffeatures.iteritems():
            (mal, psig) = _parseFeatureSignature(sig)

            try:
                sigmatch = _checkForEquivalentSig(sigmap.keys(), psig)
                (tmpflag, tmpdepth, tmpcode) = \
                    afeatures[sigmap[sigmatch][0]]
                tmpdepth = min(tmpdepth, depth)
                tmpcode += code
                afeatures[sigmap[sigmatch][0]] = \
                    (tmpflag, tmpdepth, tmpcode)
                sigmap[sigmatch].append(sig)
            except NoEquivalentSigError:
                # mergedfeatures get the depth of minus one
                # so this way need to make less amount of changes here
                afeatures[sig] = (mal, depth, list(code))
                sigmap[psig] = [sig]

    # outputfile
    # fd, fdcsv = _prologCSV(folder)

    global __curfile
    fcount = 0
    files = returnFileNames(folder, ['.xml'])
    fstats = [None]*len(__statsorder)
    ftotal = len(files)

    # get statistics for all files; write results into csv
    # and merge the features
    for file in files:
        __curfile = file
        fcount += 1
        try:
            tree = etree.parse(file)
        except etree.XMLSyntaxError:
            print("ERROR: cannot parse (%s). Skipping this file." %
                os.path.join(folder, file))
            continue

        print('INFO: parsing file (%5d) of (%5d) -- (%s).' %
            (fcount, ftotal, os.path.join(folder, file)))

        root = tree.getroot()
        try:
            (features, _, featuresgrouter) = _getFeatures(root)
        except IfdefEndifMismatchError:
            print("ERROR: ifdef-endif mismatch in file (%s)" %
                (os.path.join(folder, file)))
            continue
        _mergeFeatures(features)

    # filter annotations that do not have any c-code
    # filter annotations with less than 2 features
    afeatureitems = filter(lambda (a, (f, d, c)):
            c != [''], afeatures.items())
    annotations = map(lambda (a, (f, b, c)): (a, f), afeatureitems)
    annotations2andmore = filter(lambda (a, f): len(f) > 1, annotations)
    annotationmap = dict()
    for (a, f) in annotations2andmore: annotationmap[a] = f

    annotations2andmore = map(lambda s: set(s), annotationmap.values())

    projectpath = os.path.dirname(folder)
    fd = open(
        os.path.join(
            projectpath,
            __outputfile
        )
        , 'w')

    featurenames = reduce(set.union, annotations2andmore, set([]))
    for i in featurenames:
        fd.write(i + '\n')
    for (a,f) in annotationmap.iteritems():
        fd.write(prettyPrintSet(f)+';'+a+'\n')
    fd.close()


# ##################################################
# add command line options

def addCommandLineOptionsMain(optionparser):
    ''' add command line options for a direct call of this script'''
    optionparser.add_argument("--folder", dest="folder",
            help="input folder [default: %(default)s]", default=".")


def addCommandLineOptions(optionparser) :
    # TODO implement CSP solving?
    # optionparser.add_argument("--csp", dest="csp", action="store_true",
    #         default=False, help="make use of csp solver to check " \
    #         "feature expression equality  [default: %(default)s]")
    # optionparser.add_argument("--str", dest="str", action="store_true",
    #         default=True, help="make use of simple string comparision " \
    #         "for checking feature expression equality  [default: %(default)s]")
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

    # ####
    # main

    folder = os.path.abspath(options.folder)
    if (os.path.isdir(folder)):
        apply(folder)
    else:
        sys.exit(-1)

