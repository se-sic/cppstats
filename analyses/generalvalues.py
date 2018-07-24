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
from collections import OrderedDict


# #################################################
# path adjustments, so that all imports can be done relative to these paths

__lib_subfolder = "lib"
sys.path.append(os.path.abspath(__lib_subfolder))  # lib subfolder


# #################################################
# external modules

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
__outputfile = "cppstats.csv"
__metricvaluesfile = "metric_values.csv"

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
__conditionals_ending = __conditionals_elif + __conditionals_else + \
                        __conditionals_endif
__macro_define = ['define']
__macrofuncs = {}       # functional macros like: "GLIBVERSION(2,3,4)",
                        # used as "GLIBVERSION(x,y,z) 100*x+10*y+z"
__curfile = ''          # current processed xml-file
__defset = set()        # macro-objects
__defsetf = dict()      # macro-objects per file

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


def _prologCSV(folder, file, headings, delimiter = ","):
    """prolog of the CSV-output file
    no corresponding _epilogCSV."""
    fd = open(os.path.join(folder, file), 'w')
    fdcsv = csv.writer(fd, delimiter=delimiter)
    fdcsv.writerow(["sep=" + delimiter])
    fdcsv.writerow(headings)
    return (fd, fdcsv)


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
        pypa.Word(pypa.nums+'-').setParseAction(lambda t: str(int(t[0]))) + \
        pypa.Optional(pypa.Suppress(pypa.Literal('U'))) + \
        pypa.Optional(pypa.Suppress(pypa.Literal('L'))) + \
        pypa.Optional(pypa.Suppress(pypa.Literal('L')))

__identifier = \
        pypa.Word(pypa.alphanums+'_'+'-'+'@'+'$').setParseAction(_collectDefines)
__arg = pypa.Word(pypa.alphanums+'_')
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
        'defined' : '',
        '!' : '&not',
        '&&': '&and',
        '||': '&or',
        '<' : '<',
        '>' : '>',
        '<=': '<=',
        '>=': '>=',
        '==': '=',
        '!=': '!=',
        '*' : '*',       # needs rewriting with parenthesis
        '/' : '/',
        '%' : '',        # needs rewriting a % b => modp(a, b)
        '+' : '+',
        '-' : '-',
        '&' : '',        # needs rewriting a & b => BitAnd(a, b)
        '|' : '',        # needs rewriting a | b => BitOr(a, b)
        '>>': '>>',      # needs rewriting a >> b => a / (2^b)
        '<<': '<<',      # needs rewriting a << b => a * (2^b)
    }

    def _rewriteOne(param):
        """This function returns each one parameter function
        representation for maple."""
        if param[0][0] == '!':
            ret = __pt[param[0][0]] + '(' + str(param[0][1]) + ')'
        if param[0][0] == 'defined':
            ret = __pt[param[0][0]] + str(param[0][1])
        return  ret


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
    except ValueError, e:
        print('ERROR (parse): cannot parse sig (%s) ~~ (%s)' %
                (sig, e))
        return sig
    return ''.join(rsig)


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


_elsePrefix = "###"
def _getFeatureSignature(condinhist, options):
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
            if (options.rewriteifdefs):
                fname = '!(' + fname + ')'
            else:
                fname = _elsePrefix + '!(' + fname + ')'

        if fsig == '':
            fsig = fname
            continue
        if tag == 'else':
            continue
        if tag in [ 'if', 'elif']:
            if (options.rewriteifdefs):
                fsig = '(' + fsig + ') && (' + fname + ')'
            else:
                fsig = fname
            continue
    return fsig


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


