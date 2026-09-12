export ORGHOST = merlin
export COMHOST = copper
export ENGINEHOST = merlin
export STATICHOST = merlin
export PROJECT = bbsengine6
export OUTDIR = /srv/repo/$(PROJECT)/

export datestamp = $(shell date +%Y%m%d-%H%M)
export archivename = $(PROJECT)-$(datestamp)
export PROJECTRELEASEDIR = /srv/repo/$(PROJECT)/
export PROJECTBUILDDIR = /home/jam/projects/$(PROJECT)/releases/$(archivename)/
export RSYNC = rsync --chmod=Dg=rwxs,Fgu=rw,Fo=r --verbose \
	--exclude '*~' \
	--archive --times --no-group --update --backup --recursive \
	--human-readable --checksum --rsh=ssh \
	--delete-after --mkpath \
	--exclude 'captchas'

VERSION ?= 6

# Python package version. PY_VERSION is a dev-timestamp captured once at
# Makefile parse time; VERSION_PREFIX is the stable semver prefix. Combined
# they produce the wheel filename (and the __version__ written to
# py/src/$(PROJECT)/_version.py) so that the wheel produced by `build` and
# the wheel selected by the deploy-tui sub-make stay in lockstep.
#
# Resolution is per-SECOND, not per-minute. Two `deploy bbsengine6.tui`
# runs that landed in the same minute produced identical wheel filenames;
# pip then compared the freshly-built wheel's Version against the
# already-installed Version (same string) and reported "Requirement
# already satisfied", so site-packages stayed stale while new wheels piled
# up in /srv/repo/bbsengine6/. Second resolution collapses that 60-second
# collision window to a 1-second one, which is short enough that a
# back-to-back deploy is essentially never going to collide in practice.
PY_VERSION := $(shell date +%Y%m%d%H%M%S)
VERSION_PREFIX = 0.0.1.dev

# Set by `deploy --editable` (deploytool). Empty by default. Propagated
# to py/src/Makefile deploy-tui which switches between editable and
# wheel install.
DEPLOY_EDITABLE ?=

# Set by `deploy --upgrade` (deploytool). Default "1" (deploytool sets
# this when --upgrade is passed or no flag is given). Propagated to
# py/src/Makefile deploy-tui which splices `--upgrade` into every
# `pip install` line when this is "1". Empty means the prior no-op-
# if-version-matches behavior.
DEPLOY_UPGRADE ?=

# @since 20230414
export SCSSLOADPATH = --load-path $(PWD)/../zoidweb6/skin/scss/ \
                     --load-path $(PWD)/skin/scss/ \
                     --load-path $(PWD)/../zoid6/shared/skin/scss/
export SCSS = sass --line-numbers --stop-on-error --trace --style expanded --sourcemap=none $(SCSSLOADPATH)

export MARDOWNLIBSTAGE = /srv/www/
export MARKDOWNLIBPROD = merlin:/srv/www/

# @since 20230424
export ENGINESTAGE = /srv/www/bbsengine6/
export ENGINESTAGEDOCROOT = /srv/www/vhosts/zoidtechnologies.com/html/engine/

export ENGINEPROD = $(ENGINEHOST):/srv/www/bbsengine6/
export ENGINEPRODDOCROOT = $(ENGINEHOST):/srv/www/vhosts/zoidtechnologies.com/html/engine/

export WWWPROD = $(ORGHOST):/srv/www/vhosts/www.bbsengine.org/
export WWWPRODDOCROOT = $(WWWPROD)html/

export WWWSTAGE = /srv/www/vhosts/www.bbsengine.org/
export WWWSTAGEDOCROOT = $(WWWSTAGE)html/

