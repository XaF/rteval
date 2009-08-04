%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?python_ver: %define python_ver %(%{__python} -c "import sys ; print sys.version[:3]")}


Name:		rteval
Version:	0.9
Release:	1%{?dist}
Summary:	utility to evaluate system suitability for RT Linux

Group:		System/Utilities
License:	GPL
Source0:	rteval-%{version}.tar.bz2
Source1:	linux-2.6.26.1.tar.bz2
Source2:	hackbench.tar.bz2
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:	python gcc binutils make libxslt libxslt-python
Requires:	python-schedutils
Requires:	python-dmidecode >= 3.10
Requires: 	rt-tests >= 0.29
BuildArch: 	noarch

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

%build


%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/usr/share/%{name}-%{version}/loadsource
mkdir -p $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/%{python_sitelib}

python setup.py install --root $RPM_BUILD_ROOT
install %{SOURCE1} $RPM_BUILD_ROOT/usr/share/%{name}-%{version}/loadsource
install %{SOURCE2} $RPM_BUILD_ROOT/usr/share/%{name}-%{version}/loadsource
install rteval/rteval_text.xsl $RPM_BUILD_ROOT/usr/share/%{name}-%{version}/rteval_text.xsl
install rteval/rteval_dmi.xsl $RPM_BUILD_ROOT/usr/share/%{name}-%{version}/rteval_dmi.xsl

%clean
rm -rf $RPM_BUILD_ROOT

%post
rm -f /usr/bin/rteval
ln -s %{python_sitelib}/rteval/rteval.py /usr/bin/rteval

%files
%defattr(-,root,root,-)
%attr(0755, root, root) %{python_sitelib}/rteval
%doc
%attr(0644, root, root) /usr/share/%{name}-%{version}/loadsource/*
%attr(0644, root, root) /usr/share/%{name}-%{version}/rteval_text.xsl
%attr(0644, root, root) /usr/share/%{name}-%{version}/rteval_dmi.xsl

%if "%{python_ver}" >= "2.5"
%{python_sitelib}/*.egg-info
%endif

%changelog
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
