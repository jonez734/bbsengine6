PROJECT = bbsengine6
OUTDIR = /srv/repo/$(PROJECT)/
VERSION := $(shell date +%Y%m%d%H%M)
export VERSION_PREFIX = 0.0.1.dev

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

.PHONY: install version deploy-tui
.PHONY: clean rename-sdist sign release all install

# DEPLOY_EDITABLE is set by `deploytool --editable`. Empty by default.
# When set to 1, deploy-tui installs editable from the source tree
# (`pip install -e .`). When unset, deploy-tui installs the wheel
# whose filename is composed from $(VERSION_PREFIX)$(VERSION), which
# matches the wheel produced by `make build` in the same invocation.
DEPLOY_EDITABLE ?=

install: version
	cd .. && $(PIP) install --no-cache-dir -e .

deploy-tui:
ifeq ($(DEPLOY_EDITABLE),1)
	cd .. && $(PIP) install --no-cache-dir -e .
else
	@WHEEL=$(OUTDIR)/$(PROJECT)-$(VERSION_PREFIX)$(VERSION)-py3-none-any.whl; \
	if [ ! -f "$$WHEEL" ]; then \
		echo "expected wheel $$WHEEL not found" >&2; \
		exit 1; \
	fi; \
	$(PIP) install --no-cache-dir $$WHEEL
endif

rename-sdist:
	@for f in $(OUTDIR)/*.tar.gz; do \
		if [ -f "$$f" ] && echo "$$f" | grep -vq '\-src\.tar\.gz' ; then \
			mv "$$f" "$${f%.tar.gz}-src.tar.gz"; \
			echo "Renamed $$f -> $${f%.tar.gz}-src.tar.gz"; \
		fi \
	done

sign:
	@for f in $(OUTDIR)/*; do \
		if [ -f "$$f" ] && [ ! -f "$$f.asc" ] && [ "$${f##*.}" != "asc" ]; then \
			gpg --armor --detach-sign "$$f"; \
			echo "Signed $$f"; \
		fi \
	done

release:
	$(MAKE) -C ../.. wheel-release

all:

clean:
	-rm *~
	$(MAKE) -C $(PROJECT) clean
	$(MAKE) -C tk clean

version:
	@echo '__version__ = "$(VERSION_PREFIX)$(VERSION)"' > $(PROJECT)/_version.py
	@echo '__datestamp__ = "'`date +%Y%m%d-%H%M`-`whoami`'"' >> $(PROJECT)/_version.py

push: tag
	git push -u github v$(VERSION)

tag:
	@if git rev-parse v$(VERSION) >/dev/null 2>&1; then \
		echo "Tag v$(VERSION) already exists. Skipping."; \
	else \
		git tag -a v$(VERSION) -m "Release v$(VERSION)"; \
		echo "Tag v$(VERSION) created locally."; \
	fi
