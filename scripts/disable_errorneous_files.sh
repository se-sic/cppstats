#!/bin/bash
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


INPUTFILE="cppstats_errorneous_files.txt"

while read file;
do
	basefile=`dirname ${file}`/`basename ${file} .xml`
	if [ ! -e "${basefile}" ]; then
		echo "ERROR: basefile ($basefile)" not available!
		continue
	fi
	if [ -e "${file}.disabled" ]; then
		echo "INFO: file ($file) already disabled"
		continue
	fi
	if [ -e "${file}" ]; then
		echo "INFO: moving file ($file)"
		mv ${file} ${file}.disabled
	else
		echo "INFO: file ($file) not available"
	fi
done < ${INPUTFILE}
