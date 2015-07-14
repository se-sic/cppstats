#!/bin/sh
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


prog=/home/joliebig/workspace/reverse_cpp/src/src2srcml2009
progargs='--language=C '

while read dir; do
	cd ${dir}
	echo $PWD
	rm *.xml
	for i in `ls *.c`;
	do
		${prog} ${progargs} ${i} ${i}.xml
	done
	for i in `ls *.h`;
	do
		${prog} ${progargs} ${i} ${i}.xml
	done
	cd ../..
done < ./projects.txt
