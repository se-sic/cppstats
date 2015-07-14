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
# This program is distribin the hope that it will be useful,
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

# this script is made for changing macros that span over
# multiple lines (examples see below) to one line for
# better parsing
# e.g.:
# #define FillGroup1            \
#    "mov  r11,r2         \n\t" \
#    "mov  r10,r2         \n\t" \ ...
#
# effects all kind of macros #defines, conditionals, ...

import os, sys

# translates macros (s.o. or usage)
def translate(infile, outfile):
	fdin    = open(infile)
	fdout   = open(outfile, 'w')
	curline = ''
	numlines = 0

	for line in fdin:
		sline = line.strip()

		# macro found
		if len(curline):
			# multi-line macro
			if sline.endswith('\\'):
				curline += sline[:-1]
				numlines += 1
			else:
				curline += sline
                #TODO fix line endings
				fdout.write(curline+'\n')
				fdout.write('\n' * numlines)
				curline = ''
				numlines = 0

			continue

		# found a new macro
		if (sline.startswith('#') and sline.endswith('\\')):
			curline += sline[:-1]
			numlines += 1
			continue

		# normal line
		fdout.write(line)

	# closeup
	fdin.close()
	fdout.close()


# usage
def usage():
	print('usage: ' + sys.argv[0] + ' <infile> <outfile>')
	print('')
	print('Translates multiple macros in the source-code of the infile')
	print('to a oneliner-macro in the outfile.')

##################################################
if __name__ == '__main__':

	if (len(sys.argv) < 3):
		usage()
		sys.exit(-1)

	infile = os.path.abspath(sys.argv[1])
	outfile = os.path.abspath(sys.argv[2])

	translate(infile, outfile)

