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
indirabs="`cd \"${D}\" 2>/dev/null && pwd || echo \"${D}\"`/$B"


# change to script directory
if [ `dirname ${cmd}` != '.' ]; then
	cd `dirname ${cmd}` || exit -1
fi


# check the preconditions
bin=${PWD}
echo ${bin}
echo '### preliminaries ...'

case `uname -s` in
	Linux|linux) s2sml=src2srcml.linux; sml2s=srcml2src.linux;;
	Darwin|darwin) s2sml=src2srcml.osx; sml2s=srcml2src.osx;;
	*) echo '### program src2srcml missing'
	   echo '    see: http://www.sdml.info/projects/srcml/trunk/'
	   exit 1;;
esac

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
invest=${indirabs}/_cppstats_featurelocations

if [ -e ${invest} ]; then
	rm -rf ${invest}
fi
mkdir ${invest}


# copy source-files
echo '### preparing sources ...'
echo '### copying all-files to one folder ...'
echo '### and renaming duplicates (only filenames) to a unique name.'
cd ${sourcedir}
find . -type f \( -iname "*.h" -o -iname "*.c" \) -exec cp --parents --no-preserve=mode '{}' ${invest} \;

cd ${invest}

# reformat source-files and delete comments and include guards
echo '### reformat source-files'
for f in `find . -type f \( -iname "*.h" -o -iname "*.c" \)`; do
	f=${invest}/${f}

	# translate macros that span over multiple lines to one line
	cp ${f} ${f}.bak01
	mv ${f} ${f}tmp.txt
	${bin}/move_multiple_macros.py ${f}tmp.txt ${f}
	rm -f ${f}tmp.txt

#	# format source-code
#	cp ${f} ${f}.bak02
#	#astyle --style=java ${f}
#	if [ -e ${f}.orig ]; then
#		rm -f ${f}.orig
#	fi

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

# TODO muss das gemacht werden?
	# delete preprocessor directives in #ifdefs (such as #error, #line, #pragma)
	cp ${f} ${f}.bak08
	${bin}/partial_preprocessor.py -i ${f} -o ${f}tmp.txt
	mv ${f}tmp.txt ${f}

done # for f in `find . -type f \( -iname "*.h" -o -iname "*.c" \)`; do

# create xml-representation of the source-code
echo '### create xml-representation of the source-code files'
for f in `find . -type f \( -iname "*.h" -o -iname "*.c" \)`; do
	echo "create representation for ${invest}/${f}"
	${bin}/${s2sml} --language=C ${f} -o ${f}.xml || rm ${f}.xml
done #for f in `find . -type f \( -iname "*.h" -o -iname "*.c" \)`; do
