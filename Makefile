HERE	:=	$(shell pwd)
PACKAGE :=	prevert
VERSION :=      $(shell awk '/Version:/ { print $$2 }' ${PACKAGE}.spec)

runit:
	python prevert/prevert.py -v --builddir=./run --loaddir=./loadsource --duration=10

clean:
	rm -f prevert/*~ prevert/*.py[co] *.tar.bz2

install:
	python setup.py --dry-run install


tarfile:
	rm -rf tarball && mkdir -p tarball/prevert-$(VERSION)
	cp -r prevert tarball/prevert-$(VERSION)
	cp Makefile setup.py prevert.spec tarball/prevert-$(VERSION)
	tar -C tarball -cjvf prevert-$(VERSION).tar.bz2 prevert-$(VERSION)

rpm:	tarfile
	rm -rf rpm
	mkdir -p rpm/{BUILD,RPMS,SRPMS,SOURCES,SPECS}
	cp prevert-$(VERSION).tar.bz2 rpm/SOURCES
	cp prevert.spec rpm/SPECS
	cp loadsource/* rpm/SOURCES
	rpmbuild -ba --define "_topdir $(HERE)/rpm" rpm/SPECS/prevert.spec
