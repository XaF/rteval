<?xml version="1.0"?>
<xsl:stylesheet  version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>

  <!--                       -->
  <!-- Main report framework -->
  <!--                       -->
  <xsl:template match="/rteval">
    <xsl:text>  ===================================================================&#10;</xsl:text>
    <xsl:text>   rteval (v</xsl:text><xsl:value-of select="@version"/><xsl:text>) report&#10;</xsl:text>
    <xsl:text>  -------------------------------------------------------------------&#10;</xsl:text>
    <xsl:text>   Test run:     </xsl:text>
    <xsl:value-of select="run_info/date"/><xsl:text> </xsl:text><xsl:value-of select="run_info/time"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Run time:     </xsl:text>
    <xsl:value-of select="run_info/@days"/><xsl:text> days </xsl:text>
    <xsl:value-of select="run_info/@hours"/><xsl:text>h </xsl:text>
    <xsl:value-of select="run_info/@minutes"/><xsl:text>m </xsl:text>
    <xsl:value-of select="run_info/@seconds"/><xsl:text>s</xsl:text>
    <xsl:text>&#10;</xsl:text>
    <xsl:if test="run_info/annotate">
      <xsl:text>   Remarks:      </xsl:text>
      <xsl:value-of select="run_info/annotate"/>
    </xsl:if>
    <xsl:text>&#10;&#10;</xsl:text>

    <xsl:text>   Tested node:  </xsl:text>
    <xsl:value-of select="SystemInfo/uname/node|uname/node"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Model:        </xsl:text>
    <xsl:value-of select="SystemInfo/DMIinfo/HardwareInfo/GeneralInfo/Manufacturer|HardwareInfo/GeneralInfo/ProductName"/>
    <xsl:text> - </xsl:text><xsl:value-of select="SystemInfo/DMIinfo/HardwareInfo/GeneralInfo/ProductName|HardwareInfo/GeneralInfo/ProductName"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   BIOS version: </xsl:text>
    <xsl:value-of select="SystemInfo/DMIinfo/HardwareInfo/BIOS|HardwareInfo/BIOS"/>
    <xsl:text> (ver: </xsl:text>
    <xsl:value-of select="SystemInfo/DMIinfo/HardwareInfo/BIOS/@Version|HardwareInfo/BIOS/@Version"/>
    <xsl:text>, rev :</xsl:text>
    <xsl:value-of select="SystemInfo/DMIinfo/HardwareInfo/BIOS/@BIOSrevision|HardwareInfo/BIOS/@BIOSrevision"/>
    <xsl:text>, release date: </xsl:text>
    <xsl:value-of select="SystemInfo/DMIinfo/HardwareInfo/BIOS/@ReleaseDate|HardwareInfo/BIOS/@ReleaseDate"/>
    <xsl:text>)</xsl:text>
    <xsl:text>&#10;&#10;</xsl:text>

    <xsl:text>   CPU cores:    </xsl:text>
    <xsl:choose>
      <xsl:when test="SystemInfo/CPUtopology">
	<xsl:value-of select="SystemInfo/CPUtopology/@num_cpu_cores"/>
	<xsl:text> (online: </xsl:text>
	<xsl:value-of select="SystemInfo/CPUtopology/@num_cpu_cores_online"/>
	<xsl:text>)</xsl:text>
      </xsl:when>
      <xsl:when test="hardware/cpu_topology">
        <xsl:value-of select="hardware/cpu_topology/@num_cpu_cores"/>
	<xsl:text> (online: </xsl:text>
	<xsl:value-of select="hardware/cpu_topology/@num_cpu_cores_online"/>
	<xsl:text>)</xsl:text>
      </xsl:when>
      <xsl:when test="hardware/cpu_cores">
	<xsl:value-of select="hardware/cpu_cores"/>
      </xsl:when>
      <xsl:otherwise>(unknown)</xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   NUMA Nodes:   </xsl:text>
    <xsl:choose>
      <xsl:when test="SystemInfo/Memory/numa_nodes">
        <xsl:value-of select="SystemInfo/Memory/numa_nodes"/>
      </xsl:when>
      <xsl:when test="hardware/numa_nodes">
        <xsl:value-of select="hardware/numa_nodes"/>
      </xsl:when>
      <xsl:otherwise>(unknown)</xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Memory:       </xsl:text>
    <xsl:value-of select="SystemInfo/Memory/memory_size|hardware/memory_size"/>
    <xsl:choose>
      <xsl:when test="SystemInfo/Memory/memory_size/@unit">
	<xsl:value-of select="concat(' ',SystemInfo/Memory/memory_size/@unit)"/>
      </xsl:when>
      <xsl:when test="hardware/memory_size/@unit">
	<xsl:value-of select="concat(' ',hardware/memory_size/@unit)"/>
      </xsl:when>
      <xsl:otherwise>
	<xsl:text> kB</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Kernel:       </xsl:text>
    <xsl:value-of select="SystemInfo/uname/kernel|uname/kernel"/>
    <xsl:if test="SystemInfo/uname/kernel/@is_RT = '1' or uname/kernel/@is_RT = '1'">  (RT enabled)</xsl:if>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Base OS:      </xsl:text>
    <xsl:value-of select="SystemInfo/uname/baseos|uname/baseos"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Architecture: </xsl:text>
    <xsl:value-of select="SystemInfo/uname/arch|uname/arch"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Clocksource:  </xsl:text>
    <xsl:value-of select="SystemInfo/Kernel/ClockSource/source[@current='1']|clocksource/current"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Available:    </xsl:text>
    <xsl:choose>
      <xsl:when test="SystemInfo/Kernel/ClockSource/source">
        <xsl:for-each select="SystemInfo/Kernel/ClockSource/source">
          <xsl:value-of select="."/>
          <xsl:text> </xsl:text>
        </xsl:for-each>
      </xsl:when>
      <xsl:when test="clocksource/available">
        <xsl:value-of select="clocksource/available"/>
      </xsl:when>
      <xsl:otherwise>(unknown)</xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;&#10;</xsl:text>
   
    <xsl:text>   System load:&#10;</xsl:text>
    <xsl:text>       Load average: </xsl:text>
    <xsl:value-of select="loads/@load_average"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:if test="loads/command_line">
      <xsl:text>&#10;</xsl:text>
      <xsl:text>       Executed loads:&#10;</xsl:text>
      <xsl:apply-templates select="loads/command_line"/>
    </xsl:if>
    <xsl:text>&#10;</xsl:text>
    <!-- Generate a summary report for all measurement profiles -->
    <xsl:apply-templates select="Measurements/Profile"/>
   <xsl:text>  ===================================================================&#10;</xsl:text>
