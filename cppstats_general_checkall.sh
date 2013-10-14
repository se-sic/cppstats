#!/bin/bash

LOGFILE=./log/cppstats_general_logfile_`date +%Y%m%d`_$RANDOM.txt
INPUTFILE=./cppstats_input.txt

# possible arguments: --loff (for list-of-features file)
ARGS=${@}

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
	echo "# check `basename $dir`"
	./pxml.py --folder $dir/_cppstats ${ARGS} 2>&1 | tee -a $LOGFILE >> /dev/null
	notify-send "finished $dir"
done < $INPUTFILE
