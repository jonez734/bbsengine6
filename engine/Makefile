# Per-vhost /engine/ install. Caller can override two ways:
#   1. inline (existing): make -C engine stage \
#                            ENGINESTAGEDOCROOT=/srv/www/.../html/engine/
#   2. env var (new): ENGINE_DOCROOT=/srv/www/.../html/engine/ make -C engine stage
#                     (deploytool plumbs ENGINE_DOCROOT into the make env,
#                      see src/deploytool/lib.py:run_make_deploy)
# Inline always wins (make: command line > environment > file). When neither
# is set, falls through to the zoidtechnologies.com default -- the historical
# behavior for engine-stage / engine-prod.
#
# Engine entry-points are staged via $(wildcard *.php). Any *.php file
# dropped into this directory is automatically picked up by `stage:`
# and pushed to $(ENGINESTAGEDOCROOT) on $(ENGINEHOST). There is no
# allow-list to update when adding a new engine helper -- just add the
# .php file. Files using other extensions (.inc, no extension, etc.)
# are NOT staged. If you need a non-.php engine file, either rename
# it or add an explicit entry to ENGINE_PHP below the wildcard.
#
# Engine entry-points currently in this directory (verified by
# deploytool/tests/test_deploy_bbsengine6_engine.py:
# test_engine_vhostconfig_php_exists_with_resolver + the wildcard
# dry-run layer of test_engine_makefile_wildcard_includes_vhostconfig):
#   router.php, serve-tmpl.php, vhostconfig.php, join.php,
#   login.php, logout.php, direct.php, standalone.php.
ENGINE_DOCROOT     ?= /srv/www/vhosts/zoidtechnologies.com/html/engine/
ENGINESTAGEDOCROOT ?= $(ENGINE_DOCROOT)
ENGINEPRODDOCROOT  ?= $(ENGINEHOST):$(ENGINESTAGEDOCROOT)

all:

clean:

ENGINE_PHP = $(wildcard *.php)

stage:
	mkdir -p $(ENGINESTAGEDOCROOT)
	$(RSYNC) $(ENGINE_PHP) $(ENGINESTAGEDOCROOT)

deploy-engine: stage
	@echo "engine-deploy-prod -> $(ENGINEPRODDOCROOT)"
	$(RSYNC) $(ENGINESTAGEDOCROOT) $(ENGINEPRODDOCROOT)

deploy: stage
	$(RSYNC) $(ENGINESTAGEDOCROOT) $(ENGINEPRODDOCROOT)

.PHONY: all clean stage deploy deploy-engine