# @since 2026-09-09 — single canonical install. The previous
# design fanned engine/*.php out to two prod docroots: this
# Makefile exported WWWENGINESTAGEDOCROOT/WWWENGINEPRODDOCROOT
# for the .org side, and engine/Makefile deploy-engine rsynced
# engine/*.php to both /srv/www/vhosts/zoidtechnologies.com/
# html/engine/ and /srv/www/vhosts/www.bbsengine.org/html/engine/.
# The .org vhost now serves the engine entry points at the
# docroot root (no /engine/ URL prefix; see www/org/htaccess-prod
# for the flattened /router.php, /serve-md.php, /join.php,
# /login.php, /logout.php rewrite targets), and the docroot's
# entry-point files are SYMLINKS to the canonical install at
# /srv/www/bbsengine6/ (already exported as ENGINESTAGE /
# ENGINEPROD above; the rsync target is the same path). The
# engine/Makefile deploy-engine now pushes the install to
# ENGINEHOST:$(ENGINESTAGE) (the canonical install) AND to
# $(ENGINEPRODDOCROOT) (the .com docroot copy). The .org
# docroot no longer receives a real-file engine/ tree from
# this Makefile; the docroot symlinks are created by
# www/org/Makefile stage. The WWWENGINESTAGEDOCROOT /
# WWWENGINEPRODDOCROOT pair is dropped.
#
# @since 2026-09-07 — handbook.php eradicated; no per-vhost
# PHP dispatcher under www/org/php/handbook.php; engine/ is the
# only .org-vhost PHP handler set.

export ORGPROD = $(ORGHOST):/srv/www/vhosts/www.bbsengine.org/
export ORGPRODDOCROOT = $(WWWPROD)html/

export ORGSTAGE = /srv/www/vhosts/www.bbsengine.org/
export ORGSTAGEDOCROOT = $(ORGSTAGE)html/

export STATICSTAGE = /srv/www/vhosts/static.zoidtechnologies.com/
export STATICSTAGEDOCROOT = $(STATICSTAGE)html/
export STATICPROD = $(ORGHOST):/srv/www/vhosts/static.zoidtechnologies.com/

all:

clean:
	-$(MAKE) -C php clean
	-$(MAKE) -C handbook clean
	-$(MAKE) -C py clean
	-$(MAKE) -C www clean
	-$(MAKE) -C skin clean
	-rm *~

