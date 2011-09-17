#!/bin/bash

LOGFILE=./log/cppstats_disciplined_preparation_log_`date +%Y%m%d`_$RANDOM.txt
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
	# cut of _cppstats_discpline of inputfile
	notify-send "starting $dir"
	./cppstats_dmacros_prepare.sh $dir 2>&1 | tee -a $LOGFILE >> /dev/null
	notify-send "finished $dir"
done < $INPUTFILE
