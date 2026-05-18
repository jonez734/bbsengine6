PROJECT = bbsengine6
OUTDIR = dist/ # /srv/repo/$(PROJECT)/
VERSION = $(shell date +%Y%m%d%H%M)

PYTHON = python3

.PHONY: build version
.PHONY: clean build rename-sdist sign release all

build: version
	VERSION=$(VERSION) $(PYTHON) -m build --outdir $(OUTDIR)

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

release: clean build rename-sdist sign

all:

clean:
	-rm *~
#	$(MAKE) -C con clean
	$(MAKE) -C $(PROJECT) clean
	$(MAKE) -C tk clean

sdist:
	$(PYTHON) -m setup sdist --dist-dir /srv/repo/$(PROJECT)/

version:
#	@echo '__version__ = "'`git log -1 --format='%H' | cut -c 1-16`'"' > bbsengine6/_version.py
	@echo '__version__ = "0.0.1.dev$(VERSION)"' > bbsengine6/_version.py
	@echo '__datestamp__ = "'`date +%Y%m%d-%H%M`-`whoami`'"' >> bbsengine6/_version.py

push: tag
#	git push -u gitlab v$(VERSION)
	git push -u github v$(VERSION)

tag:
	@if git rev-parse v$(VERSION) >/dev/null 2>&1; then \
		echo "Tag v$(VERSION) already exists. Skipping."; \
	else \
		git tag -a v$(VERSION) -m "Release v$(VERSION)"; \
		echo "Tag v$(VERSION) created locally."; \
	fi