def _getFeatures(root, options):
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
        itouter = fouter[-1]                # feature surround tags
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
        itcode = fcode[-1]                # feature code
        itcode = itcode.replace('\n\n', '\n')
        itcode = itcode[1:]                # itcode starts with '\n'; del
        fcode = fcode[:-1]
        itinner = finner[-1]                # feature enclosed tags
        finner = finner[:-1]

        # handle the feature code
        if (features.has_key(itsig)):
            features[itsig][1].append(itcode)
        else:
            features[itsig] = (len(flist)+1, [itcode])

        # handle the inner granularity
        featuresgrinner.append((itsig, itinner))
        return (features, featuresgrinner, fcode, flist, finner)

    from collections import OrderedDict
    features = OrderedDict({}) # see above; return value
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
    elses = []
    ifdef_number = 0

    # iterate over all tags separately <start>- and <end>-tag
    for event, elem in etree.iterwalk(root, events=("start", "end")):
        ns, tag = __cpprens.match(elem.tag).groups()

        # handling conditionals
        # hitting on conditional-macro
        if ((tag in __conditionals_all)
                and (event == 'start')
                and (ns == __cppnscpp)):    # check the cpp:namespace
            parcon = True

        # hitting on conditional-macro else or elif
        if (((tag in __conditionals_else) or (tag in __conditionals_elif))
                and (event == 'start')
                and (ns == __cppnscpp)):    # check the cpp:namespace
            ifdef_number += 1


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

            fsig = _getFeatureSignature(condinhist, options)
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
                if condinhist[-1][0] == 'else':
                    elses.append(ifdef_number)
                condinhist = condinhist[:-1]

            condinhist = condinhist[:-1]
            ifdef_number += 1

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
    return (features, featuresgrinner, featuresgrouter, elses)


__nestedIfdefsLevels = []
__nestingDepthsOfBranches = []
def _getNestingDepths(root):
    """This function counts the number of nested ifdefs (conditionals)
    within the source-file in two different ways.
     1) the nesting depth of each #ifdef block (nested or not nested, one value for #if/#elif/#else branches)
        __nestedIfdefsLevels = [int]
     2) the nesting depth of each top-level (non-nested) branch (#if/#elif/#else) separately
        __nestingDepthsOfBranches = [(file path, xml element, feature signature, maximum nesting of this element)]
    """

    global __curfile, __nestedIfdefsLevels, __nestingDepthsOfBranches

    elements = [it for it in root.iterdescendants()]

    cncur = 0
    cnmax = -1
    sigblockhist = []

    # [] of integers
    cnlist = []
    # [(file path, xml element, feature signature, maximum nesting of this element)]
    sighist = []

    for elem in elements:
        ns, tag = __cpprens.match(elem.tag).groups()

        # if a branch ends somehow
        if ((tag in __conditionals_ending)
            and (ns == __cppnscpp)):

            # reduce nesting level
            cncur -= 1

            # if we are back at top-level
            if cncur == 0:

                # insert max-nesting value to top-level element
                (xfile, xelem, xsig, xdepth) = sigblockhist[-1]
                sigblockhist[-1] = (xfile, xelem, xsig, cnmax)

                # reset value, since branch is finished
                cnmax = -1

                # if an #endif is reached, a whole block of #if/#elif/#else is finished
                if tag in __conditionals_endif:
                    sighist += sigblockhist
                    sigblockhist = []

        # if hitting the next conditional
        if ((tag in __conditionals_all)
            and (ns == __cppnscpp)):

            # increase nesting level
            cncur += 1

            # gather the nesting depth of each #ifdef block (incl. #else/#elif branches)
            if (tag in __conditionals):
                cnlist.append(cncur)

            # add top-level signatures to history
            if cncur == 1:

                # if #else is reached, its empty signature must be rewritten as
                # negation of previous signatures within this #ifdef block
                if tag in __conditionals_else:
                    #FIXME how to do this if rewriting is enabled?!

                    newsig = ['!(' + xsig + ')' for (_, _, xsig, _) in sigblockhist]
                    sigblockhist.append((__curfile, elem, " && ".join(newsig), -1))

                else:

                    sigblockhist.append((__curfile, elem, _getMacroSignature(elem), -1))

            # calculate current max of this branch
            cnmax = max(cnmax, cncur)

            # # DEBUG
            # print "%s %s: %s (max: %s)" % (tag, _getMacroSignature(elem), cncur, cnmax)

    if (len(cnlist) > 0):
        nnitmp = filter(lambda n: n > 0, cnlist)
        __nestedIfdefsLevels += nnitmp

    __nestingDepthsOfBranches += sighist