release:
	echo "-=- making a new release of $(PROJECT) -=-";
	mkdir -p $(PROJECTBUILDDIR);
	$(MAKE) -C www release;
	$(MAKE) -C handbook release;
	git log > CHANGELOG.txt;
	$(installfile) README.txt INSTALL.txt RELEASENOTES.txt CHANGELOG.txt composer.json $(PROJECTBUILDDIR);
	$(RSYNC) --verbose --recursive php py $(PROJECTBUILDDIR);
	pushd releases;\
	tar jcf $(archivename).tar.bz2 $(archivename)/*;\
	tar zcf $(archivename).tgz $(archivename)/*;\
	zip -r $(archivename).zip $(archivename)/*;\
	mkdir -p $(PROJECTRELEASEDIR);\
	install --mode=0644 $(archivename).tar.bz2 $(archivename).tgz $(archivename).zip $(PROJECTRELEASEDIR);\
	install --mode=0644 $(archivename)/README.txt $(PROJECTRELEASEDIR);\
	install --mode=0644 $(archivename)/CHANGELOG.txt $(PROJECTRELEASEDIR);\
	popd;\
	echo "[DONE]"

apidocs:
	mkdir -p $(STAGEDOCROOT)$(VERSION)/apidocs/
	phpdoc run \
	--target $(STAGEDOCROOT)$(VERSION)/apidocs/ \
	--directory php \
	--extensions php \
	--title "$(PROJECT) apidocs" \
	--defaultpackagename "$(PROJECT)" \
	--sourcecode \
	--progressbar \
	--template responsive

handbook:
	-$(MAKE) -C handbook stage VERSION=$(VERSION)

prod:
##	$(MAKE) wwworg
	$(MAKE) engine
##	$(MAKE) handbook-prod
	$(MAKE) markdown

sql:
	tar zcvf $(PROJECT)-sql-$(datestamp).tar.gz sql/

markdown:
	$(RSYNC) --links --exclude 'vhosts' /srv/www/markdown $(MARKDOWNLIBPROD)


skin-prod:
	$(MAKE) -C skin stage
	$(RSYNC) $(ENGINESTAGE)skin/ $(ENGINEPROD)skin/

wwworg:
	$(MAKE) -C www org VERSION=$(VERSION)
	# @since 2026-09-09 — single canonical install. The
	# wwworg target first stages the .org docroot (including
	# the symlinks at html/router.php, html/serve-md.php, etc.
	# pointing at /srv/www/bbsengine6/), then engine-deploy-prod
	# ships the install to ENGINEHOST:/srv/www/bbsengine6/.
	# Both land in seconds and Apache isn't serving mid-deploy,
	# so the brief window where symlinks dangle is harmless.
	# @since 2026-09-07 — engine/ ships with wwworg because the
	# test (tests/test_handbook_6_returns_200.sh) probes
	# /handbook/<v>/... which requires engine/router.php and
	# engine/serve-md.php on the .org vhost. Previously engine/
	# shipped via engine-deploy-prod only; that required the
	# operator to run a separate target after wwworg. The two
	# are now combined so a single `make wwworg` brings up the
	# whole .org vhost end-to-end.
	$(MAKE) engine-deploy-prod VERSION=$(VERSION)
	# @since 2026-09-07 — php/ helpers (util.php, markdown.php,
	# blurb.php, engine.php) ship with wwworg because
	# engine/router.php requires them at /srv/www/bbsengine6/php/
	# (absolute paths, not include_path lookup). Without this
	# step the router's require_once chain raises
	# 'Failed opening required' and the request 500s with no
	# router-emitted body. Combined with engine-deploy-prod
	# above so wwworg is a single-shot end-to-end deploy for
	# the .org vhost.
	$(MAKE) php-deploy-prod

wwwcom:
	$(MAKE) -C www com

engine:
	$(MAKE) -C engine all
push:
	git push -u gitlab
	git push -u github

backup:
	rsync --recursive --verbose --exclude=.venv . /run/media/jam/AEAB-CF37/projects/$(PROJECT)/

log:
	git log --graph --pretty=format:"%h %ad %s%d [%an]%n%B" --date=short > LOG_FULL.md
	git log --pretty=format:"%ad|%h %s%d [%an]" --date=short | awk -F'|' '{if ($$1!=date) {print "## " $$1; date=$$1} print "  " $$2}' > LOG_SUMMARY.md

version:
	@echo '__version__ = "$(VERSION_PREFIX)$(PY_VERSION)"' > py/src/$(PROJECT)/_version.py
	@echo '__datestamp__ = "'`date +%Y%m%d-%H%M`-`whoami`'"' >> py/src/$(PROJECT)/_version.py

.PHONY: ensure-repo
ensure-repo:
	@stat -c '%G' /srv/repo 2>/dev/null | grep -qx repo || sudo chgrp repo /srv/repo
	@stat -c '%a' /srv/repo 2>/dev/null | grep -q '^2775$$' || sudo chmod 2775 /srv/repo

.PHONY: ensure-build-dir
ensure-build-dir: ensure-repo
	@mkdir -p /srv/repo/$(PROJECT)/
	@stat -c '%G' /srv/repo/$(PROJECT)/ 2>/dev/null | grep -qx repo || sudo chgrp repo /srv/repo/$(PROJECT)/
	@stat -c '%a' /srv/repo/$(PROJECT)/ 2>/dev/null | grep -q '^2775$$' || sudo chmod 2775 /srv/repo/$(PROJECT)/

# Make sure $(1)/build/ exists with mode 1775 (sticky + rwxrwxr-x) before
# invoking `python -m build`. Mode 1775 is intentional:
#   - sticky (t): only the owner of a file inside may delete/rename it,
#     so concurrent builds under a shared group can't stomp each other.
#   - setgid (s) is intentionally NOT set: setuptools' shutil.copystat
#     mirrors build/'s mode onto the freshly-created dist-info dir, and
#     a setgid'd dist-info EPERMs the subsequent bdist_wheel step in
#     SELinux-enforcing + NoNewPrivs containers (we lack CAP_FSETID).
#   - group write (g+w): any user in the build group can rebuild
#     without needing to chown.
# The chmod is expressed as `chmod g-s,+t` (drop the setgid bit the
# parent dir inherited onto the freshly-mkdir'd build/, then add the
# sticky bit). The numeric form `chmod 1775` is functionally equivalent
# but fails on BTRFS+SELinux setups where the parent directory's
# setgid bit blocks the owner from clearing it via the numeric mode
# (`chmod: Operation not permitted` on a dir the caller owns). The
# symbolic form works because the kernel only restricts numeric-mode
# changes that would remove the inherited setgid bit; `g-s` is
# permitted regardless of where the bit came from.
#
# If $(1)/build/ exists but is owned by a different user (e.g. left over
# from a prior build run as a different uid), rename it out of the way
# first. The parent dir is group-writable in this tree so the rename is
# permitted even when we don't own the build/ contents. Without this,
# the subsequent chmod fails with EPERM and the build aborts.
# Canonical version lives at bed/Makefile:165-189 (PREPARE_BUILD);
# all four projects (bed, bbsengine6, zoidoffice, casino) target this
# comment + macro pair so a fix in one place applies to all. See also
# zoid6/TODO.md "PREPARE_BUILD standardization (cross-project)".
#
# Note: py/ is currently mode 775 (no setgid), so this tree is
# "safe-by-accident" today -- py/build/ won't inherit setgid from
# py/, so the copystat cascade won't fire. The macro is added here
# anyway so a future chmod 2775 on py/ (e.g. matching the rest of
# the tree for consistency) doesn't silently regress the EPERM.
PREPARE_BUILD = \
	if [ -d $(1)/build ] && [ ! -O $(1)/build ]; then \
		mv $(1)/build $(1)/build.stale.$$ 2>/dev/null || true; \
	fi; \
	mkdir -p $(1)/build && chmod g-s,+t $(1)/build

build: clean version ensure-build-dir
	$(call PREPARE_BUILD,$(CURDIR)/py)
	cd py && python3 -m build --outdir $(OUTDIR)

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

wheel-release: build rename-sdist sign

.PHONY: handbook handbook-prod handbook-deploy-prod release sql prod www apidocs clean log engine prod skin-prod php-deploy php-deploy-prod engine-deploy-prod parsedown-deploy parsedown-deploy-prod deploy deploy-wwworg deploy-wwwcom deploy-handbook deploy-handbook-prod deploy-tui
.PHONY: version ensure-repo ensure-build-dir build rename-sdist sign wheel-release



php-deploy:
	$(RSYNC) php/ $(ENGINESTAGE)php/

php-deploy-prod: php-deploy
	$(RSYNC) $(ENGINESTAGE)php/ $(ENGINEPROD)php/

# @since 2026-09-06 — pushes engine/*.php to both prod docroots
# (zoidtechnologies.com + www.bbsengine.org) over ssh. Companion
# to php-deploy-prod; chained from deploy-handbook-prod so the
# engine tree lands alongside the handbook artifacts.
# engine/Makefile's deploy target ssh-pushes *.php straight to
# each prod target; --mkpath in $(RSYNC) creates the destination
# dir on the remote if it doesn't yet exist (relevant for .org,
# where /html/engine/ did not exist before this change).
engine-deploy-prod:
	$(MAKE) -C engine deploy

parsedown-deploy:
	mkdir -p /srv/www/markdown/
	$(RSYNC) vendor/erusev/parsedown/Parsedown.php /srv/www/markdown/
	$(RSYNC) vendor/erusev/parsedown-extra/ParsedownExtra.php /srv/www/markdown/

parsedown-deploy-prod: parsedown-deploy
	$(RSYNC) /srv/www/markdown/ merlin:/srv/www/markdown/

markdown-deploy:
	mkdir -p /srv/www/markdown/
	$(RSYNC) markdown/Markdown*.php /srv/www/markdown/

markdown-deploy-prod: parsedown-deploy
	$(RSYNC) /srv/www/markdown/ merlin:/srv/www/markdown/

deploy-wwworg: wwworg

deploy-wwwcom: wwwcom

handbook-prod:
	$(MAKE) -C handbook stage VERSION=$(VERSION)

# Local-stage then ssh-rsync to merlin. Mirrors the
# php-deploy/php-deploy-prod split: handbook-prod writes to
# $(WWWSTAGE)html/handbook/$(VERSION)/ locally; this target pushes
# that tree to $(WWWPROD)html/handbook/$(VERSION)/ on merlin over
# ssh (via $(RSYNC)'s --rsh=ssh). No fs bind-mount assumption.
handbook-deploy-prod: handbook-prod
	$(RSYNC) $(WWWSTAGE)html/handbook/$(VERSION)/ $(WWWPROD)html/handbook/$(VERSION)/

deploy-handbook: handbook-prod

# Ship the full handbook stack to merlin over ssh. Each prereq
# handles its own local-stage-then-ssh-rsync:
#
#   php-deploy-prod       -> /srv/www/bbsengine6/php/markdown.php
#   wwworg                -> /srv/www/vhosts/www.bbsengine.org/html/{config.php,index.php,...}
#                            + symlinks html/router.php,
#                              html/serve-md.php, html/join.php,
#                              html/login.php, html/logout.php ->
#                              /srv/www/bbsengine6/{router,serve-md,
#                              join,login,logout}.php
#                            (no /engine/ URL prefix; the
#                             .org vhost serves the engine entry
#                             points at the docroot root, see
#                             www/org/htaccess-prod)
#   handbook-deploy-prod  -> /srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/*.md
#   engine-deploy-prod    -> /srv/www/bbsengine6/{router,serve-md,join,login,logout}.php
#                            (canonical install) +
#                            /srv/www/vhosts/zoidtechnologies.com/html/engine/*.php
#                            (legacy /engine/... copy on the .com vhost)
#                            Note: engine-deploy-prod is NOT a
#                            direct prereq of deploy-handbook-prod
#                            because wwworg already chains it
#                            (see the wwworg target above), so
#                            it would double-run if listed here.
#
# All four use $(RSYNC) (which carries --rsh=ssh), so this runs
# cleanly from a build host with no fs bind-mount between the build
# host and merlin. wwworg pushes its whole staged docroot minus
# the four legacy handbook artifact excludes (see www/Makefile:50-56)
# to merlin via ORGPROD. The engine/ and html/engine/ excludes that
# were previously in the org rsync are gone (this commit) because
# the .org docroot no longer has an html/engine/ subdir; the entry
# points are symlinks at the docroot root.
#
# After this runs, reload php-fpm on merlin so opcache picks up the
# new files immediately:
#   sudo systemctl reload php-fpm
deploy-handbook-prod: php-deploy-prod wwworg handbook-deploy-prod
	@echo "Handbook stack deployed: /srv/www/bbsengine6/{router,serve-md,join,login,logout}.php (canonical install) + php/markdown.php + html/{config.php,router.php,serve-md.php,join.php,login.php,logout.php,.htaccess} + html/handbook/$(VERSION)/"
	@echo "Reminder on merlin: sudo systemctl reload php-fpm"

deploy:
	$(MAKE) -C engine stage
	$(MAKE) -C engine deploy-engine
	$(MAKE) -C skin stage
	$(MAKE) php-deploy
	mkdir -p $(ENGINESTAGE)smarty/
	$(RSYNC) smarty/*.php $(ENGINESTAGE)smarty/
	# @since 2026-09-09 — drop --delete-after from this rsync.
	# The previous design (pre-refactor) had engine/*.php
	# living only at the docroots, not at
	# /srv/www/bbsengine6/ on merlin, so the rsync from the
	# build host's $(ENGINESTAGE) (containing php/, skin/,
	# smarty/) to merlin's $(ENGINEPROD) was safe with
	# --delete-after: anything merlin had that the source
	# didn't was orphan cruft. The single-install refactor
	# (this commit series) makes /srv/www/bbsengine6/ the
	# CANONICAL install of engine/*.php (shipped by
	# `engine deploy-engine` above), so this rsync would
	# then delete those engine/*.php files because they
	# aren't in the build host's local stage (the build
	# host's $(ENGINESTAGE) is read-only and never had
	# engine/*.php). Without --delete-after, the rsync
	# still pushes new/updated php/, skin/, smarty/ files
	# but preserves engine/*.php on merlin. The
	# canonical-install path (/srv/www/bbsengine6/) now
	# carries files from two sources: the build host
	# (php/, skin/, smarty/) and the engine/Makefile
	# deploy-engine (engine/*.php), and the rsync that
	# pushes the former must not delete the latter. The
	# $(RSYNC) macro carries --delete-after; we override
	# it with --no-delete-after on this specific line so
	# engine/*.php on merlin is preserved.
	$(RSYNC) --no-delete-after $(ENGINESTAGE) $(ENGINEPROD)

deploy-tui: build
	$(MAKE) -C py/src deploy-tui DEPLOY_EDITABLE=$(DEPLOY_EDITABLE) DEPLOY_UPGRADE=$(DEPLOY_UPGRADE) VERSION=$(PY_VERSION) VERSION_PREFIX=$(VERSION_PREFIX)
