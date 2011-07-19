#!/usr/bin/python
# -*- coding: utf-8 -*-

# this script checks include guards of c, cpp - header files
# and removes them:
# e.g.: test.h
# #if !defined(foo)
# #define foo ...
# #endif // foo
#
# parser works with following characteristics:
#  - the include guard doesn't have to start at the first line
#    and doesn't have to finish at the last line
#  - only one guard per file
#  - deleting first include-guard of following syntax
#  - include is formated like:
#     line x  : #if !defined(foo)
#     line x+1: #define foo
#     line x+2:  ...
#     line x+y: #endif

import os, re, sys

__debug = False

def apply(fname):
    fname = os.path.abspath(fname)

    # check for include-guard
    rg = re.compile('#if\s+!defined\((\S+)\)')
    rd = re.compile('#define\s+(\S+)')
    sourcecode = list()

    with open(fname, 'r') as fd:
        for line in fd.readlines():
            sourcecode.append(line.strip())

    def _findCorrespondingItems(sourcecode):
        '''This method returns a tuple with the include guard elements to cut of the source.
        return of (-1, -1), means no proper include guard found.
        the following rules apply:
        - include guard has to be the first one of the occuring #ifdefs
        - no alternatives, i.e. occuring #else or #elif, allowed
        '''
        ifdefpos = -1
        ifdef = ''
        currentitem = -1
        guardname = ''
        taillist = list()

        # processing ifdef
        for item in sourcecode:
            currentitem += 1
            if item.startswith('#if'):
                ifdef = item
                ifdefpos = currentitem
                taillist = list(sourcecode[currentitem:])
                break
            if currentitem == len(sourcecode):
                return (-1, -1)

        # processing ifdef and define
        regres = rg.match(ifdef)
        if (regres):
            guardname = regres.groups()[0]
        else:
            return (-1, -1)

        define = taillist[1]
        regres = rd.match(define)
        if (regres):
            if guardname != regres.groups()[0]:
                return (-1, -1)
        else:
            return (-1, -1)

        # process taillist for else and endif
        ifcount = 1
        currentitem = 1 # go two steps ahead as we jump over #if and #define
        for item in taillist[2:]:
            currentitem += 1
            if item.startswith('#else') and ifcount == 1:
                return (-1, -1)        # we do not support alternative include guards
            if item.startswith('#elif') and ifcount == 1:
                return (-1, -1)        # we do not support alternative include guards
            if item.startswith('#if'):
                ifcount += 1
                continue
            if item.startswith('#endif'):
                ifcount -= 1
                if ifcount == 0:
                    return(ifdefpos, currentitem+ifdefpos)
                continue
        return (-1, -1)

    (ifdef, endif) = _findCorrespondingItems(list(sourcecode))
    if (ifdef == -1 or endif == -1):
        pass
    else:
        sourcecode = sourcecode[:max(0, ifdef-1)]+sourcecode[ifdef+2:endif]+sourcecode[endif+1:]

    for item in sourcecode:
        print(item)



def usage():
    print(sys.argv[0] + ' filename')
    print('programm writes results to stdout')


##################################################
if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
    else:
        apply(sys.argv[1])
