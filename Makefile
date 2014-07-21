# create zip file
NAME=cppstats
VERSION=0.8
FILES=lib analyses preparations analysis.py cppstats_input.txt preparation.py README
# README_CYGWIN

${NAME}_${VERSION}.zip: ${FILES}
	zip -r  $@ ${FILES} -x \*.pyc *win/*
