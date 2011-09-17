#!/bin/bash

LOGFILE=./log/cppstats_general_preparation_logfile_`date +%Y%m%d`_$RANDOM.txt
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
	# cut of _cppstats for inputfile
	notify-send "starting $dir"
	./cppstats_general_prepare.sh $dir 2>&1 | tee -a $LOGFILE >> /dev/null
	notify-send "finished $dir"
done < $INPUTFILE
