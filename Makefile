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

runit:
	[ -d ./run ] || mkdir run
	python rteval/rteval.py -D -v --workdir=./run --loaddir=./loadsource --duration=$(D) -f ./rteval/rteval.conf -i ./rteval rteval

sysreport:
	python rteval/rteval.py -v --workdir=./run --loaddir=./loadsource --duration=$(D) --sysreport

clean:
	rm -f *~ rteval/*~ rteval/*.py[co] *.tar.bz2

realclean: clean
	rm -rf run tarball rpm

install:
	python setup.py --dry-run install

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
