<!--
cppstats is a suite of analyses for measuring C preprocessor-based
variability in software product lines.
Copyright (C) 2011-2015 University of Passau, Germany

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this program.  If not, see
<http://www.gnu.org/licenses/>.

Contributors:
    Jörg Liebig <joliebig@fim.uni-passau.de>
    Claus Hunsen <hunsen@fim.uni-passau.de>
-->
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:cpp="http://www.srcML.org/srcML/cpp"
	xmlns:srcml="http://www.srcML.org/srcML/src"
>

<!-- replace comments with empty lines -->
<xsl:template match="srcml:comment" name="lines">
  <!--select everything after first line break-->
  <xsl:param name="pText" select="substring-after(., '&#xA;')"/>

  <!-- if there is some text in the comment,
       replace each line with an empty line! -->
  <xsl:if test="string-length($pText)">
   <xsl:text>&#10;</xsl:text>

   <xsl:call-template name="lines">
    <xsl:with-param name="pText" select="substring-after($pText, '&#xA;')"/>
   </xsl:call-template>
  </xsl:if>
</xsl:template>

<xsl:template match="*">
	<xsl:copy>
		<xsl:apply-templates />
	</xsl:copy>
</xsl:template>

</xsl:stylesheet>

