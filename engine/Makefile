# Per-vhost install: caller passes ENGINESTAGEDOCROOT/ENGINEPRODDOCROOT.
ENGINESTAGEDOCROOT ?= /srv/www/vhosts/zoidtechnologies.com/html/engine/
ENGINEPRODDOCROOT  ?= $(ENGINEHOST):/srv/www/vhosts/zoidtechnologies.com/html/engine/

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
