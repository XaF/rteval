runit:
	python prevert/prevert.py -v --builddir=./run --loaddir=./loadsource --duration=10

clean:
	rm -f prevert/*~ prevert/*.py[co]

install:
	python setup.py --dry-run install
