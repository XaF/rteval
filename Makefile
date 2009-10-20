HERE	:=	$(shell pwd)
PACKAGE :=	rteval
VERSION :=      $(shell awk '/Version:/ { print $$2 }' ${PACKAGE}.spec | head -n 1)
D	:=	10
PYSRC	:=	rteval/rteval.py 	\
		rteval/cyclictest.py 	\
		rteval/dmi.py 		\
		rteval/hackbench.py 	\
		rteval/__init__.py 	\
		rteval/kcompile.py 	\
		rteval/load.py 		\
		rteval/rtevalclient.py 	\
		rteval/rtevalConfig.py 	\
		rteval/rtevalMailer.py 	\
		rteval/xmlout.py

XSLSRC	:=	rteval/rteval_dmi.xsl 	\
		rteval/rteval_text.xsl

CONFSRC	:=	rteval/rteval.conf

DESTDIR	:=
DATADIR	:=	$(DESTDIR)/usr/share
CONFDIR	:=	$(DESTDIR)/etc
MANDIR	:=	$(DESTDIR)/usr/share/man
PYLIB	:= 	$(DESTDIR)$(shell python -c 'import distutils.sysconfig;  print distutils.sysconfig.get_python_lib()')
LOADDIR	:=	loadsource

KLOAD	:=	$(LOADDIR)/linux-2.6.26.1.tar.bz2
HLOAD	:=	$(LOADDIR)/hackbench.tar.bz2

runit:
	[ -d ./run ] || mkdir run
	python rteval/rteval.py -D -v --workdir=./run --loaddir=./loadsource --duration=$(D) -f ./rteval/rteval.conf -i ./rteval

sysreport:
	python rteval/rteval.py -D -v --workdir=./run --loaddir=./loadsource --duration=$(D) -i ./rteval --sysreport

clean:
	rm -f *~ rteval/*~ rteval/*.py[co] *.tar.bz2

realclean: clean
	rm -rf run tarball rpm

install: installdirs
	if [ "$(DESTDIR)" = "" ]; then \
		python setup.py install; \
	else \
		python setup.py install --root=$(DESTDIR); \
	fi
	install -m 644 $(KLOAD) $(DATADIR)/rteval/loadsource
	install -m 644 $(HLOAD) $(DATADIR)/rteval/loadsource
	install -m 644 rteval/rteval_text.xsl $(DATADIR)/rteval
	install -m 644 rteval/rteval_dmi.xsl $(DATADIR)/rteval
	install -m 644 rteval/rteval.conf $(CONFDIR)
	install -m 644 doc/rteval.8 $(MANDIR)/man8/
	gzip $(MANDIR)/man8/rteval.8
	chmod 755 $(PYLIB)/rteval/rteval.py
	if [ "$(DESTDIR)" = "" ]; then \
		ln -s $(PYLIB)/rteval/rteval.py /usr/bin/rteval; \
	fi


installdirs:
	[ -d $(DATADIR)/rteval/loadsource ] || mkdir -p $(DATADIR)/rteval/loadsource
	[ -d $(CONFDIR) ] || mkdir -p $(CONFDIR)
	[ -d $(MANDIR)/man8 ]  || mkdir -p $(MANDIR)/man8
	[ -d $(PYLIB) ]   || mkdir -p $(PYLIB)
	[ -d $(DESTDIR)/usr/bin ] || mkdir -p $(DESTDIR)/usr/bin

uninstall:
	rm -f /usr/bin/rteval
	rm -f $(CONFDIR)/rteval.conf
	rm -f $(MANDIR)/man8/rteval.8.gz
	rm -rf $(PYLIB)/rteval
	rm -rf $(DATADIR)/rteval

tarfile:
	rm -rf tarball && mkdir -p tarball/rteval-$(VERSION)/rteval
	cp $(PYSRC) tarball/rteval-$(VERSION)/rteval
	cp $(XSLSRC) tarball/rteval-$(VERSION)/rteval
	cp $(CONFSRC) tarball/rteval-$(VERSION)/rteval
	cp -r doc/ tarball/rteval-$(VERSION)
	cp Makefile setup.py rteval.spec COPYING tarball/rteval-$(VERSION)
	tar -C tarball -cjvf rteval-$(VERSION).tar.bz2 rteval-$(VERSION)

rpm:	tarfile
	rm -rf rpm
	mkdir -p rpm/{BUILD,RPMS,SRPMS,SOURCES,SPECS}
	cp rteval-$(VERSION).tar.bz2 rpm/SOURCES
	cp rteval.spec rpm/SPECS
	cp loadsource/* rpm/SOURCES
	rpmbuild -ba --define "_topdir $(HERE)/rpm" rpm/SPECS/rteval.spec

help:
	@echo ""
	@echo "rteval Makefile targets:"
	@echo ""
	@echo "        runit:     do a short testrun locally [default]"
	@echo "        rpm:       run rpmbuild"
	@echo "        tarfile:   create the source tarball"
	@echo "        install:   install rteval locally"
	@echo "        clean:     cleanup generated files"
	@echo "        sysreport: do a short testrun and generate sysreport data"
	@echo ""
