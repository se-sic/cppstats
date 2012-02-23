#!/bin/bash

LOGFILE=./log/cppstats_deacode_zombiecode_analysis_logfile_`date +%Y%m%d`_$RANDOM.txt
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
	cp -r $dir/source $dir/_cppstats_dead
	chmod -R u+rw $dir/_cppstats_dead
	for f in `find $dir/_cppstats_dead -type f \( -name "*.c" -o -name "*.h" \)`; do
		/work/joliebig/vamos_tool/vamos-1.2/undertaker/undertaker -j dead ${f} 2>&1 | tee -a $LOGFILE >> /dev/null
	done
	notify-send "finished $dir"
done < $INPUTFILE
