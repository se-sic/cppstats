#!/bin/bash

LOGFILE="./log/cppstats_disciplined_logfile_%s_`date +%Y%m%d_%H%M%S`.txt"
INPUTFILE="./cppstats_input.txt"

#if [ -e $LOGFILE ]; then
	#rm $LOGFILE
#fi
#touch $LOGFILE

which notify-send > /dev/null
if [ $? -ne 0 ]; then
	echo '### program notify-send missing!'
	echo '    aptitude install libnotify-bin'
	exit 1
fi

which parallel > /dev/null
if [ $? -ne 0 ]; then
	echo '### program "parallel" missing!'
	echo '    http://www.gnu.org/software/parallel/'
	echo '    (tested with version 20140422)'
	exit 1
fi

#while read dir; do
	#notify-send "starting $dir"
	#echo "# check `basename $dir`"
	#./dmacros.py -a 1 -d $dir/_cppstats_discipline 2>&1 | tee -a $LOGFILE >> /dev/null
	#notify-send "finished $dir"
#done < $INPUTFILE


function cppstats_dmacros_check() {
	if [ -z "$1" ]; then return 0; fi #skip if folder argument is empty
	FOLDER=`basename "$1"`

	notify-send "starting $FOLDER"
	echo "# check $FOLDER"
	#TODO cut "_cppstats_discipline" off of parameter!
	./dmacros.py -a 1 -d "${1}/_cppstats_discipline" 2>&1 | tee -a `printf ${LOGFILE} ${FOLDER}` >> /dev/null
	notify-send "finished $FOLDER"

	return 0
}
export LOGFILE
export -f cppstats_dmacros_check


parallel --gnu --no-notice --arg-file "${INPUTFILE}" cppstats_dmacros_check
