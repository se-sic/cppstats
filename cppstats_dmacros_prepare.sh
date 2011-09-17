#!/bin/bash

# parameters
# cmd - script-name itself
# indir - input-directory
cmd=${0}

# get the abspath of the input-directory
if [ -z ${1} ]; then
	echo '### no input directory given!'
	exit -1
fi
indir=${1}

D=`dirname "${indir}"`
B=`basename "${indir}"`
indirabs="`cd \"$D\" 2>/dev/null && pwd || echo \"$D\"`/$B"


# change to script directory
if [ `dirname ${cmd}` != '.' ]; then
	cd `dirname ${cmd}` || exit -1
fi


# check the preconditions
bin=${PWD}
echo ${bin}
echo '### preliminaries ...'

which python > /dev/null
if [ $? -ne 0 ]; then
	echo '### programm python missing!'
	echo '    see: http://www.python.org/'
	exit 1
fi

which astyle > /dev/null
if [ $? -ne 0 ]; then
	echo '### programm astyle missing!'
	echo '    see: http://astyle.sourceforge.net/'
	exit 1
fi

which xsltproc > /dev/null
if [ $? -ne 0 ]; then
	echo '### programm xsltproc missing!'
	echo '    see: http://www.xmlsoft.org/XSLT/xsltproc2.html'
	exit 1
fi

which notify-send > /dev/null
if [ $? -ne 0 ]; then
	echo '### program notify-send missing!'
	echo '    aptitude install libnotify-bin'
	exit 1
fi


# create the working directory within the sw-project
cd ${indirabs}
sourcedir=${indirabs}/source
invest=${indirabs}/_cppstats_discipline

if [ -e ${invest} ]; then
	rm -rf ${invest}
fi
mkdir ${invest}

notify-send "starting ${indirabs}"

# copy source-files
echo '### preparing sources ...'
echo '### copying all-files to one folder ...'
cd ${sourcedir}
find . -type f \( -name "*.h" -o -name "*.c" \) -exec cp --parents '{}' ${invest} \;

cd ${invest}

# reformat source-files and delete comments and include guards
echo '### reformat source-files'
SAVEIFS=$IFS
IFS=$(echo -en "\n\b")
for f in `find . -type f \( -name "*.h" -o -name "*.c" \)`; do
	f=${invest}/${f}

	# translate macros that span over multiple lines to one line
	cp ${f} ${f}.bak01
	mv ${f} ${f}tmp.txt
	${bin}/move_multiple_macros.py ${f}tmp.txt ${f}
	rm -f ${f}tmp.txt

	# delete comments
	cp ${f} ${f}.bak02
	${bin}/src2srcml --language=C ${f} -o ${f}tmp.xml
	xsltproc ${bin}/delete_comments.xsl ${f}tmp.xml > ${f}tmp_out.xml
	${bin}/srcml2src ${f}tmp_out.xml -o ${f}
	rm -f ${f}tmp.xml ${f}tmp_out.xml

	# format source-code
	cp ${f} ${f}.bak03
	astyle --style=java ${f}
	if [ -e ${f}.orig ]; then
		rm -f ${f}.orig
	fi

	# delete leading, trailing and inter (# ... if) whitespaces
	cp ${f} ${f}.bak04
	cat ${f} | sed 's/^[ \t]\+//g;s/[ \t]\+$//g;s/\#[ \t]\+/\#/g' > ${f}tmp.txt
	mv ${f}tmp.txt ${f}

	# delete multipe whitespaces
	cp ${f} ${f}.bak05
	cat ${f} | sed 's/\t/ /g;s/[ \t]\{2,\}/ /g' > ${f}tmp.txt
	mv ${f}tmp.txt ${f}

	# rewrite ifdefs and ifndefs
	cp ${f} ${f}.bak06
	${bin}/rewriteifdefs.py ${f} > ${f}tmp.txt
	mv ${f}tmp.txt ${f}
	
	# delete include guards
	if [ ${f/*./} == 'h' ]; then
		echo 'deleting include guard in ' ${f}
		cp ${f} ${f}.bak07
		mv ${f} ${f}tmp.txt
		${bin}/delete_include_guards.py ${f}tmp.txt > ${f}
		rm -f ${f}tmp.txt
	fi
	
	# delete preprocessor directives in #ifdefs
	cp ${f} ${f}.bak08
	${bin}/partial_preprocessor.py -i ${f} -o ${f}tmp.txt
	mv ${f}tmp.txt ${f}

	# delete empty lines
	cp ${f} ${f}.bak09
	mv ${f} ${f}tmp.txt
	${bin}/delete_emptylines.sed ${f}tmp.txt > ${f}
	rm -f ${f}tmp.txt
done


# create xml-representation of the source-code
echo '### create xml-representation of the source-code files'
for f in `find . -type f \( -name "*.h" -o -name "*.c" \)`; do
	echo "create representation for ${invest}/${f}"
	${bin}/src2srcml --language=C ${f} -o ${f}.xml || rm ${f}.xml
done
IFS=$SAVEIFS
