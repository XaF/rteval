%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?python_ver: %define python_ver %(%{__python} -c "import sys ; print sys.version[:3]")}

Name:		rteval
Version:	1.18
Release:	1%{?dist}
Summary:	Utility to evaluate system suitability for RT Linux

Group:		Development/Tools
License:	GPLv2
URL:		http://git.kernel.org/?p=linux/kernel/git/clrkwllms/rteval.git
Source0:	rteval-%{version}.tar.bz2
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:	python
Requires:	python
Requires:	python-schedutils python-ethtool libxslt-python >= 1.1.17
Requires:	python-dmidecode >= 3.10
Requires:	rt-tests >= 0.65
Requires:	rteval-loads
BuildArch:	noarch
Obsoletes:	rteval <= 1.7

%description
The rteval script is a utility for measuring various aspects of 
realtime behavior on a system under load. The script unpacks the
hackbench and kernel source, builds hackbench and then goes into a
loop, running hackbench and compiling a kernel tree. During that loop
the cyclictest program is run to measure event response time. After
the run time completes, a statistical analysis of the event response
times is done and printed to the screen.

%prep
%setup -q

# version sanity check (make sure specfile and rteval.py match)
srcver=$(awk '/version =/ { print $3; }' rteval/rteval.py | sed -e 's/"\(.*\)"/\1/')
if [ $srcver != %{version} ]; then
   printf "\n***\n*** rteval spec file version do not match the rteval/rteval.py version\n***\n\n"
   exit -1
fi

%build


%install
rm -rf ${RPM_BUILD_ROOT}
mkdir -p ${RPM_BUILD_ROOT}
make DESTDIR=${RPM_BUILD_ROOT} install_rteval
mkdir -p ${RPM_BUILD_ROOT}/usr/bin
# note that python_sitelib has a leading slash...
ln -s ../..%{python_sitelib}/rteval/rteval.py ${RPM_BUILD_ROOT}/usr/bin/rteval


