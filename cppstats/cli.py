# -*- coding: utf-8 -*-
# cppstats is a suite of analyses for measuring C preprocessor-based
# variability in software product lines.
# Copyright (C) 2014-2015 University of Passau, Germany
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
#     Claus Hunsen <hunsen@fim.uni-passau.de>


# #################################################
# imports from the std-library

import sys
from argparse import ArgumentParser, RawTextHelpFormatter, _VersionAction  # for parameters to this script

# #################################################
# imports from subfolders

import preparation, analysis
import cppstats as cstats # import cppstats.py and avoid confusion with module


# #################################################
# external modules

# enums
from enum import Enum


# #################################################
# global constants

__inputlist_default = "cppstats_input.txt"


# #################################################
# definition of cppstats steps
class steps(Enum):
    ALL = 0
    PREPARATION = 1
    ANALYSIS = 2


# #################################################
# custom actions

class CppstatsVersionAction(_VersionAction):
    # FIXME not needed for Python 3.4+! see http://bugs.python.org/issue18920
    '''
        subclass to _VersionAction as that class prints version information
        to ``stderr``, but this subclass prints to ``stdout`` instead.

        Note: This is default in Python 3.4+.
    '''

    def __init__(self, *args, **kwargs):
        """Initialisation method for the _VersionAction class"""
        _VersionAction.__init__(self, *args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        version = self.version
        if version is None:
            version = parser.version
        formatter = parser._get_formatter()
        formatter.add_text(version)
        # parser.exit(message=formatter.format_help())

        # change output to sys.stdout and exit then without a message
        parser._print_message(message=formatter.format_help(), file=sys.stdout)
        parser.exit(status=0)


# #################################################
# construct ArgumentParser

def getOptions(kinds, step=steps.ALL):
    """
    Constructs the parser needed for cppstats. Includes following procedure:
      * addition of step-specific arguments
      * parsing
      * addition of constants
      * checking of constraints

    :arg kinds : the list of preperation/analysis kinds, dependent on the step parameter
    :arg step : the variant of cppstats to execute: one of cli.steps (ALL, PREPARATION, ANALYSIS)
    :rtype : the resulting options
    """

    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)

    # version (uses CppstatsVersionAction instead of 'version' as action)
    parser.add_argument('--version', action=CppstatsVersionAction, version=cstats.version())


    # ADD KIND ARGUMENT

    # kinds
    kindgroup = parser.add_mutually_exclusive_group(required=False)
    kindgroup.add_argument("--kind", choices=kinds.keys(), dest="kind",
                           default=kinds.keys()[0], metavar="<K>",
                           help="the preparation to be performed [default: %(default)s]")
    kindgroup.add_argument("-a", "--all", action="store_true", dest="allkinds", default=False,
                           help="perform all available kinds of preparation/analysis [default: %(default)s]")


    # ADD INPUT TYPE (list or file)

    # input 1
    inputgroup = parser.add_mutually_exclusive_group(required=False)  # TODO check if True is possible some time...
    inputgroup.add_argument("--list", type=str, dest="inputlist", metavar="LIST",
                            nargs="?", default=__inputlist_default, const=__inputlist_default,
                            help="a file that contains the list of input projects/folders [default: %(default)s]")
    # input 2
    if step == steps.ALL:
        inputgroup.add_argument("--file", type=str, dest="inputfile", nargs=2, metavar=("IN", "OUT"),
                                help="a source file IN that is prepared and analyzed, the analysis results are written to OUT"
                                     "\n(--list is the default)")
    elif step == steps.PREPARATION:
        inputgroup.add_argument("--file", type=str, dest="inputfile", nargs=2, metavar=("IN", "OUT"),
                                help="a source file IN that is prepared, the preparation result is written to OUT"
                                     "\n(--list is the default)")
    elif step == steps.ANALYSIS:
        inputgroup.add_argument("--file", type=str, dest="inputfile", nargs=2, metavar=("IN", "OUT"),
                                help="a srcML file IN that is analyzed, the analysis results are written to OUT"
                                     "\n(--list is the default)")


    # ADD VARIOUS STEP-DEPENDENT ARGUMENTS

    # no backup files
    if step == steps.ALL or step == steps.PREPARATION:
        parser.add_argument("--nobak", action="store_true", dest="nobak", default=False,
                            help="do not backup files during preparation [default: %(default)s]")

    # add general CLI options applying for all or several analyses
    if step == steps.ALL or step == steps.ANALYSIS:
        # constants for the choices of '--filenames' are added in method 'addConstants'
        parser.add_argument("--filenames", choices=[0, 1], dest="filenames", default=0,
                            help="determines the file paths to print [default: %(default)s]\n"
                                 "(0=paths to srcML files, 1=paths to source files)")
        parser.add_argument("--filenamesRelative", action="store_true", dest="filenamesRelative", default=False,
                            help="print relative file names [default: %(default)s]\n"
                                 "e.g., '/projects/apache/_cppstats/afile.c.xml' gets 'afile.c.xml'.")


    # ADD POSSIBLE PREPARATION/ANALYSIS KINDS AND THEIR COMMAND-LINE ARGUMENTS

    if step == steps.ALL:
        parser.add_argument_group("Possible Kinds of Analyses <K>".upper(), ", ".join(kinds.keys()))

        # add options for each analysis kind
        for kind in kinds.values():
            analysisPart = kind[1]
            analysisThread = analysis.getKinds().get(analysisPart)
            analysisThread.addCommandLineOptions(parser)

    elif step == steps.PREPARATION:
        parser.add_argument_group("Possible Kinds of Preparation <K>".upper(), ", ".join(kinds.keys()))

    elif step == steps.ANALYSIS:
        parser.add_argument_group("Possible Kinds of Analyses <K>".upper(), ", ".join(kinds.keys()))

        # add options for each analysis kind
        for cls in kinds.values():
            cls.addCommandLineOptions(parser)


    # PARSE OPTIONS

    options = parser.parse_args()


    # ADD CONSTANTS TO OPTIONS

    addConstants(options)


    # CHECK CONSTRAINTS ON OPTIONS

    checkConstraints(options)


    # RETURN

    return options


def addConstants(options):
    # add option constants
    # --filenames
    options.FILENAME_SRCML = 0
    options.FILENAME_SOURCE = 1


def checkConstraints(options):
    # constraints
    if (options.allkinds == True and options.inputfile):
        print "Using all kinds of preparation for a single input and output file is weird!"
        sys.exit(1)
