#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
