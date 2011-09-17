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

# create the working directory within the sw-project
cd ${indirabs}
sourcedir=${indirabs}/source
invest=${indirabs}/_cppstats2010

if [ -e ${invest} ]; then
	rm -rf ${invest}
fi
mkdir ${invest}


# copy source-files
echo '### preparing sources ...'
echo '### copying all-files to one folder ...'
echo '### and renaming duplicates (only filenames) to a unique name.'
cd ${sourcedir}
cp -r . ${invest}
chmod -R 755 ${invest}
find ${invest} -name "*.h" -prune -o -name "*.c" -prune -o -exec rm -f '{}' \;

notify-send "starting ${indirabs}"
cd ..
cd ${invest}

# create xml-representation of the source-code
echo '### create xml-representation of the source-code files'
for i in .h .c;
do
	echo "create representation for ${i}"
	# || rm ${j}.xml is a workaround - since for longer files src2srcml does not work
	find ${invest} -type f -name "*${i}" -exec ${bin}/src2srcml2010 --cpp-markup-if0 --language=C '{}' --output='{}'.xml \;
done

notify-send "finished ${indirabs}"
