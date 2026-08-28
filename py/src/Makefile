PROJECT = bbsengine6
OUTDIR = /srv/repo/$(PROJECT)/
# Allow VERSION/VERSION_PREFIX to be passed in by the parent Makefile
# (see ../Makefile deploy-tui target). Fall back to a fresh timestamp
# only when invoked standalone, so the wheel produced by `make build`
# in the parent and the wheel selected here stay in lockstep.
#
# Per-second resolution (matching ../Makefile PY_VERSION) so two
# back-to-back `deploy bbsengine6.tui` runs in the same minute don't
# produce identical wheel filenames — pip would otherwise compare the
# freshly-built wheel's Version against the installed Version (same
# string) and report "Requirement already satisfied".
VERSION ?= $(shell date +%Y%m%d%H%M%S)
export VERSION_PREFIX ?= 0.0.1.dev

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

# DEPLOY_WITH_DEPS is set by `deploytool --with-deps`. Empty by
# default. When set to 1, `precheck-editable` switches from hard-fail
# to warn-and-proceed for the editable-in-venv case: a `--with-deps`
# invocation semantically promises "rebuild the venv, no questions
# asked", so blocking on an editable install that the operator may
# have placed there on purpose is wrong-headed. The `verify-install`
# macro that runs after the wheel install provides the actual
# correctness check — if the editable .pth finder shadows the wheel
# install, `pip show` will disagree with the wheel's METADATA and the
# deploy aborts with a precise diagnosis naming the editable-install
# cause.
#
# Without `--with-deps`, the precheck still hard-fails: most operators
# are not consciously managing a mixed editable/wheel state and
# silently no-op'ing is the wrong default.
DEPLOY_WITH_DEPS ?=

# Verifies the wheel just installed is the one `pip show` reports
# as installed. Catches the silent-no-op case where `pip install
# <wheel>` exits 0 without actually replacing an existing install
# (orphaned .dist-info, permission-denied mid-install, an editable
# install of the same distribution name in the same venv, etc.). On
# mismatch, prints the verbatim `pip show` output (stdout) and aborts
# the deploy with a summary (stderr).
#
# Three values are compared:
#   - filename:  regex-extracted from $$WHEEL (recipe time)
#   - METADATA:  Version: line from the wheel's METADATA (unzip -p)
#   - pip show:  Version: line from `pip show $(PROJECT)` post-install
#
# All three must agree. Used by `deploy-tui` in the non-editable
# branch. Editable installs (DEPLOY_EDITABLE=1) skip this — `pip
# show` for an editable install reports the *source-tree* version,
# not a wheel version, and the comparison semantics differ.
#
# Takes the wheel path as $$WHEEL (recipe-scoped), not as $(WHEEL)
# (Makefile-evaluated), because the wheel filename embeds a
# timestamp that is only known after `ls -t $(OUTDIR)/...` runs at
# recipe time. Same shape as casino/Makefile:verify-install;
# ported from zoidoffice/src/Makefile VERIFY_INSTALL.
define verify-install
	EXPECTED_FROM_FILENAME=$$(basename "$$WHEEL" | sed -E 's/^$(PROJECT)-(.+)-py3-none-any\.whl$$/\1/'); \
	EXPECTED_FROM_METADATA=$$(unzip -p "$$WHEEL" '*/METADATA' 2>/dev/null | awk -F': ' '/^Version: / {print $$2; exit}'); \
	echo "=== verify-install ($(PROJECT)) ==="; \
	echo "  wheel filename Version: $$EXPECTED_FROM_FILENAME"; \
	echo "  wheel METADATA Version: $$EXPECTED_FROM_METADATA"; \
	echo "--- pip show $(PROJECT) ---"; \
	SHOW_OUTPUT=$$($(PIP) show $(PROJECT) 2>&1); \
	SHOW_RC=$$?; \
	echo "$$SHOW_OUTPUT"; \
	echo "(pip show exited $$SHOW_RC)"; \
	echo "--- end pip show ---"; \
	INSTALLED=$$(echo "$$SHOW_OUTPUT" | awk '/^Version: / {print $$2; exit}'); \
	if [ "$$INSTALLED" != "$$EXPECTED_FROM_FILENAME" ] \
		|| [ "$$INSTALLED" != "$$EXPECTED_FROM_METADATA" ]; then \
		echo "verify-install FAILED: $$WHEEL was installed but pip show does not agree" >&2; \
		echo "  expected filename:  $$EXPECTED_FROM_FILENAME" >&2; \
		echo "  expected METADATA:  $$EXPECTED_FROM_METADATA" >&2; \
		echo "  pip show Version:   $$INSTALLED" >&2; \
		exit 1; \
	fi; \
	echo "verify-install OK: pip show reports $$INSTALLED"
endef

