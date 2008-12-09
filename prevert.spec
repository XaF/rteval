Name:		prevert
Version:	0.1
Release:	1%{?dist}
Summary:	utility to measure event response time under load

Group:		System/Utilities
License:	GPL
Source0:	prevert-%{version}.tar.bz2
Source1:	linux-2.6.27.tar.bz2
Source2:	hackbench.tar.bz2
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires:	python gcc binutils make rt-tests

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

make install DESTDIR=$RPM_BUILD_ROOT


%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc



%changelog
