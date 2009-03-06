<?xml version="1.0"?>
<xsl:stylesheet  version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>

  <!--                       -->
  <!-- Main report framework -->
  <!--                       -->
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
   <!-- Format other sections of the report, if they are found                 -->
   <!-- To add support for even more sections, just add them into the existing -->
   <!-- xsl:apply-tempaltes tag, separated with pipe(|)                        -->
   <!--                                                                        -->
   <!--       select="cyclictest|new_foo_section|another_section"              -->
   <!--                                                                        -->
   <xsl:apply-templates select="cyclictest"/>
  ===================================================================
</xsl:template>
  <!--                              -->
  <!-- End of main report framework -->
  <!--                              -->



  <!--  Formats and lists all used commands lines  -->
  <xsl:template match="command_line">
           - <xsl:value-of select="@name"/>: <xsl:value-of select="."/>
  </xsl:template>



  <!-- Format the cyclic test section of the report -->
  <xsl:template match="/rteval/cyclictest">
   ** Cyclic test
      Command: <xsl:value-of select="command_line"/>

      System:  <xsl:value-of select="system/@description"/>
      Statistics: <xsl:apply-templates select="system/statistics"/>
      <!-- Add CPU core info and stats-->
      <xsl:apply-templates select="core"/>
  </xsl:template>



  <!--  Format the CPU core section in the cyclict test part -->
  <xsl:template match="cyclictest/core">

      CPU core <xsl:value-of select="@id"/>   Priority: <xsl:value-of select="@priority"/>
      Statistics: <xsl:apply-templates select="statistics"/>
  </xsl:template>



  <!-- Generic formatting of statistics information -->
  <xsl:template match="statistics">
          Min: <xsl:value-of select="minimum"/>   Max: <xsl:value-of select="maximum"/>   Mean: <xsl:value-of select="mean"/>
          Std.dev: <xsl:value-of select="standard_deviation"/>       Median: <xsl:value-of select="median"/>
          Samples: <xsl:value-of select="samples"/>  
          Range: <xsl:value-of select="range"/>   
          Mode: <xsl:value-of select="mode"/>
  </xsl:template>

</xsl:stylesheet>