def _getScatteringTanglingValues(sigs, defines):
    """This method returns the scattering and tangling VALUES of
    defines according to the given mapping of a define to occurances
    in the signatures. The input is all feature-signatures and
    all defines."""
    #TODO insert tuples into description!

    def __add(x, y):
        """This method is a helper function to add values
        of lists pairwise. See below for more information."""
        return x+y

    scat = list()            # relation define to signatures
    tang = [0]*len(sigs)    # signatures overall
    for d in defines:
        dre = re.compile(r'\b'+d+r'\b')        # using word boundaries
        vec = map(lambda s: not dre.search(s) is None, sigs)
        scat.append(vec.count(True))
        tang = map(__add, tang, vec)

    # create dictionaries from sigs and defines and corresponding
    # scattering and tangling values
    scatdict = zip(defines, scat)
    tangdict = zip(sigs, tang)

    return (scatdict, tangdict)


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

        # if options.str:
        return sig1 == sig2

    # _checkForEquivalentSig
    for it in l:
        if _checkSigEquivalence(it, sig):
            return it
    raise NoEquivalentSigError()


def resetModule() :
    global __macrofuncs, __defset, __defsetf, __nestedIfdefsLevels, __nestingDepthsOfBranches
    __macrofuncs = {}       # functional macros like: "GLIBVERSION(2,3,4)",
                            # used as "GLIBVERSION(x,y,z) 100*x+10*y+z"
    __defset = set()        # macro-objects
    __defsetf = dict()      # macro-objects per file
    __nestedIfdefsLevels = []
    __nestingDepthsOfBranches = []


def apply(folder, options):

    """This function applies the analysis to all xml-files in that
    directory and take the results and joins them together. Results
    are getting written into the fdcsv-file."""
    # overall status variables
    resetModule()

    sigmap = {}                # {<converted sig>: [<equivalent sigs>]}
    afeatures = {}            # identified features; {<sig>: (depth, [code])}

    def _mergeFeatures(ffeatures):
        """This function merges the, with the parameter given
        dictionary (ffeatures) to the afeatures (overall-features)."""
        for (sig, (depth, code)) in ffeatures.iteritems():
            psig = _parseFeatureSignatureAndRewrite(sig)

            try:
                sigmatch = _checkForEquivalentSig(sigmap.keys(), psig)
                (tmpdepth, tmpcode) = afeatures[sigmap[sigmatch][0]]
