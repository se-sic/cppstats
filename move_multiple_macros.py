#!/usr/bin/python
# -*- coding: utf-8 -*-

# this script is made for changing macros that span over
# multiple lines (examples see below) to one line for
# better parsing
# e.g.:
# #define FillGroup1            \
#    "mov  r11,r2         \n\t" \
#    "mov  r10,r2         \n\t" \ ...
#
# effects all kind of macros #defines, conditionals, ...

__author__  = "Jörg Liebig"
__date__    = "$Date:$"
__version__ = "$Rev:$"

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

