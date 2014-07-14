<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:cpp="http://www.sdml.info/srcML/cpp"
	xmlns:srcml="http://www.sdml.info/srcML/src"
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

