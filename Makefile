PYTHON = python
PIP = pip
VENV_DIR = venv

VER = $(shell git describe --tags)
VERSION = $(firstword $(subst -, ,$(VER)))
ifeq ($(shell git diff --name-only),)
UNCLEAN = "False"
else
UNCLEAN = "True"
endif

BRANCH = $(shell git rev-parse --abbrev-ref HEAD)

ifeq ($(OS),Windows_NT)
VENV_BIN = $(VENV_DIR)/Scripts
PIP = $(VENV_BIN)/pip.exe
FLAKE8 = $(VENV_BIN)/flake8.exe
ifeq ($(shell if test -d $(VENV_DIR); then echo "exist";fi),exist)
PYTHON = $(VENV_BIN)/python.exe
endif
else
VENV_BIN = $(VENV_DIR)/bin
PIP = $(VENV_BIN)/pip
FLAKE8 = $(VENV_BIN)/flake8
ifeq ($(shell if test -d $(VENV_DIR); then echo "exist";fi),exist)
PYTHON = $(VENV_BIN)/python
endif
endif

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
	$(PYTHON) -m pip install --upgrade pip;
	$(PYTHON) -m pip install --upgrade build;
	$(PYTHON) -m build;

release:
	$(PYTHON) -m pip install --upgrade twine;
	$(PYTHON) -m twine upload dist/*;

test: all
	$(FLAKE8) ./src --count --select=E9,F63,F7,F82 --show-source --statistics
	$(FLAKE8) ./src --count --max-complexity=20 --ignore=E402 --max-line-length=120 --statistics
	PYTHONPATH=./src $(PYTHON) -m unittest discover -s ./test

build_devenv:
	if [ ! -d $(VENV_DIR) ]; then \
		$(PYTHON) -m venv $(VENV_DIR); \
		$(PIP) install --upgrade pip setuptools wheel; \
		$(PIP) install -r requirements.txt; \
	else \
		echo "Virtualenv $(VENV_DIR) already exists"; \
	fi

.PHONY: src/hamcc/__version__.py test clean_devenv build_devenv

clean:
	rm -rf build
	rm -rf dist
	rm -f src/hamcc/__version__.py
	rm -f

clean_devenv:
	rm -r venv

