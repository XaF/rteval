<?xml version="1.0"?>
<xsl:stylesheet  version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>
  <xsl:template match="/rteval">  ===================================================================
   rteval (v<xsl:value-of select="@version"/>) report
  -------------------------------------------------------------------
   Test run:     <xsl:value-of select="run_info/date"/> <xsl:value-of select="run_info/time"/>
   Run time:     <xsl:value-of select="run_info/@days"/> days <xsl:value-of select="run_info/@hours"/>h <xsl:value-of select="run_info/@minutes"/>m <xsl:value-of select="run_info/@seconds"/>s

   Tested node:  <xsl:value-of select="uname/node"/>
   CPU cores:    <xsl:value-of select="hardware/cpu_cores"/>
   Memory:       <xsl:value-of select="hardware/memory_size"/> KB
   Kernel:       <xsl:value-of select="uname/kernel"/> <xsl:if test="uname/kernel/@is_RT = '1'"> (RT enabled)</xsl:if>
   Architecture: <xsl:value-of select="uname/arch"/>
   
   Load commands:
       Load average: <xsl:value-of select="loads/@load_average"/>
       Commands:<xsl:apply-templates select="loads/command_line"/><xsl:text>
</xsl:text>
   <xsl:apply-templates select="cyclictest"/>
  ===================================================================
</xsl:template>

<xsl:template match="/rteval/loads/command_line">
           - <xsl:value-of select="@name"/>: <xsl:value-of select="."/>
</xsl:template>

<xsl:template match="/rteval/cyclictest">
   ** Cyclic test
      Command: <xsl:value-of select="command_line"/>

      System:  <xsl:value-of select="system/@description"/>
      Statistics: <xsl:apply-templates select="system/statistics"/>

      <xsl:apply-templates select="core"/>
</xsl:template>

<xsl:template match="cyclictest/core">

      CPU Core <xsl:value-of select="@id"/>   Priority: <xsl:value-of select="@priority"/>
      Statistics: <xsl:apply-templates select="statistics"/>
</xsl:template>

<xsl:template match="statistics">
          Min: <xsl:value-of select="minimum"/>   Max: <xsl:value-of select="maximum"/>   Mean: <xsl:value-of select="mean"/>
          Std.dev: <xsl:value-of select="standard_deviation"/>       Median: <xsl:value-of select="median"/>
          Samples: <xsl:value-of select="samples"/>  
          Range: <xsl:value-of select="range"/>   
          Mode: <xsl:value-of select="mode"/>
</xsl:template>

</xsl:stylesheet>