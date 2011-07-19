#!/bin/bash

LOGFILE=/work/joliebig/cppstats/cppstats_disciplined_logfile_`date +%Y%m%d`_$RANDOM.txt
INPUTFILE=/home/joliebig/workspace/reverse_cpp/src/cppstats_input.txt

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
	/home/joliebig/workspace/reverse_cpp/src/dmacros.py -a 1 -d $dir/_cppstats_discipline 2>&1 | tee -a $LOGFILE >> /dev/null
	notify-send "finished $dir"
done < $INPUTFILE