</xsl:template>
  <!--                              -->
  <!-- End of main report framework -->
  <!--                              -->


  <!--  Formats and lists all used commands lines  -->
  <xsl:template match="command_line">
    <xsl:text>         - </xsl:text>
    <xsl:value-of select="@name"/>
    <xsl:text>: </xsl:text>
    <xsl:choose>
      <xsl:when test="not(@run) or @run = '1'">
	<xsl:value-of select="."/>
      </xsl:when>
      <xsl:otherwise>(Not run)</xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>


  <xsl:template match="/rteval/Measurements/Profile">
    <xsl:text>   Measurement profile </xsl:text>
    <xsl:value-of select="position()"/><xsl:text>: </xsl:text>
    <xsl:choose>
      <xsl:when test="@loads = '1'"><xsl:text>With loads, </xsl:text></xsl:when>
      <xsl:otherwise><xsl:text>Without loads, </xsl:text></xsl:otherwise>
    </xsl:choose>
    <xsl:choose>
      <xsl:when test="@parallel = '1'">
        <xsl:text>measurements in parallel</xsl:text>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text>measurements serialised</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>

    <!-- Format other sections of the report, if they are found                 -->
    <!-- To add support for even more sections, just add them into the existing -->
    <!-- xsl:apply-tempaltes tag, separated with pipe(|)                        -->
    <!--                                                                        -->
    <!--       select="cyclictest|new_foo_section|another_section"              -->
    <!--                                                                        -->
    <xsl:apply-templates select="cyclictest|hwlatdetect[@format='1.0']|sysstat"/>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>

  <!-- Format the cyclic test section of the report -->
  <xsl:template match="/rteval/Measurements/Profile/cyclictest">
    <xsl:text>       Latency test&#10;</xsl:text>

    <xsl:text>          Started: </xsl:text>
    <xsl:value-of select="timestamps/runloop_start"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Stopped: </xsl:text>
    <xsl:value-of select="timestamps/runloop_stop"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Command: </xsl:text>
    <xsl:value-of select="@command_line"/>
    <xsl:text>&#10;&#10;</xsl:text>

    <xsl:apply-templates select="abort_report"/>

    <xsl:text>          System:  </xsl:text>
    <xsl:value-of select="system/@description"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Statistics: &#10;</xsl:text>
    <xsl:apply-templates select="system/statistics"/>

    <!-- Add CPU core info and stats-->
    <xsl:apply-templates select="core">
      <xsl:sort select="@id" data-type="number"/>
    </xsl:apply-templates>
  </xsl:template>


  <!--  Format the CPU core section in the cyclict test part -->
  <xsl:template match="/rteval/Measurements/Profile/cyclictest/core">
    <xsl:text>          CPU core </xsl:text>
    <xsl:value-of select="@id"/>
    <xsl:text>       Priority: </xsl:text>
    <xsl:value-of select="@priority"/>
    <xsl:text>&#10;</xsl:text>
    <xsl:text>          Statistics: </xsl:text>
    <xsl:text>&#10;</xsl:text>
    <xsl:apply-templates select="statistics"/>
  </xsl:template>


  <!-- Generic formatting of statistics information -->
  <xsl:template match="/rteval/Measurements/Profile/cyclictest/*/statistics">
    <xsl:text>            Samples:           </xsl:text>
    <xsl:value-of select="samples"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:if test="samples > 0">
      <xsl:text>            Mean:              </xsl:text>
      <xsl:value-of select="mean"/>
      <xsl:value-of select="mean/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Median:            </xsl:text>
      <xsl:value-of select="median"/>
      <xsl:value-of select="median/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Mode:              </xsl:text>
      <xsl:value-of select="mode"/>
      <xsl:value-of select="mode/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Range:             </xsl:text>
      <xsl:value-of select="range"/>
      <xsl:value-of select="range/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Min:               </xsl:text>
      <xsl:value-of select="minimum"/>
      <xsl:value-of select="minimum/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Max:               </xsl:text>
      <xsl:value-of select="maximum"/>
      <xsl:value-of select="maximum/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Mean Absolute Dev: </xsl:text>
      <xsl:value-of select="mean_absolute_deviation"/>
      <xsl:value-of select="mean_absolute_deviation/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Std.dev:           </xsl:text>
      <xsl:value-of select="standard_deviation"/>
      <xsl:value-of select="standard_deviation/@unit"/>
      <xsl:text>&#10;</xsl:text>
    </xsl:if>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>


  <!-- Format the hwlatdetect test section of the report -->
  <xsl:template match="/rteval/Measurements/Profile/hwlatdetect[@format='1.0' and not(@aborted)]">
    <xsl:text>     Hardware latency detector&#10;</xsl:text>

    <xsl:text>       Run duration: </xsl:text>
    <xsl:value-of select="RunParams/@duration"/>
    <xsl:text> seconds&#10;</xsl:text>

    <xsl:text>       Threshold:    </xsl:text>
    <xsl:value-of select="RunParams/@threshold"/>
    <xsl:text>us&#10;</xsl:text>

    <xsl:text>       Width:       </xsl:text>
    <xsl:value-of select="RunParams/@width"/>
    <xsl:text>us&#10;</xsl:text>

    <xsl:text>       Window size: </xsl:text>
    <xsl:value-of select="RunParams/@window"/>
    <xsl:text>us&#10;&#10;</xsl:text>

    <xsl:text>       Threshold exceeded </xsl:text>
    <xsl:value-of select="samples/@count"/>
    <xsl:text> times&#10;</xsl:text>
    <xsl:apply-templates select="samples/sample"/>
  </xsl:template>

  <xsl:template match="/rteval/Measurements/Profile/hwlatdetect[@format='1.0' and @aborted > 0]">
    <xsl:text>     Hardware latency detector&#10;</xsl:text>
    <xsl:text>        ** WARNING ** hwlatedect failed to run&#10;</xsl:text>
  </xsl:template>

  <xsl:template match="/rteval/Measurements/Profile/hwlatdetect[@format='1.0']/samples/sample">
    <xsl:text>         - @</xsl:text>
    <xsl:value-of select="@timestamp"/>
    <xsl:text>  </xsl:text>
    <xsl:value-of select="@duration"/>
    <xsl:text>us&#10;</xsl:text>
  </xsl:template>

  <!-- Format the cyclic test section of the report -->
  <xsl:template match="/rteval/Measurements/Profile/sysstat">
    <xsl:text>       sysstat measurements&#10;</xsl:text>

    <xsl:text>          Started: </xsl:text>
    <xsl:value-of select="timestamps/runloop_start"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Stopped: </xsl:text>
    <xsl:value-of select="timestamps/runloop_stop"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Records saved: </xsl:text>
    <xsl:value-of select="@num_entries"/>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>

  <!-- Format information about aborts - if present -->
  <xsl:template match="abort_report">
      <xsl:text>      Run aborted: </xsl:text>
      <xsl:value-of select="@reason"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:if test="breaktrace">
        <xsl:text>                   </xsl:text>
        <xsl:text>Aborted due to latency exceeding </xsl:text>
        <xsl:value-of select="breaktrace/@latency_threshold"/>
        <xsl:text>us.&#10;</xsl:text>
        <xsl:text>                   </xsl:text>
        <xsl:text>Measured latency when stopping was </xsl:text>
        <xsl:value-of select="breaktrace/@measured_latency"/>
        <xsl:text>us.&#10;&#10;</xsl:text>
      </xsl:if>
  </xsl:template>

</xsl:stylesheet>
