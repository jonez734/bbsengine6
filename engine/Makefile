# engine/Makefile
# Deployment for /engine/ web-accessible PHP files.
# @since 2026-06-15
#
# @since 2026-09-06 — fan-out to multiple docroots. The original
# single-docroot design shipped engine/*.php only to the
# zoidtechnologies.com vhost. The www.bbsengine.org vhost's
# htaccess-prod rewrites its /handbook/<v>/... URIs to
# /engine/router.php and /engine/serve-md.php, so the engine
# tree must exist at the .org docroot too.
# WWWENGINESTAGEDOCROOT / WWWENGINEPRODDOCROOT mirror the
# existing ENGINESTAGE / ENGINEPROD pair. stage mkdir-p's local
# staging roots (no ssh); deploy-engine ssh-pushes *.php to
# each prod docroot.
#
# @since 2026-09-07 — handbook.php eradicated. The old
# .org-vhost entry point (www/org/php/handbook.php) is gone;
# engine/ is the only .org-vhost PHP handler set.
#
# @since 2026-09-09 — single canonical install. The previous
# design fanned engine/*.php out to two prod docroots:
# zoidtechnologies.com/html/engine/ and www.bbsengine.org/html/engine/.
# The www.bbsengine.org vhost now serves the engine entry points
# at the docroot root (no /engine/ URL prefix; see www/org/htaccess-prod
# for the flattened /router.php, /serve-md.php, /join.php, /login.php,
# /logout.php rewrite targets), and the docroot's entry-point files
# are SYMLINKS to the canonical install at /srv/www/bbsengine6/.
# This Makefile now ships one install to that canonical path; the
# zoidtechnologies.com docroot still receives a real-file copy
# under its /engine/ subdir for backwards compatibility with
# existing /engine/... URLs on that vhost. The www.bbsengine.org
# docroot no longer receives a real-file copy from this Makefile;
# the symlinks are created by www/org/Makefile stage.

# Uses exported variables from parent Makefile:
# ENGINESTAGE, ENGINESTAGEDOCROOT, ENGINEHOST, ENGINEPROD, ENGINEPRODDOCROOT, RSYNC.

# Canonical install: a single copy of engine/*.php on merlin at a
# stable absolute path. The .org docroot's symlinks point here; the
# .com docroot's /engine/ tree is a separate copy. Symlink target
# path stability matters: if /srv/www/bbsengine6/ ever moves on
# merlin, the .org symlinks break. Keep the install path stable.
INSTALL_DIR ?= /srv/www/bbsengine6/

ENGINESTAGEDOCROOT ?= /srv/www/vhosts/zoidtechnologies.com/html/engine/
ENGINEPRODDOCROOT ?= $(ENGINEHOST):/srv/www/vhosts/zoidtechnologies.com/html/engine/

all:

clean:

# Local-only stage: mkdir -p the .com staging docroot. No ssh.
# Errors propagate — a read-only mount on the build host will
# fail stage loudly rather than silently dropping the push.
# (Run from a host where /srv/www/vhosts/zoidtechnologies.com/
# html/ is writable; deploy-engine then ssh-pushes *.php to
# the .com prod docroot and to the canonical install path.)
# The .org staging root is managed by www/org/Makefile, which
# creates the docroot symlinks; this Makefile no longer
# touches /srv/www/vhosts/www.bbsengine.org/html/engine/.
stage:
	mkdir -p $(ENGINESTAGEDOCROOT)

# ssh-push engine/*.php to the canonical install dir AND to the
# .com prod docroot. $(RSYNC) carries --mkpath, so the destination
# dir is created on the remote if it doesn't exist yet. Source
# list is expanded by make's $(wildcard) so the shell doesn't try
# to execute the bare glob.
# @since 2026-09-06 — also ship .htaccess. make's $(wildcard) skips
# dotfiles by default, so it's listed explicitly. The .htaccess
# carries the RewriteEngine + RewriteRule plumbing that the .org
# vhost's engine/ tree relied on. With the canonical-install model
# (this commit), the .htaccess in the install dir is only used by
# the .com vhost's /engine/ subdir; the .org vhost's symlinks do
# not need a sibling .htaccess (the vhost's own .htaccess handles
# routing into /router.php, /serve-md.php, etc.).
# If a future dotfile appears under engine/, add it here.
ENGINE_PHP = .htaccess $(wildcard *.php)

deploy-engine:
	$(RSYNC) $(ENGINE_PHP) $(ENGINEHOST):$(INSTALL_DIR)
	$(RSYNC) $(ENGINE_PHP) $(ENGINEPRODDOCROOT)

# Retained for compatibility with the top-level `deploy` target,
# which calls `engine stage` and `engine deploy-engine` separately.
# Same ssh-push as deploy-engine; engine/*.php does not pass through
# local staging because both docroots are read-only on the build host.
deploy:
	$(RSYNC) $(ENGINE_PHP) $(ENGINEHOST):$(INSTALL_DIR)
	$(RSYNC) $(ENGINE_PHP) $(ENGINEPRODDOCROOT)

.PHONY: all clean stage deploy deploy-engine
