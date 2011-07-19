# create zip file
NAME=cppstats
VERSION=0.7
FILES=dmacros.py pxml.py pstat.py stats.py src2srcml2009 srcml2src2009 rewriteifdefs.py partial_preprocessor.py cpplib.py cppstats_general_prepare.sh move_multiple_macros.py delete_comments.xsl delete_emptylines.sed delete_include_guards.py cppstats_pretty_prepare.sh

${NAME}_${VERSION}.zip: ${FILES}
	zip $@ ${FILES}