#                if (tmpdepth != depth):
#                    print("INFO: depths of feature fragments do not" +
#                            " match (%s, %s)!" % (str(tmpdepth), str(depth)))
                tmpdepth = min(tmpdepth, depth)
                tmpcode += code
                afeatures[sigmap[sigmatch][0]] = (tmpdepth, tmpcode)
                sigmap[sigmatch].append(sig)
            except NoEquivalentSigError:
                # mergedfeatures get the depth of minus one
                # so this way need to make less amount of changes here
                afeatures[sig] = (depth, list(code))
                sigmap[psig] = [sig]


    global __curfile
    fcount = 0
    files = returnFileNames(folder, ['.xml'])
    files.sort()
    ftotal = len(files)

    # get statistics for all files
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
            (features, _, featuresgrouter, elses) = _getFeatures(root, options)
        except IfdefEndifMismatchError:
            print("ERROR: ifdef-endif mismatch in file (%s)" % (os.path.join(folder, file)))
            continue

        # remove #else branches from list of features as there is no existing signature in the source code!
        if not options.rewriteifdefs:
            features = OrderedDict((sig, value)
                                   for sig, value in features.iteritems()
                                   if not sig.startswith(_elsePrefix))

        # merge features of file in the global list of features
        _mergeFeatures(features)

        # calculate nesting depths (per block and per branch)
        _getNestingDepths(root)

        # file successfully parsed
        fcount += 1
        print('INFO: parsing file (%5d) of (%5d) -- (%s).' % (fcount, ftotal, os.path.join(folder, file)))

    # get signatures and defines
    sigs = _flatten(sigmap.values())
    defs = list(__defset)

    # preparation: opn file for writing
    stfheadings = ['name', 'values']
    stfrow = [None]*len(stfheadings)
    stfhandle, stfwriter = _prologCSV(os.path.join(folder, os.pardir), __metricvaluesfile, stfheadings)

    # scattering and tangling values
    # each signature is used once per file

    (scatvalues, tangvalues) = _getScatteringTanglingValues(sigs, defs)
    scats = sorted([x[1] for x in scatvalues])
    tangs = sorted([x[1] for x in tangvalues])

    stfrow[0] = "tangling"
    tanglingstring = ';'.join(map(str, tangs))
    stfrow[1] = tanglingstring
    stfwriter.writerow(stfrow)

    stfrow[0] = "scattering"
    scatteringstring = ';'.join(map(str, scats))
    stfrow[1] = scatteringstring
    stfwriter.writerow(stfrow)

    # nesting values

    stfrow[0] = "nestedIfdefsLevels"
    ndstring = ';'.join(map(str, __nestedIfdefsLevels))
    stfrow[1] = ndstring
    stfwriter.writerow(stfrow)

    stfhandle.close()

    # MERGED VALUES

    # scattering + tangling (merged)
    # each signature is used only once per project (string equality)
    (scatvalues_merged, tangvalues_merged) = _getScatteringTanglingValues(list(set(sigs)), defs)

    sd, sdcsv = _prologCSV(os.path.join(folder, os.pardir), "merged_scattering_degrees.csv", ["define","SD"], delimiter=",")
    for (define, scat) in scatvalues_merged:
        sdcsv.writerow([define,scat])
    sd.close()

    td, tdcsv = _prologCSV(os.path.join(folder, os.pardir), "merged_tangling_degrees.csv", ["signature","TD"], delimiter=",")
    for (sig, tang) in tangvalues_merged:
        tdcsv.writerow([sig,tang])
    td.close()

    nd, ndcsv = _prologCSV(os.path.join(folder, os.pardir), "nesting_degrees_toplevel_branches.csv", ["file", "signature", "ND"], delimiter=",") # , "linenumber"
    for (file, elem, sig, depth) in __nestingDepthsOfBranches:

        #adjust file name if wanted
        if options.filenamesRelative : # relative file name (root is project folder (not included in path))
            file = os.path.relpath(file, folder)

        if options.filenames == options.FILENAME_SRCML : # cppstats file names
            pass # nothing to do here, as the file path is the cppstats path by default
        if options.filenames == options.FILENAME_SOURCE : # source file name
            file = file.replace(".xml", "").replace("/_cppstats/", "/source/", 1)

        # print information to file
        ndcsv.writerow([file, sig, depth]) # , elem.sourceline - 1
    nd.close()


# ##################################################
# add command line options

def addCommandLineOptionsMain(optionparser):
    ''' add command line options for a direct call of this script'''
    optionparser.add_argument("--folder", dest="folder",
        help="input folder [default=%(default)s]", default=".")


def addCommandLineOptions(optionparser) :
    # TODO implement CSP solving?
    # optionparser.add_option("--csp", dest="csp", action="store_true",
    # default=False, help="make use of csp solver to check " \
    # "feature expression equality [default=False]")
    # optionparser.add_option("--str", dest="str", action="store_true",
    #     default=True, help="make use of simple string comparision " \
    #     "for checking feature expression equality [default=True]")
    optionparser.add_argument("--norewriteifdefs", dest="rewriteifdefs",
                              action="store_false", default=True,
                              help="rewrite nested #ifdefs and #elifs as a conjunction of "
                                   "inner and outer expressions [default=%(default)s]\n"
                                   "(exception are #else tags, which ARE rewritten as "
                                   "negation of the #if branch! see also --norewriteelse "
                                   "of analysis GENERALVALUES)")
    #FIXME add command line function to remove #else too!


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
        apply(folder, options)
    else:
        sys.exit(-1)
