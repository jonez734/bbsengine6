# engine/Makefile
# Deployment for /engine/ web-accessible PHP files.
# @since 2026-06-15
#
# @since 2026-09-06 — fan-out to multiple docroots. The original
# single-docroot design shipped engine/*.php only to the
# zoidtechnologies.com vhost. handbook.php on the www.bbsengine.org
# vhost also requires engine/router.php via a relative path
# (__DIR__/../../engine/router.php), so the engine tree must exist
# at the .org docroot too. WWWENGINESTAGEDOCROOT /
# WWWENGINEPRODDOCROOT mirror the existing ENGINESTAGE / ENGINEPROD
# pair. stage mkdir-p's local staging roots (no ssh); deploy-engine
# ssh-pushes *.php to each prod docroot.

# Uses exported variables from parent Makefile:
# ENGINESTAGE, ENGINESTAGEDOCROOT, ENGINEHOST, ENGINEPROD, ENGINEPRODDOCROOT, RSYNC,
# WWWSTAGE, WWWPROD, WWWENGINESTAGEDOCROOT, WWWENGINEPRODDOCROOT, ORGHOST.

ENGINESTAGEDOCROOT ?= /srv/www/vhosts/zoidtechnologies.com/html/engine/
WWWENGINESTAGEDOCROOT ?= /srv/www/vhosts/www.bbsengine.org/html/engine/
ENGINEPRODDOCROOT ?= $(ENGINEHOST):/srv/www/vhosts/zoidtechnologies.com/html/engine/
WWWENGINEPRODDOCROOT ?= $(ORGHOST):/srv/www/vhosts/www.bbsengine.org/html/engine/

all:

clean:

# Local-only stage: mkdir -p both staging docroots. No ssh.
# Errors propagate — a read-only mount on the build host will
# fail stage loudly rather than silently dropping the push.
# (Run from a host where /srv/www/vhosts/{zoidtechnologies.com,
# www.bbsengine.org}/html/ is writable; deploy-engine then
# ssh-pushes *.php to each prod docroot.)
stage:
	mkdir -p $(ENGINESTAGEDOCROOT)
	mkdir -p $(WWWENGINESTAGEDOCROOT)

# ssh-push engine/*.php to each prod docroot. $(RSYNC) carries
# --mkpath, so the destination dir is created on the remote if it
# doesn't exist yet (relevant for .org, where /html/engine/ did not
# exist before this change). Source list is expanded by make's
# $(wildcard) so the shell doesn't try to execute the bare glob.
ENGINE_PHP = $(wildcard *.php)

deploy-engine:
	$(RSYNC) $(ENGINE_PHP) $(ENGINEPRODDOCROOT)
	$(RSYNC) $(ENGINE_PHP) $(WWWENGINEPRODDOCROOT)

# Retained for compatibility with the top-level `deploy` target,
# which calls `engine stage` and `engine deploy-engine` separately.
# Same ssh-push as deploy-engine; engine/*.php does not pass through
# local staging because both docroots are read-only on the build host.
deploy:
	$(RSYNC) $(ENGINE_PHP) $(ENGINEPRODDOCROOT)
	$(RSYNC) $(ENGINE_PHP) $(WWWENGINEPRODDOCROOT)

.PHONY: all clean stage deploy deploy-engine