%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%if "%{python_ver}" >= "2.5"
%{python_sitelib}/*.egg-info
%endif

%dir %{_datadir}/%{name}

%doc COPYING
%{_mandir}/man8/rteval.8*
%{_datadir}/%{name}/rteval_*.xsl
%config(noreplace) %{_sysconfdir}/rteval.conf
%{python_sitelib}/rteval/
/usr/bin/rteval

%changelog
* Tue Feb 16 2010 Clark Williams <williams@redhat.com> - 1.18-1
- fix usage of python 2.6 features on RHEL5 (python 2.4)

* Tue Feb 16 2010 Clark Williams <williams@redhat.com> - 1.17-1
- added logic to filter non-printables from service status output
  so that we have legal XML output
- added logic to hackbench.py to cleanup properly at the end
  of the test

* Thu Feb 11 2010 Clark Williams <williams@redhat.com> - 1.16-1
- fix errors in show_remaining_time() introduced because
  time values are floats rather than ints

* Thu Feb 11 2010 Clark Williams <williams@redhat.com> - 1.15-1
- added logic to use --numa and --smp options of new cyclictest
- added countdown report for time remaining in a run

* Tue Feb  9 2010 Clark Williams <williams@redhat.com> - 1.14-1
- David Sommerseth <davids@redhat.com>:
  merged  XMLReport() changes for hwcert suite

* Tue Dec 22 2009 Clark Williams <williams@redhat.com> - 1.13-1
- added cyclictest default initializers
- added sanity checks to statistics reduction code
- updated release checklist to include origin push
- updated Makefile clean and help targets
- davids updates (mainly for v7 integration):
  - Add explicit sys.path directory to the python sitelib+
    '/rteval'
  - Send program arguments via RtEval() constructor
  - Added more DMI data into the summary.xml report
  - Fixed issue with not including all devices in the 
    OnBoardDeviceInfo tag

* Thu Dec  3 2009 David Sommerseth <davids@redhat.com> - 1.12-2
- fixed Makefile and specfile to include and install the
  rteval/rteval_histogram_raw.py source file for gaining
  raw access to histogram data
- Removed xmlrpc package during merge against master_ipv4 branch

* Wed Nov 25 2009 Clark Williams <williams@redhat.com> - 1.12-1
- fix incorrect reporting of measurement thread priorities

* Mon Nov 16 2009 Clark Williams <williams@redhat.com> - 1.11-5
- ensure that no double-slashes ("//") appear in the symlink
  path for /usr/bin/rteval (problem with rpmdiff)

* Tue Nov 10 2009 Clark Williams <williams@redhat.com> - 1.11-4
- changed symlink back to install and tracked by %files

* Mon Nov  9 2009 Clark Williams <williams@redhat.com> - 1.11-3
- changed symlink generation from %post to %posttrans

* Mon Nov  9 2009 Clark Williams <williams@redhat.com> - 1.11-2
- fixed incorrect dependency for libxslt

* Fri Nov  6 2009 Clark Williams <williams@redhat.com> - 1.11-1
- added base OS info to XML file and XSL report
- created new package rteval-loads for the load source code

* Wed Nov  4 2009 Clark Williams <williams@redhat.com> - 1.10-1
- added config file section for cyclictest and two settable
  parameters, buckets and interval

* Thu Oct 29 2009 Clark Williams <williams@redhat.com> - 1.9-1
- merged davids updates:
	-H option (raw histogram data)
	cleaned up xsl files
	fixed cpu sorting

* Mon Oct 26 2009 David Sommerseth <davids@redhat.com> - 1.8-3
- Fixed rpmlint complaints

* Mon Oct 26 2009 David Sommerseth <davids@redhat.com> - 1.8-2
- Added xmlrpc package, containing the XML-RPC mod_python modules

* Tue Oct 20 2009 Clark Williams <williams@redhat.com> - 1.8-1
- split kcompile and hackbench into sub-packages
- reworked Makefile (and specfile) install/uninstall logic
- fixed sysreport incorrect plugin option
- catch failure when running on root-squashed NFS

* Tue Oct 13 2009 Clark Williams <williams@redhat.com> - 1.7-1
- added kthread status to xml file
- merged davids changes for option processing and additions
  to xml summary

* Tue Oct 13 2009 Clark Williams <williams@redhat.com> - 1.6-1
- changed stat calculation to loop less
- added methods to grab service and kthread status

* Mon Oct 12 2009 Clark Williams <williams@redhat.com> - 1.5-1
- changed cyclictest to use less memory when doing statisics
  calculations
- updated debug output to use module name prefixes 
- changed option processing to only process config file once

* Fri Oct  9 2009 Clark Williams <williams@redhat.com> - 1.4-1
- changed cyclictest to use histogram rather than sample array
- calcuated statistics directly from histogram
- changed sample interval to 100us
- added -a (affinity) argument to force cpu affinity for
  measurement threads

* Thu Sep 24 2009 David Sommerseth <davids@redhat.com> - 1.3-3
- Cleaned up the spec file and made rpmlint happy

* Wed Sep 23 2009 David Sommerseth <davids@redhat.com> - 1.3-2
- Removed version number from /usr/share/rteval path

* Tue Sep 22 2009 Clark Williams <williams@redhat.com> - 1.3-1
- changes from davids:
  * changed report code to sort by processor id
  * added report submission retry logic
  * added emailer class

* Fri Sep 18 2009 Clark Williams <williams@redhat.com> - 1.2-1
- added config file handling for modifying load behavior and
  setting defaults
- added units in report per IBM request

* Wed Aug 26 2009 Clark Williams <williams@redhat.com> - 1.1-2
- missed a version change in rteval/rteval.py

* Wed Aug 26 2009 Clark Williams <williams@redhat.com> - 1.1-1
- modified cyclictest.py to start cyclictest threads with a
  'distance' of zero, meaning they all have the same measurement
  interval

* Tue Aug 25 2009 Clark Williams <williams@redhat.com> - 1.0-1
- merged davids XMLRPC fixes
- fixed --workdir option
- verion bump to 1.0

* Thu Aug 13 2009 Clark Williams <williams@redhat.com> - 0.9-2
- fixed problem with incorrect version in rteval.py

* Tue Aug  4 2009 Clark Williams <williams@redhat.com> - 0.9-1
- merged dsommers XMLRPC and database changes
- Specify minimum python-dmidecode version, which got native XML support
- Added rteval_dmi.xsl
- Fixed permission issues in /usr/share/rteval-x.xx

* Wed Jul 22 2009 Clark Williams <williams@redhat.com> - 0.8-1
- added code to capture clocksource info
- added code to copy dmesg info to report directory
- added code to display clocksource info in report
- added --summarize option to display summary of existing report
- added helpfile target to Makefile

* Tue Mar 26 2009 Clark Williams <williams@torg> - 0.7-1
- added require for python-schedutils to specfile
- added default for cyclictest output file
- added help parameter to option parser data
- renamed xml output file to summary.xml
- added routine to create tarfile of result files

* Wed Mar 18 2009 Clark Williams <williams@torg> - 0.6-6
- added code to handle binary data coming from DMI tables

* Wed Mar 18 2009 Clark Williams <williams@torg> - 0.6-5
- fixed logic for locating XSL template (williams)
- fixed another stupid typo in specfile (williams)

* Wed Mar 18 2009 Clark Williams <williams@torg> - 0.6-4
- fixed specfile to install rteval_text.xsl in /usr/share directory

* Wed Mar 18 2009 Clark Williams <williams@torg> - 0.6-3
- added Requires for libxslt-python (williams)
- fixed race condition in xmlout constructor/destructor (williams)

* Wed Mar 18 2009 Clark Williams <williams@torg> - 0.6-2
- added Requires for libxslt (williams)
- fixed stupid typo in rteval/rteval.py (williams)

* Wed Mar 18 2009 Clark Williams <williams@torg> - 0.6-1
- added xml output logic (williams, dsommers)
- added xlst template for report generator (dsommers)
- added dmi/smbios output to report (williams)
- added __del__ method to hackbench to cleanup after run (williams)
- modified to always keep run data (williams)

* Fri Feb 20 2009 Clark Williams <williams@torg> - 0.5-1
- fixed tab/space mix problem
- added report path line to report

* Fri Feb 20 2009 Clark Williams <williams@torg> - 0.4-1
- reworked report output
- handle keyboard interrupt better
- removed duration mismatch between rteval and cyclictest

* Mon Feb  2 2009 Clark Williams <williams@torg> - 0.3-1
- initial checkin
