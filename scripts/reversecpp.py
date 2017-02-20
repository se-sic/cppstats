# -*- coding: utf-8 -*-
# cppstats is a suite of analyses for measuring C preprocessor-based
# variability in software product lines.
# Copyright (C) 2011 University of Passau, Germany
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


'''
this collection of functions is dedicated to discipline undisciplined
preprocessor annotations in the source code. the annotations covered are
those of conditional compilation (#if, #ifdef, #ifndef, #elif, #else, and
#endif).

basic strategy is:
1. adding line markers to the orginial source code file; these markers are
   necessary in the following steps for moving undisciplined annotations and
   merging different source code files
2. extract all configuration paramters from #ifdef expressions and generate
   all possible variants
3. create an xml representation for each of the variants
4. based on the line markers move undisciplined annotations to disciplined ones
   in each of the variants
5. merge the different variants and create a single source code file
'''

import itertools
import os
import subprocess
import sys
import tempfile
from cpplib import _collectIfdefExpressions, _parseIfDefExpression
from optparse import OptionParser

############################################################
# config
cpptool = '/usr/bin/cpp'
tmpfolder = './tmp_reversecpp/'
src2srcml = os.path.join(os.path.expanduser('~'), 'bin', 'src2srcml2009')
src2srcmloptions = ['--language', 'C']
srcml2src = os.path.join(os.path.expanduser('~'), 'bin', 'srcml2src2009')
############################################################

class Util:
    @classmethod
    def returnFileNames(folder, extfilt = ['.xml']):
        '''
        This function returns all files of the input folder <folder>
        and its subfolders.
        '''
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


class ReverseCPP:

    def __init__(self):
        oparser = OptionParser()
        oparser.add_option("--ifolder", dest="ifolder",
                           help="input folder")
        oparser.add_option("--ofolder", dest="ofolder",
                           help="output folder")
        oparser.add_option("--debug", dest="debug",
                           help="print out debug information")
        self.opts, self.args = oparser.parse_args()

    def setup(self):
        if not os.path.exists(tmpfolder):
            if self.opts.debug:
                print('INFO: tmpfolder (%s) does not exist; creating it' % tmpfolder)
            os.mkdir(tmpfolder)
        if not os.path.exists(src2srcml):
            print('ERROR: src2srcml tool is not available under path (%s)' % src2srcml)
            print('ERROR: program terminating ...!')
            sys.exit(-1)
        if not os.path.exists(srcml2src):
            print('ERROR: srcml2src tool is not available under path (%s)' % srcml2src)
            print('ERROR: program terminating ...!')
            sys.exit(-1)

    def addingLineMarkersToFile(self, infile, outfile):
        '''
        This method adds line markers (comments) to the source code file (infile) and
        writes the result to the output file (outfile). Three different markers are added:
        1. a comment containing the conditional compilation macro is added before each
           macro
        2. each line gets a comment with the lineid at the end
        3. include macros are turned into comments so that that preprocessor omits file
           inclusion during the preprocessing step
        '''
        fdin = open(os.path.abspath(infile), 'r')
        fdout = open(os.path.abspath(outfile), 'w')
        lineid = 0

        for line in fdin.xreadlines():
            # found #if{ndef|def||} or #e{ndif|lse|lif}
            if line.startswith('#if') or line.startswith('#e'):
                fdout.write('//'+ line + str(lineid))
                lineid += 1
            if line.startswith('#include'):
                fdout.write('//'+ line + str(lineid))
                lineid += 1
                continue
            fdout.write(line.strip() + '/* lineid=' + str(lineid) + ' */\n')
            lineid += 1

        print('processed file ' + os.path.abspath(infile))

    def createVariants(self, symbols, fname):
        '''
        Generate for each combination of symbols a variant for the inputfile fname
        and return the list of generated files.
        '''
        generatedfiles = []
        for configuration in itertools.product(range(2), repeat=len(symbols)):
            configuration = list(configuration)
            pairs = zip(configuration, symbols)
            validpairs = filter(lambda (m, n): m != 0, pairs)

            if len(validpairs): validdefines = list(zip(*validpairs)[1])
            else: validdefines = []

            validdefines = map(lambda n: '-D'+n, validdefines)
            cppinvocation = [cpptool]
            cppinvocation += validdefines
            cppinvocation += [fname]

            # create call-string and generate a variant
            extension = os.path.splitext(fname)[1]
            tmpfile = tempfile.NamedTemporaryFile(suffix=extension, dir=tmpfolder, delete=False)
            cppinvocation += ['-C']
            cppinvocation += [tmpfile.name]
            print(cppinvocation)
            subprocess.call(cppinvocation)
            generatedfiles.append(tmpfile.name)
        return generatedfiles

    def createXMLRepresentation(self, fname):
        '''
        This method creates an xml representation from the input file using the src2srcml
        tool (http://www.srcML.org/). After the successful generation of the
        xml representation the method returns the filename of the xml file.
        '''
        src2srcmlinvocation = [src2srcml]
        src2srcmlinvocation += src2srcmloptions
        src2srcmlinvocation += [fname] # input file
        src2srcmlinvocation += [fname+'.xml'] # output file
        print(src2srcmlinvocation)
        subprocess.call(src2srcmlinvocation)
        return fname+'.xml'

    def createXMLRepresenations(self, flist):
        '''
        This method creates an xml representation of each file in the input list (flist)
        and returns a list of the generated xml files.
        '''
        generatedlist = []
        for file in flist:
            generatedlist.append(self.createXMLRepresentation(file))
        return generatedlist


    def apply(self):
        self.setup()
        symbols, _ = _parseIfDefExpression('AA && BB')
        flist = self.createVariants(symbols, '/home/joliebig/workspace/reverse_cpp/test/test.c')
        flist = self.createXMLRepresenations(flist)
        print(flist)
        print(_collectIfdefExpressions('/home/joliebig/workspace/reverse_cpp/test/test.c'))

##################################################
if __name__ == '__main__':
    r = ReverseCPP()
    r.apply()
