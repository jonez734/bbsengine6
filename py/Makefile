PROJECT = bbsengine6
VERSION = $(shell date +%Y%m%d%H%M)
USER = $(shell whoami)

.PHONY: all version clean

all:

version:
	@echo '__version__ = "0.0.1.dev$(VERSION)"' > src/$(PROJECT)/_version.py
	@echo '__datestamp__ = "$(VERSION)"' >> src/$(PROJECT)/_version.py
	@echo '__githash__ = "'`git log -1 --format='%H' 2>/dev/null | cut -c 1-16`'"' >> src/$(PROJECT)/_version.py
	@cat src/$(PROJECT)/_version.py

clean:
	-rm *~
