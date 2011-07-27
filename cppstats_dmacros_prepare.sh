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
echo '### and renaming duplicates (only filenames) to a unique name.'
for i in .h .c;
do
	echo "formating source-file $i"
	find ${sourcedir} -type f -iname "*${i}" -exec cp --backup=t '{}' ${invest} \;
done

cd ${invest}
for i in `ls *~`;
do
	echo $i
	mv $i `echo $i | sed -r 's/(.+)\.(.+)\.~([0-9]+)~$/\1__\3.\2/g'`
done

# reformat source-files and delete comments and include guards
echo '### reformat source-files'
for i in .h .c;
do
	for j in `ls *${i}`;
	do
		j=${invest}/${j}

		# translate macros that span over multiple lines to one line
		cp ${j} ${j}.bak01
		mv ${j} tmp.txt
		${bin}/move_multiple_macros.py tmp.txt ${j}
		rm -f tmp.txt

		# delete comments
		cp ${j} ${j}.bak02
		${bin}/src2srcml --language=C ${j} -o tmp.xml
		xsltproc ${bin}/delete_comments.xsl tmp.xml > tmp_out.xml
		${bin}/srcml2src tmp_out.xml -o ${j}
		rm -f tmp.xml tmp_out.xml

		# format source-code
		cp ${j} ${j}.bak03
		astyle --style=java ${j}
		if [ -e ${j}.orig ]; then
			rm -f ${j}.orig
		fi

		# delete leading, trailing and inter (# ... if) whitespaces
		cp ${j} ${j}.bak04
		cat ${j} | sed 's/^[ \t]\+//g;s/[ \t]\+$//g;s/\#[ \t]\+/\#/g' > tmp.txt
		mv tmp.txt ${j}

		# delete multipe whitespaces
		cp ${j} ${j}.bak05
		cat ${j} | sed 's/\t/ /g;s/[ \t]\{2,\}/ /g' > tmp.txt
		mv tmp.txt ${j}

		# rewrite ifdefs and ifndefs
		cp ${j} ${j}.bak06
		${bin}/rewriteifdefs.py ${j} > tmp.txt
		mv tmp.txt ${j}
		
		# delete include guards
		if [ $i == '.h' ]; then
			echo 'deleting include guard in ' ${j}
			cp ${j} ${j}.bak07
			mv ${j} tmp.txt
			${bin}/delete_include_guards.py tmp.txt > ${j}
			rm -f tmp.txt
		fi
		
		# delete preprocessor directives in #ifdefs
		cp ${j} ${j}.bak08
		${bin}/partial_preprocessor.py -i ${j} -o tmp.txt
		mv tmp.txt ${j}

		# delete empty lines
		cp ${j} ${j}.bak09
		mv ${j} tmp.txt
		${bin}/delete_emptylines.sed tmp.txt > ${j}
		rm -f tmp.txt
	done
done


# create xml-representation of the source-code
echo '### create xml-representation of the source-code files'
for i in .h .c;
do
	for j in `ls *${i}`;
	do
		echo "create representation for ${j}"
		${bin}/src2srcml --cpp-markup-if0 --language=C ${j} -o ${j}.xml || rm ${j}.xml
	done
done

notify-send "finished ${indirabs}"
