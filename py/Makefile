PROJECT = bbsengine6
OUTDIR = /srv/repo/$(PROJECT)/
VERSION = $(shell date +%Y%m%d%H%M)
USER = $(shell whoami)

.PHONY: all version clean stale-build test test-unit test-integration lint

all:

version:
	@echo '__version__ = "0.0.3.dev$(VERSION)"' > src/$(PROJECT)/_version.py
	@echo '__datestamp__ = "$(VERSION)"' >> src/$(PROJECT)/_version.py
	@echo '__githash__ = "'`git log -1 --format='%H' 2>/dev/null | cut -c 1-16`'"' >> src/$(PROJECT)/_version.py
	@cat src/$(PROJECT)/_version.py

# Move aside any build/dist/egg-info directory the project holds before a build.
# A tree left by another user (or a failed build) cannot be deleted, but renaming
# it only needs write access to this project directory. The stale tree is kept
# under a *.stale.<timestamp> name, so nothing is lost and the build starts clean.
stale-build:
	@ts=$$(date +%Y%m%d%H%M%S); \
	for d in build dist src/*.egg-info; do \
		for x in $$d; do \
			[ -e "$$x" ] || continue; \
			mv "$$x" "$$x.stale.$$ts" && echo "stale-build: moved $$x -> $$x.stale.$$ts"; \
		done; \
	done

clean: stale-build
	-rm -rf build dist
	-rm -rf src/*.egg-info
	-find . -type d -name __pycache__ -exec rm -rf {} +
	-find . -type d -name .pytest_cache -exec rm -rf {} +
	-find . -type d -name .ruff_cache -exec rm -rf {} +
	-find . -type d -name .mypy_cache -exec rm -rf {} +
	-rm *~

test:
	cd $(CURDIR) && python3 -m pytest tests/ -p no:cacheprovider

test-unit:
	cd $(CURDIR) && python3 -m pytest tests/ -m unit -p no:cacheprovider

test-integration:
	cd $(CURDIR) && python3 -m pytest tests/ -m integration -p no:cacheprovider

lint:
	cd $(CURDIR)/src && python3 -m ruff check .
