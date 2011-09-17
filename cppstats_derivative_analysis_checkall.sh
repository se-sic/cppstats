#!/bin/bash

LOGFILE=./log/cppstats_derivative_analysis_logfile_`date +%Y%m%d`_$RANDOM.txt
INPUTFILE=./cppstats_input.txt

if [ -e $LOGFILE ]; then
	rm $LOGFILE
fi
touch $LOGFILE

which notify-send > /dev/null
if [ $? -ne 0 ]; then
	echo '### program notify-send missing!'
	echo '    aptitude install libnotify-bin'
	exit 1
fi

while read dir; do
	notify-send "starting $dir"
	./derivan.py --folder $dir/_cppstats_discipline 2>&1 | tee -a $LOGFILE >> /dev/null
	notify-send "finished $dir"
done < $INPUTFILE
