HERE	:=	$(shell pwd)
PACKAGE :=	rteval
VERSION :=      $(shell awk '/Version:/ { print $$2 }' ${PACKAGE}.spec)
D	:=	10

runit:
	[ -d ./run ] || mkdir run
	python rteval/rteval.py -v --workdir=./run --loaddir=./loadsource --duration=$(D)

sysreport:
	python rteval/rteval.py -v --workdir=./run --loaddir=./loadsource --duration=$(D) --sysreport

clean:
	rm -f rteval/*~ rteval/*.py[co] *.tar.bz2

realclean: clean
	rm -rf run tarball rpm

install:
	python setup.py --dry-run install


tarfile:
	rm -rf tarball && mkdir -p tarball/rteval-$(VERSION)
	cp -r rteval tarball/rteval-$(VERSION)
	cp Makefile setup.py rteval.spec tarball/rteval-$(VERSION)
	tar -C tarball -cjvf rteval-$(VERSION).tar.bz2 rteval-$(VERSION)

rpm:	tarfile
	rm -rf rpm
	mkdir -p rpm/{BUILD,RPMS,SRPMS,SOURCES,SPECS}
	cp rteval-$(VERSION).tar.bz2 rpm/SOURCES
	cp rteval.spec rpm/SPECS
	cp loadsource/* rpm/SOURCES
	rpmbuild -ba --define "_topdir $(HERE)/rpm" rpm/SPECS/rteval.spec
