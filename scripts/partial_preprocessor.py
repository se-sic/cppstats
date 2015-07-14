#!/usr/bin/env python
# -*- coding: utf-8 -*-
# cppstats is a suite of analyses for measuring C preprocessor-based
# variability in software product lines.
# Copyright (C) 2010-2015 University of Passau, Germany
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


#FIXME move this script to another folder!
from optparse import OptionParser
import sys

from lib.cpplib import _filterAnnotatedIfdefs


class PartialPreprocessor:
    def __init__(self):
        oparser = OptionParser()
        oparser.add_option('-i', '--inputfile', dest='ifile',
                help='input file (mandatory)')
        oparser.add_option('-o', '--outputfile', dest='ofile',
                help='output file (mandatory)')
        (self.opts, self.args) = oparser.parse_args()

        if not self.opts.ifile or not self.opts.ofile:
            oparser.print_help()
            sys.exit(-1)

        _filterAnnotatedIfdefs(self.opts.ifile, self.opts.ofile)


##################################################
if __name__ == '__main__':
    PartialPreprocessor()
