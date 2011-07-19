#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys

class WrongIfdefError(Exception):
	def __init__(self):
		pass
	def __str__(self):
		return ("Didn't find \"ifdef\" or \"ifndef\" as macro")

def rewriteFile(fname):
	fd = open(fname, 'r')

	for line in fd:
		if line.startswith('#ifdef') or line.startswith('#ifndef'):
			ifdef, identifier = line.split(None, 1)
			identifier = identifier.strip()

			if ifdef == '#ifdef':
				print('#if defined(' + identifier + ')')
				continue
			if ifdef == '#ifndef':
				print('#if !defined(' + identifier + ')')
				continue
			raise WrongIfdefError()
		else:
			print(line.strip())

	fd.close()


##################################################
if __name__ == '__main__':
	if (len(sys.argv) != 2):
		print("usage: " + sys.argv[0] + " <filename>")
	else:
		rewriteFile(sys.argv[1])
