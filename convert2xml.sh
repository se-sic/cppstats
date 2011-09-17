#!/bin/sh

prog=/home/joliebig/workspace/reverse_cpp/src/src2srcml2009
progargs='--language=C '

while read dir; do
	cd $dir
	echo $PWD
	rm *.xml
	for i in `ls *.c`;
	do
		${prog} ${progargs} $i $i.xml
	done
	for i in `ls *.h`;
	do
		${prog} ${progargs} $i $i.xml
	done
	cd ../..
done < ./projects.txt
