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


# this script checks include guards of c, cpp - header files
# and removes them:
# e.g.: test.h
# #if !defined(foo)
# #define foo ...
# #endif // foo
#
# parser works with following characteristics:
# - the include guard doesn't have to start at the first line
# and doesn't have to finish at the last line
#  - only one guard per file
#  - deleting first include-guard of following syntax
#  - include is formated like:
#     line x  : #if !defined(foo)
#     line x+1: #define foo
#     line x+2:  ...
#     line x+y: #endif

import os, re, sys

__debug = False


def apply(fname, out=sys.stdout):
    fname = os.path.abspath(fname)

    # check for include-guard
    rg = re.compile('#if\s+!defined\((\S+)\)')
    rd = re.compile('#define\s+(\S+)')
    sourcecode = list()

    with open(fname, 'r') as fd:
        for line in fd.readlines():
            sourcecode.append(line)

    def _findCorrespondingItems(sourcecode):
        '''This method returns a tuple with the include guard elements to cut of the source.
        return of (-1, -1), means no proper include guard found.
        the following rules apply:
        - include guard has to be the first one of the occuring #ifdefs
        - no alternatives, i.e. occuring #else or #elif, allowed
        '''
        ifdefpos = -1
        ifdef = ''
        sifdef = '' # stripped #if
        currentitem = -1
        guardname = ''
        taillist = list()

        # processing ifdefs
        for item in sourcecode:
            sitem = item.strip()
            currentitem += 1

            # line is empty (except for whitespace, probably)
            if not sitem:
                continue

            if sitem.startswith('#if'):
                ifdef = item
                sifdef = sitem
                ifdefpos = currentitem
                taillist = list(sourcecode[currentitem:])
                break # search for #if

            # end of code reached and nothing found so far
            if currentitem == len(sourcecode):
                # no include guard found
                return (-1, -1)

        # processing ifdef and define
        regres = rg.match(sifdef)
        if (regres):
            guardname = regres.groups()[0]
        else:
            return (-1, -1)

        define = taillist[1]
        regres = rd.match(define.strip())
        if (regres):
            if guardname != regres.groups()[0]:
                return (-1, -1)
        else:
            return (-1, -1)

        # process taillist for else and endif
        ifcount = 1
        currentitem = 1  # go two steps ahead as we jump over #if and #define
        for item in taillist[2:]:
            currentitem += 1
            if item.startswith('#else') and ifcount == 1:
                return (-1, -1)  # we do not support alternative include guards
            if item.startswith('#elif') and ifcount == 1:
                return (-1, -1)  # we do not support alternative include guards
            if item.startswith('#if'):
                ifcount += 1
                continue
            if item.startswith('#endif'):
                ifcount -= 1
                if ifcount == 0:
                    return (ifdefpos, currentitem + ifdefpos)
                continue
        return (-1, -1)

    (ifdef, endif) = _findCorrespondingItems(list(sourcecode))
    if (ifdef == -1 or endif == -1):
        pass
    else:
        # concat source code again and replace include guard with empty lines
        sourcecode = sourcecode[:max(0, ifdef)] + \
                     ["", ""] + \
                     sourcecode[ifdef + 2:endif] + \
                     [""] + \
                     sourcecode[endif + 1:]

    for item in sourcecode:
        out.write(item.rstrip('\n') + '\n')


def usage():
    print(sys.argv[0] + ' filename')
    print('programm writes results to stdout')


##################################################
if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
    else:
        apply(sys.argv[1])
