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

import sys, os

class WrongIfdefError(Exception):
	def __init__(self):
		pass
	def __str__(self):
		return ("Didn't find \"ifdef\" or \"ifndef\" as macro")

def rewriteFile(fname, out = sys.stdout):
	fd = open(fname, 'r')

	for line in fd:
		if line.startswith('#ifdef') or line.startswith('#ifndef'):
			ifdef, identifier = line.split(None, 1) # FIXME if there is a comment after the constant, it is incorporated into the brackets! this may lead to errors.
			identifier = identifier.strip()

			if ifdef == '#ifdef':
				out.write('#if defined(' + identifier + ')' + '\n')
				continue
			if ifdef == '#ifndef':
				out.write('#if !defined(' + identifier + ')' + '\n')
				continue
			raise WrongIfdefError()
		else:
			out.write(line)

	fd.close()


##################################################
if __name__ == '__main__':
	if (len(sys.argv) != 2):
		print("usage: " + sys.argv[0] + " <filename>")
	else:
		rewriteFile(sys.argv[1])