# Hard-fail precondition for `deploy-tui` (non-editable branch).
#
# PEP 660 / setuptools' `__editable___<pkg>_*_finder` `.pth` hook
# makes an editable install of `<pkg>` in a venv mutually exclusive
# with a wheel install of the same `<pkg>` into the same venv:
# the editable hook wins on `import`, so a subsequent `pip install
# /srv/repo/.../<pkg>-*.whl` writes a fresh dist-info but is shadowed
# on import, and the operator's running TUI keeps seeing the source
# tree. Wheels accumulate in OUTDIR; `pip show` keeps reporting the
# source-tree version. There is no in-place fix — the two install
# modes can't coexist in one venv.
#
# `precheck-editable` runs at the top of the non-editable branch of
# `deploy-tui`. It deliberately does NOT call `pip uninstall` itself:
# that would lose any post-install hooks, race with concurrently-
# installed editable installs in the same venv, and undermine the
# operator's conscious choice to be in editable mode. The error is
# a precondition report, not a fixup — same shape as the in-tree
# PREPARE_BUILD macro in bbsengine6/Makefile (which reports a
# foreign-owned build/, it doesn't chown on the operator's behalf).
#
# Behavior branches on DEPLOY_WITH_DEPS (set by deploytool when
# `--with-deps` is passed; empty by default):
#
#   - DEPLOY_WITH_DEPS unset (default): hard fail with the two clean
#     remedies. Most operators are not consciously managing a mixed
#     editable/wheel state and silently no-op'ing is the wrong
#     default.
#   - DEPLOY_WITH_DEPS=1: warn-and-proceed. `--with-deps` semantically
#     promises "rebuild the venv, no questions asked", so blocking
#     on an editable install the operator may have placed there on
#     purpose is wrong-headed. The post-install `verify-install`
#     macro then becomes the actual correctness check — if the
#     editable .pth finder shadows the wheel install, `pip show`
#     will disagree with the wheel's METADATA and the deploy aborts
#     with a precise diagnosis naming the editable-install cause.
#
# Implemented as a recipe-time macro (not a `.PHONY` target) so the
# check only fires on the non-editable branch — the editable branch
# legitimately has an editable install and must not be flagged.
define precheck-editable
	SHOW=$$($(PIP) show $(PROJECT) 2>/dev/null); \
	if echo "$$SHOW" | grep -q '^Editable project location:'; then \
		EDITABLE_SRC=$$(echo "$$SHOW" | awk -F': ' '/^Editable project location: / {print $$2; exit}'); \
		if [ "$(DEPLOY_WITH_DEPS)" = "1" ]; then \
			echo "deploy-tui: WARNING: $(PROJECT) is installed editable in the active venv" >&2; \
			echo "  editable source: $$EDITABLE_SRC" >&2; \
			echo >&2; \
			echo "DEPLOY_WITH_DEPS=1 is set (deploy --with-deps), so precheck-editable is" >&2; \
			echo "proceeding with the wheel install. If the editable .pth finder shadows it" >&2; \
			echo "(the common case), verify-install will abort with a precise diagnosis." >&2; \
			echo "To switch permanently, run one of:" >&2; \
			echo >&2; \
			echo "  - Stay in editable mode:  deploy --editable bbsengine6.tui" >&2; \
			echo "  - Force a wheel rebuild:  pip uninstall bbsengine6 && deploy bbsengine6.tui" >&2; \
			echo >&2; \
		else \
			echo "deploy-tui: $(PROJECT) is installed editable in the active venv" >&2; \
			echo "  editable source: $$EDITABLE_SRC" >&2; \
			echo >&2; \
			echo "Editable and wheel installs of the same distribution name can't coexist in" >&2; \
			echo "one venv (the editable .pth finder shadows subsequent wheel installs), so" >&2; \
			echo "this Makefile refuses to silently no-op. Pick one:" >&2; \
			echo >&2; \
			echo "  1) Stay in editable mode: deploy --editable bbsengine6.tui" >&2; \
			echo "  2) Switch to wheel mode: pip uninstall bbsengine6 && deploy bbsengine6.tui" >&2; \
			echo "  3) Override for this run only: deploy --with-deps bbsengine6.tui" >&2; \
			echo >&2; \
			echo "(The Makefile intentionally doesn't 'fix' this for you — see" >&2; \
			echo " py/src/Makefile precheck-editable.)" >&2; \
			exit 1; \
		fi; \
	fi
endef

install: version
	cd .. && $(PIP) install --no-cache-dir -e .

deploy-tui:
ifeq ($(DEPLOY_EDITABLE),1)
	cd .. && $(PIP) install --no-cache-dir -e .
else
	@$(precheck-editable)
	@WHEEL=$(OUTDIR)$(PROJECT)-$(VERSION_PREFIX)$(VERSION)-py3-none-any.whl; \
	if [ ! -f "$$WHEEL" ]; then \
		WHEEL=$$(ls -t $(OUTDIR)$(PROJECT)-*.whl 2>/dev/null | head -1); \
		if [ -z "$$WHEEL" ]; then \
			echo "expected wheel $(OUTDIR)$(PROJECT)-$(VERSION_PREFIX)$(VERSION)-py3-none-any.whl not found, and no fallback wheel in $(OUTDIR)" >&2; \
			exit 1; \
		fi; \
		echo "explicit wheel missing; falling back to newest in OUTDIR: $$WHEEL" >&2; \
	fi; \
	echo "WHEEL=$$WHEEL"; \
	$(PIP) install --no-cache-dir "$$WHEEL"; \
	$(verify-install)
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
