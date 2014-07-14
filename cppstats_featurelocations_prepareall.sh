#!/bin/bash

LOGFILE="./log/cppstats_featurelocations_logfile_%s_preparation_`date +%Y%m%d_%H%M%S`.txt"
INPUTFILE="./cppstats_input.txt"

#if [ -e $LOGFILE ]; then
#	rm $LOGFILE
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
#	# cut of _cppstats_discpline of inputfile
#	notify-send "starting $dir"
#	./cppstats_pretty_prepare.sh $dir 2>&1 | tee -a $LOGFILE >> /dev/null
#	notify-send "finished $dir"
#done < $INPUTFILE


function cppstats_featurelocations_prepare() {
	if [ -z "$1" ]; then return 0; fi #skip if folder argument is empty
	FOLDER=`basename "$1"`

	notify-send "starting $1"
	echo "# prepare" `basename "$1"`
	./cppstats_featurelocations_prepare.sh "${1}" 2>&1 | tee -a `printf ${LOGFILE} ${FOLDER}` >> /dev/null
	notify-send "finished $1"

	return 0
}
export LOGFILE
export -f cppstats_featurelocations_prepare

parallel --gnu --no-notice --arg-file "${INPUTFILE}" cppstats_featurelocations_prepare
