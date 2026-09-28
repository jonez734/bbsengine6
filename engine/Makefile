# Per-vhost /engine/ install. Caller can override two ways:
#   1. inline (existing): make -C engine stage \
#                            ENGINESTAGEDOCROOT=/srv/www/.../html/engine/
#   2. env var (new): ENGINE_DOCROOT=/srv/www/.../html/engine/ make -C engine stage
#                     (deploytool plumbs ENGINE_DOCROOT into the make env,
#                      see src/deploytool/lib.py:run_make_deploy)
# Inline always wins (make: command line > environment > file). When neither
# is set, falls through to the zoidtechnologies.com default -- the historical
# behavior for engine-stage / engine-prod.
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
