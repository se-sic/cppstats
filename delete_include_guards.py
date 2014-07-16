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
# - the include guard doesn't have to start at the first line
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


def apply(fname, out=sys.stdout):
    fname = os.path.abspath(fname)

    # check for include-guard
    rg = re.compile('#if\s+!defined\((\S+)\)')
    rd = re.compile('#define\s+(\S+)')
    sourcecode = list()

    fd = open(fname, 'rU')

    first_line = fd.readline()  # read first line to determine line separator
    eol = fd.newlines
    fd.seek(0)

    sourcecode = map(str.strip, fd.readlines())
    # for line in fd:
    #     l = line.strip()
    #     if l:
    #         sourcecode.append(l)

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

        # processing ifdefs
        for item in sourcecode:
            currentitem += 1
            if item.startswith('#if'):
                # checks if the ifdef line is start of an include guard
                # breaks if an include guard is found
                # skips all other ifdefs (including also never-include-guards)

                ifdef = item
                ifdefpos = currentitem

                # processing ifdef
                ifdefexpr = rg.match(ifdef)
                if (ifdefexpr):
                    # potential include-guard matched
                    guardname = ifdefexpr.groups()[0]
                else:
                    # not an include-guard ifdef
                    continue

                # processing define line following the ifdef
                taillist = list(sourcecode[currentitem:])
                define = taillist[1]
                ifdefexpr = rd.match(define)
                if (ifdefexpr):
                    if guardname == ifdefexpr.groups()[0]:
                        # include guard found
                        break
                else:
                    # ifdef is part of never-include-guard or normal ifdef->ignore
                    continue

            if currentitem == len(sourcecode):
                # no include guard found
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
        # sourcecode = before include guard + within include guard (without guard and define (but empty lines instead)) + after include guard
        emptyItemsList = [i for i in ("","","")]
        sourcecode = sourcecode[:ifdef] \
                     + emptyItemsList[0:2] \
                     + sourcecode[ifdef + 2:endif] \
                     + emptyItemsList[:2] \
                     + sourcecode[endif + 1:]

    for item in sourcecode:
        out.write(item + eol)


def usage():
    print(sys.argv[0] + ' filename')
    print('programm writes results to stdout')


##################################################
if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
    else:
        apply(sys.argv[1])
