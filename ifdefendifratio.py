#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This tool determines, whether the ration of conditionals (ifdef) to
# endif-macros holds. The reason for this check is basically the effect,
# when running the pxml.py against a xml-file and an error occurs because
# the lists in _getFeatures are empty.

__author__  = "Jörg Liebig"
__date__    = "$Date: 2009-02-16 15:49:58 +0100 (Mon, 16 Feb 2009) $"
__version__ = "$Rev: 539 $"

# modules from the std-library
import os, re, sys

try:
	from lxml import etree
except ImportError:
	print("python-lxml module not found! (python-lxml)")
	print("see http://codespeak.net/lxml/")
	print("programm terminating ...!")
	sys.exit(-1)


##################################################
# constants:
# namespace-constant for src2srcml
__cppnscpp = 'http://www.sdml.info/srcML/cpp'
__cppnsdef = 'http://www.sdml.info/srcML/src'
__cpprens = re.compile('{(.+)}(.+)')

__conditionals = ['if', 'ifdef', 'ifndef']
__conditionals_endif = ['endif']
##################################################

def _getIfdefEndifRatio(root):
	"""This function determines all conditionals and their corresponding
	endifs and returns a counter for each of them."""
	ifdef = 0
	endif = 0

	# get all nodes
	allnodes = [node for node in root.iterdescendants()]

	for node in allnodes:
		ns, tag = __cpprens.match(node.tag).groups()

		if ((tag in __conditionals) \
				and (ns == __cppnscpp)):
			ifdef += 1
		if ((tag in __conditionals_endif) \
				and (ns == __cppnscpp)):
			endif += 1

	return (ifdef, endif)


def apply(folder):
	"""This function applies the determination function (getIfdefEndifRation)
	to each file and prints out the differance in case there is one."""
	folder = os.path.abspath(folder)
	files = os.listdir(folder)
	files = filter(lambda n: os.path.splitext(n)[1] == ".xml", files)

	for file in files:
	
		try:
			tree = etree.parse(file)
		except etree.XMLSyntaxError:
			print("ERROR: cannot parse (%s). Skipping this file!." % file)

		root = tree.getroot()
		ifdef, endif = _getIfdefEndifRatio(root)

		if (ifdef != endif):
			print("INFO: (%30s) ifdef : endif  is  %5s : %5s" % (file, str(ifdef), str(endif)))


def usage():
	"""This function prints usage-informations to stdout."""
	print('usage:')
	print('  ' + sys.argv[0] + ' <folder>')


##################################################
if __name__ == '__main__':

	if (len(sys.argv) < 2):
		usage()
		sys.exit(-1)

	folder = sys.argv[1]
	if (os.path.isdir(folder)):
		apply(folder)
	else:
		usage()
		sys.exit(-1)
