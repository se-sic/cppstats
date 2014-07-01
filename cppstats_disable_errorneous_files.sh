#!/bin/bash

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
		mv $file $file.disabled
	else
		echo "INFO: file ($file) not available"
	fi
done < ${INPUTFILE}
