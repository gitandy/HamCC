VER = $(shell git describe --tags)
VERSION = $(firstword $(subst -, ,$(VER)))
ifeq ($(shell git diff --name-only),)
UNCLEAN = "False"
else
UNCLEAN = "True"
endif

BRANCH = $(shell git rev-parse --abbrev-ref HEAD)

NO_OBSOLETE=

all:  src/hamcc/__version__.py

src/hamcc/__version__.py:
	echo __version__ = \'$(VERSION)\' > $@
	echo __version_str__ = \'$(VER)\' >> $@
	echo __branch__ = \'$(BRANCH)\' >> $@
	echo __unclean__ = $(UNCLEAN) >> $@

bdist_win: NO_OBSOLETE=-no-obsolete
bdist_win: clean all test
	PYTHONPATH=./src python setup_win.py bdist -d dist_exe;

dist: NO_OBSOLETE=-no-obsolete
dist: clean all test
	python -m pip install --upgrade pip;
	python -m pip install --upgrade build;
	python -m build;

release:
	python -m pip install --upgrade twine;
	python -m twine upload dist/*;

test:
	flake8 ./src --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 ./src --count --max-complexity=20 --max-line-length=120 --statistics
	PYTHONPATH=./src python -m unittest discover -s ./test

.PHONY: src/hamcc/__version__.py test

clean:
	rm -rf build
	rm -rf dist
	rm -f src/hamcc/__version__.py
	rm -f
