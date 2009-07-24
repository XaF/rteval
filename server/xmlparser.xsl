<?xml version="1.0"?>
<!--
     *
     *  GPLv2 - Copyright (C) 2009
     *          David Sommerseth <davids@redhat.com>
     *
     *  This program is free software; you can redistribute it and/or
     *  modify it under the terms of the GNU General Public License
     *  as published by the Free Software Foundation; version 2
     *  of the License.
     *
     *  This program is distributed in the hope that it will be useful,
     *  but WITHOUT ANY WARRANTY; without even the implied warranty of
     *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
     *  GNU General Public License for more details.
     *
     *  You should have received a copy of the GNU General Public License
     *  along with this program; if not, write to the Free Software
     *  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
     *
-->

<xsl:stylesheet  version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml"  omit-xml-declaration="yes" version="1.0" encoding="UTF-8" indent="no"/>

  <xsl:template match="/">
    <xsl:choose>
      <xsl:when test="$table = 'rtevalruns_sql'">
        <xsl:if test="$syskey = ''">
          <xsl:message terminate="yes">
            <xsl:text>Invalid 'table' parameter: </xsl:text><xsl:value-of select="$table"/>
          </xsl:message>
        </xsl:if>
        <xsl:apply-templates select="/rteval" mode="rtevalruns"/>
      </xsl:when>
      <xsl:when test="$table = 'rtevalruns_details'">
        <xsl:apply-templates select="/rteval" mode="rtevalruns_details"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:message terminate="yes">
          <xsl:text>Invalid 'table' parameter: </xsl:text><xsl:value-of select="$table"/>
        </xsl:message>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="/rteval" mode="rtevalruns">
    <xsl:variable name="insert">
      <xsl:text>INSERT INTO rtevalruns (syskey, kernel_ver, kernel_rt, arch,</xsl:text>
      <xsl:text> run_start, run_duration, load_avg, version)</xsl:text>
    </xsl:variable>
    <xsl:variable name="values">
      <xsl:value-of select="$syskey"/>
      <xsl:text>,'</xsl:text>
      <xsl:value-of select="uname/kernel"/>
      <xsl:text>',</xsl:text>
      <xsl:choose>
        <xsl:when test="uname/kernel/@is_RT = '1'">true</xsl:when>
        <xsl:otherwise>False</xsl:otherwise>
      </xsl:choose>
      <xsl:text>,'</xsl:text>
      <xsl:value-of select="uname/arch"/>
      <xsl:text>','</xsl:text>
      <xsl:value-of select="concat(run_info/date,' ',run_info/time)"/>
      <xsl:text>',</xsl:text>
      <xsl:value-of select="(run_info/@days*86400)+(run_info/@hours*3600)
                            +(run_info/@minutes*60)+(run_info/@seconds)"/>
      <xsl:text>,</xsl:text>
      <xsl:value-of select="loads/@load_average"/>
      <xsl:text>,'</xsl:text>
      <xsl:value-of select="@version"/>
      <xsl:text>'</xsl:text>
    </xsl:variable>

    <xsl:value-of select="concat($insert,' VALUES (', $values,')&#10;')"/>
  </xsl:template>

  <xsl:template match="/rteval" mode="rtevalruns_details">
    <xsl:text disable-output-escaping="yes">&lt;?xml version="1.0" encoding="UTF-8"?&gt;</xsl:text>
    <rtevalruns_details>
      <xsl:copy-of select="clocksource|loads|cyclictest/command_line"/>
    </rtevalruns_details>
  </xsl:template>

  <xsl:template match="/rteval" mode="cyclic_stats_sql">
    
  </xsl:template>

</xsl:stylesheet>
