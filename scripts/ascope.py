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


# modules from the std-library
import os
import re
import sys
from optparse import OptionParser

# external libs
# python-lxml module
try:
	from lxml import etree
except ImportError:
	print("python-lxml module not found! (python-lxml)")
	print("see http://codespeak.net/lxml/")
	print("programm terminating ...!")
	sys.exit(-1)


def returnFileNames(folder, extfilt = ['.xml']):
	'''This function returns all files of the input folder <folder>
	and its subfolders.'''
	filesfound = list()

	if os.path.isdir(folder):
		wqueue = [os.path.abspath(folder)]

		while wqueue:
			currentfolder = wqueue[0]
			wqueue = wqueue[1:]
			foldercontent = os.listdir(currentfolder)
			tmpfiles = filter(lambda n: os.path.isfile(
					os.path.join(currentfolder, n)), foldercontent)
			tmpfiles = filter(lambda n: os.path.splitext(n)[1] in extfilt,
					tmpfiles)
			tmpfiles = map(lambda n: os.path.join(currentfolder, n),
					tmpfiles)
			filesfound += tmpfiles
			tmpfolders = filter(lambda n: os.path.isdir(
					os.path.join(currentfolder, n)), foldercontent)
			tmpfolders = map(lambda n: os.path.join(currentfolder, n),
					tmpfolders)
			wqueue += tmpfolders

	return filesfound


class Ascope:
	##################################################
	# constants:
	__cppnscpp = 'http://www.srcML.org/srcML/cpp'
	__cppnsdef = 'http://www.srcML.org/srcML/src'
	__cpprens = re.compile('{(.+)}(.+)')
	__conditionals = ['if', 'ifdef', 'ifndef', 'else', 'elif', 'endif']
	__conditions   = ['if', 'ifdef', 'ifndef']
	__screensize = 50
	__depthannotation = 60
	##################################################

	def __init__(self):
		oparser = OptionParser()
		oparser.add_option('-d', '--dir', dest='dir',
				help='input directory (mandatory)')
		(self.opts, self.args) = oparser.parse_args()

		if not self.opts.dir:
			oparser.print_help()
			sys.exit(-1)

		self.loc=0
		self.checkFiles()

	def __getIfdefAnnotations__(self, root):
		'''This method returns all nodes of the xml which are ifdef
		annotations in the source code.'''
		treeifdefs = list()

		for _, elem in etree.iterwalk(root):
			ns, tag = Ascope.__cpprens.match(elem.tag).\
					groups()

			if ns == Ascope.__cppnscpp \
					and tag in Ascope.__conditionals:
				treeifdefs.append(elem)

		return treeifdefs

	def __createListFromTreeifdefs__(self, treeifdefs):
	  '''This method returns a list representation for the input treeifdefs
		(xml-objects). Corresponding #ifdef elements are in one sublist.'''
	  try:
		if not treeifdefs: return []

		listifdefs = list()
		workerlist = list()
		for nifdef in treeifdefs:
			tag = nifdef.tag.split('}')[1]
			if tag in ['if', 'ifdef', 'ifndef']:
				workerlist.append(list())
				workerlist[-1].append(nifdef)
			elif tag in ['elif', 'else']:
				workerlist[-1].append(nifdef)
			elif tag in ['endif']:
				workerlist[-1].append(nifdef)
				listifdefs.append(workerlist[-1])
				workerlist = workerlist[:-1]
			else:
				print('ERROR: tag (%s) unknown!' % tag)

		return listifdefs
  	  except IndexError:
		  return []

	def __getParentTag__(self, tag):
		parent = tag.getparent()
		return parent.tag.split('}')[1]


	def __checkDiscipline__(self, treeifdefs, loc, stats, statsU):
		listundisciplined = self.__createListFromTreeifdefs__(treeifdefs)
		# print('INFO: %s annotations to check' % len(listundisciplined))

		allannotations=[]
		for ifdef in listundisciplined:
			for i in range(len(ifdef)-1):
				allannotations.append([ifdef[i].sourceline,ifdef[i+1].sourceline,self.__findFeatures__(ifdef,i)]);

		for screen in range(0, max(1,min(65000,loc-Ascope.__screensize/2)), Ascope.__screensize/2):
			screenend=min(loc, screen+Ascope.__screensize)
			annotationsOnScreen=set()
			annotationsOnScreenCount=0
			for annotation in allannotations:
				  if annotation[0]<=screenend:
				  	 if annotation[1]>screen:
				  		annotationsOnScreen.add(annotation[2])
				  		annotationsOnScreenCount=annotationsOnScreenCount+1
			try:
				stats[annotationsOnScreenCount]=stats[annotationsOnScreenCount]+1
				statsU[len(annotationsOnScreen)]=statsU[len(annotationsOnScreen)]+1
			except IndexError:
				print(annotationsOnScreenCount)
				sys.exit(-1)

		# print(stats)
		# print(statsU)

	def __findFeatures__(self, ifdef, idx):
		result=""
		if ifdef[idx].tag.split('}')[1]=='else':
			idx=0
	                result="!"
		if ifdef[idx].tag.split('}')[1]=='ifndef':
			if (result=="!"):
		        	result=""
			else:
                		result="!"

		context = etree.iterwalk(ifdef[idx])
		for action, elem in context:
			if action=="end":
				if elem.tag.split('}')[1]=="name":
					result=result+elem.text
	        # print result;
		return result

	def checkFile(self, file, stats, statsU):
		# print('INFO: processing (%s)' % file)

		try:
			tree = etree.parse(file)

			f = open(file, 'r')
		except etree.XMLSyntaxError:
			print('ERROR: file (%s) is not valid. Skipping it.' % file)
			return

		#get LOC
		thisloc=len(f.readlines())-2
		if (thisloc > 65000):
			print('INFO: file (%s) not fully processed!' % file)

		# get root of the xml and iterate over it
		root = tree.getroot()
		treeifdefs = self.__getIfdefAnnotations__(root)
		self.__checkDiscipline__(treeifdefs, thisloc, stats, statsU)


	def checkFiles(self):
		xmlfiles = returnFileNames(self.opts.dir, ['.xml'])
		stats=[0]*Ascope.__depthannotation
		statsU=[0]*Ascope.__depthannotation
		for xmlfile in  xmlfiles:
			self.checkFile(xmlfile, stats, statsU)
		f = open("count.csv","a")
		f.write(self.opts.dir+";"+str(Ascope.__screensize)+";")
		for i in stats:
		      f.write(str(i)+";")
		for i in statsU:
		      f.write(str(i)+";")
		f.write("\n")


##################################################
if __name__ == '__main__':
	Ascope()
