%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?python_ver: %define python_ver %(%{__python} -c "import sys ; print sys.version[:3]")}


Name:		prevert
Version:	0.1
Release:	1%{?dist}
Summary:	utility to measure event response time under load

Group:		System/Utilities
License:	GPL
Source0:	prevert-%{version}.tar.bz2
Source1:	linux-2.6.27.8-modified.tar.bz2
Source2:	hackbench.tar.bz2
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:	python gcc binutils make
Requires: 	rt-tests >= 0.29
BuildArch: 	noarch

%description
The prevert script (PRe-VErification for Real Time)is a utility for measuring
the event response time under load. The script unpacks the hackbench and kernel
source, builds hackbench and then goes into a loop, running hackbench and compiling
a kernel tree. During that loop the cyclictest program is run to measure event
response time. After the run time completes, a statistical analysis of the event
response times is done and printed to the screen.

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

%clean
rm -rf $RPM_BUILD_ROOT

%post
rm -f /usr/bin/prevert
ln -s %{python_sitelib}/prevert/prevert.py /usr/bin/prevert

%files
%defattr(-,root,root,-)
%attr(0755, root, root) %{python_sitelib}/prevert
%doc
/usr/share/%{name}-%{version}/*
%if "%{python_ver}" >= "2.5"
%{python_sitelib}/*.egg-info
%endif
%changelog
