PROJECT = bbsengine6
VERSION = $(shell date +%Y%m%d%H%M)
USER = $(shell whoami)

.PHONY: all version clean test test-unit test-integration lint

all:

version:
	@echo '__version__ = "0.0.1.dev$(VERSION)"' > src/$(PROJECT)/_version.py
	@echo '__datestamp__ = "$(VERSION)"' >> src/$(PROJECT)/_version.py
	@echo '__githash__ = "'`git log -1 --format='%H' 2>/dev/null | cut -c 1-16`'"' >> src/$(PROJECT)/_version.py
	@cat src/$(PROJECT)/_version.py

clean:
	-rm *~

test:
	cd $(CURDIR) && python3 -m pytest tests/ -p no:cacheprovider

test-unit:
	cd $(CURDIR) && python3 -m pytest tests/ -m unit -p no:cacheprovider

test-integration:
	cd $(CURDIR) && python3 -m pytest tests/ -m integration -p no:cacheprovider

lint:
	cd $(CURDIR)/src && python3 -m ruff check .
