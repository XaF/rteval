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
  <xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/">
    <xsl:choose>
      <!-- TABLE: systems -->
      <xsl:when test="$table = 'systems'">
        <xsl:apply-templates select="/rteval" mode="systems_sql"/>
      </xsl:when>

      <!-- TABLE: systems_hostname -->
      <xsl:when test="$table = 'systems_hostname'">
        <xsl:if test="string(number($syskey)) = 'NaN'">
          <xsl:message terminate="yes">
            <xsl:text>Invalid 'syskey' parameter value: </xsl:text><xsl:value-of select="syskey"/>
          </xsl:message>
        </xsl:if>
        <xsl:apply-templates select="/rteval" mode="sys_hostname_sql"/>
      </xsl:when>

      <!-- TABLE: rtevalruns -->
      <xsl:when test="$table = 'rtevalruns'">
        <xsl:if test="string(number($syskey)) = 'NaN'">
          <xsl:message terminate="yes">
            <xsl:text>Invalid 'syskey' parameter value: </xsl:text><xsl:value-of select="syskey"/>
          </xsl:message>
        </xsl:if>
        <xsl:if test="$report_filename = ''">
          <xsl:message terminate="yes">
            <xsl:text>The parameter 'report_filename' parameter cannot be empty</xsl:text>
          </xsl:message>
        </xsl:if>
        <xsl:apply-templates select="/rteval" mode="rtevalruns_sql"/>
      </xsl:when>

      <!-- TABLE: rtevalruns_details -->
      <xsl:when test="$table = 'rtevalruns_details'">
        <xsl:if test="string(number($rterid)) = 'NaN'">
          <xsl:message terminate="yes">
            <xsl:text>Invalid 'rterid' parameter value: </xsl:text><xsl:value-of select="$rterid"/>
          </xsl:message>
        </xsl:if>
       <xsl:apply-templates select="/rteval" mode="rtevalruns_details_sql"/>
      </xsl:when>

      <!-- TABLE: cyclic_statistics -->
      <xsl:when test="$table = 'cyclic_statistics'">
        <xsl:if test="string(number($rterid)) = 'NaN'">
          <xsl:message terminate="yes">
            <xsl:text>Invalid 'rterid' parameter value: </xsl:text><xsl:value-of select="$rterid"/>
          </xsl:message>
        </xsl:if>
        <xsl:apply-templates select="/rteval/cyclictest" mode="cyclic_stats_sql"/>
      </xsl:when>

      <!-- TABLE: cyclic_rawdata -->
      <xsl:when test="$table = 'cyclic_rawdata'">
        <xsl:if test="string(number($rterid)) = 'NaN'">
          <xsl:message terminate="yes">
            <xsl:text>Invalid 'rterid' parameter value: </xsl:text><xsl:value-of select="$rterid"/>
          </xsl:message>
        </xsl:if>
        <xsl:apply-templates select="/rteval/cyclictest/RawSampleData" mode="cyclic_raw_sql"/>
      </xsl:when>

      <xsl:otherwise>
        <xsl:message terminate="yes">
          <xsl:text>Invalid 'table' parameter value: </xsl:text><xsl:value-of select="$table"/>
        </xsl:message>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="/rteval" mode="systems_sql">
    <sqldata table="systems" key="syskey">
      <fields>
        <field fid="0">sysid</field>
        <field fid="1">dmidata</field>
      </fields>
      <records>
        <record>
          <value fid="0" hash="sha1">
            <xsl:value-of select="concat(HardwareInfo/@SystemUUID,':',HardwareInfo/@SerialNo)"/>
          </value>
          <value fid="1" type="xmlblob">
            <xsl:copy-of select="HardwareInfo"/>
          </value>
        </record>
      </records>
    </sqldata>
  </xsl:template>

  <xsl:template match="/rteval" mode="sys_hostname_sql">
    <sqldata table="systems_hostname">
      <fields>
        <field fid="0">syskey</field>
        <field fid="1">hostname</field>
        <field fid="2">ipaddr</field>
      </fields>
      <records>
        <record>
          <value fid="0"><xsl:value-of select="$syskey"/></value>
          <value fid="1"><xsl:value-of select="uname/node"/></value>
          <value fid="2"><xsl:value-of select="network_config/interface/IPv4[@defaultgw=1]/@ipaddr"/></value>
        </record>
      </records>
    </sqldata>
  </xsl:template>

  <xsl:template match="/rteval" mode="rtevalruns_sql">
    <sqldata table="rtevalruns" key="rterid">
      <fields>
        <field fid="0">syskey</field>
        <field fid="1">kernel_ver</field>
        <field fid="2">kernel_rt</field>
        <field fid="3">arch</field>
        <field fid="4">run_start</field>
        <field fid="5">run_duration</field>
        <field fid="6">load_avg</field>
        <field fid="7">version</field>
        <field fid="8">report_filename</field>
      </fields>
      <records>
        <record>
          <value fid="0"><xsl:value-of select="$syskey"/></value>
          <value fid="1"><xsl:value-of select="uname/kernel"/></value>
          <value fid="2"><xsl:choose>
            <xsl:when test="uname/kernel/@is_RT = '1'">true</xsl:when>
            <xsl:otherwise>false</xsl:otherwise></xsl:choose>
          </value>
          <value fid="3"><xsl:value-of select="uname/arch"/></value>
          <value fid="4"><xsl:value-of select="concat(run_info/date, ' ', run_info/time)"/></value>
          <value fid="5">
            <xsl:value-of select="(run_info/@days*86400)+(run_info/@hours*3600)
                                  +(run_info/@minutes*60)+(run_info/@seconds)"/>
          </value>
          <value fid="6"><xsl:value-of select="loads/@load_average"/></value>
          <value fid="7"><xsl:value-of select="@version"/></value>
          <value fid="8"><xsl:value-of select="$report_filename"/></value>
        </record>
      </records>
    </sqldata>
  </xsl:template>

  <xsl:template match="/rteval" mode="rtevalruns_details_sql">
    <sqldata table="rtevalruns_details">
      <fields>
        <field fid="0">rterid</field>
        <field fid="1">xmldata</field>
      </fields>
      <records>
        <record>
          <value fid="0"><xsl:value-of select="$rterid"/></value>
          <value fid="1" type="xmlblob">
            <rteval_details>
              <xsl:copy-of select="clocksource|network_config|loads|cyclictest/command_line"/>
            </rteval_details>
          </value>
        </record>
      </records>
    </sqldata>
  </xsl:template>

  <xsl:template match="/rteval/cyclictest" mode="cyclic_stats_sql">
    <sqldata table="cyclic_statistics">
      <fields>
        <field fid="0">rterid</field>
        <field fid="1">coreid</field>
        <field fid="2">priority</field>
        <field fid="3">num_samples</field>
        <field fid="4">lat_min</field>
        <field fid="5">lat_max</field>
        <field fid="6">lat_mean</field>
        <field fid="7">mode</field>
        <field fid="8">range</field>
        <field fid="9">median</field>
        <field fid="10">stddev</field>
      </fields>
      <records>
        <xsl:for-each select="core/statistics|system/statistics">
          <record>
            <value fid="0"><xsl:value-of select="$rterid"/></value>
            <value fid="1"><xsl:choose>
              <xsl:when test="../@id"><xsl:value-of select="../@id"/></xsl:when>
              <xsl:otherwise><xsl:attribute name="isnull">1</xsl:attribute></xsl:otherwise></xsl:choose>
            </value>
            <value fid="2"><xsl:choose>
              <xsl:when test="../@priority"><xsl:value-of select="../@priority"/></xsl:when>
              <xsl:otherwise><xsl:attribute name="isnull">1</xsl:attribute></xsl:otherwise></xsl:choose>
            </value>
            <value fid="3"><xsl:value-of select="samples"/></value>
            <value fid="4"><xsl:value-of select="minimum"/></value>
            <value fid="5"><xsl:value-of select="maximum"/></value>
            <value fid="6"><xsl:value-of select="median"/></value>
            <value fid="7"><xsl:value-of select="mode"/></value>
            <value fid="8"><xsl:value-of select="range"/></value>
            <value fid="9"><xsl:value-of select="mean"/></value>
            <value fid="10"><xsl:value-of select="standard_deviation"/></value>
          </record>
        </xsl:for-each>
      </records>
    </sqldata>
  </xsl:template>

  <xsl:template match="/rteval/cyclictest/RawSampleData" mode="cyclic_raw_sql">
    <sqldata table="cyclic_rawdata">
      <fields>
        <field fid="0">rterid</field>
        <field fid="1">cpu_num</field>
        <field fid="2">sampleseq</field>
        <field fid="3">latency</field>
      </fields>
      <records>
        <xsl:for-each select="Thread/Sample">
          <record>
            <value fid="0"><xsl:value-of select="$rterid"/></value>
            <value fid="1"><xsl:value-of select="../@id"/></value>
            <value fid="2"><xsl:value-of select="@seq"/></value>
            <value fid="3"><xsl:value-of select="@latency"/></value>
          </record>
        </xsl:for-each>
      </records>
    </sqldata>
  </xsl:template>
</xsl:stylesheet>
