#!/bin/bash

INPUTFILE=/home/joliebig/workspace/reverse_cpp/src/cppstats_ifdefelif_input.txt

which notify-send > /dev/null
if [ $? -ne 0 ]; then
	echo '### program notify-send missing!'
	echo '    aptitude install libnotify-bin'
	exit 1
fi

while read dir; do
	cd $dir
	dir=$(dirname $dir)
	out=$(basename $dir)
	notify-send "starting $dir"
	egrep -h "#if|#elif" *.bak12 > /work/joliebig/cppstats/sebastian/`echo $out`_ifdefelif_`date +%Y%m%d`_$RANDOM.txt
	notify-send "finished $dir"
done < $INPUTFILE