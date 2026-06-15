# engine/Makefile
# Deployment for /engine/ web-accessible PHP files
# @since 2026-06-15

# Uses exported variables from parent Makefile:
# ENGINESTAGE, ENGINESTAGEDOCROOT, ENGINEHOST, ENGINEPROD, ENGINEPRODDOCROOT, RSYNC

all:

clean:

stage:
	mkdir -p $(ENGINESTAGEDOCROOT)

deploy:
	$(RSYNC) $(ENGINESTAGEDOCROOT) $(ENGINEPRODDOCROOT)

deploy-engine:
	$(RSYNC) *.php $(ENGINESTAGEDOCROOT)

all: stage deploy deploy-engine

.PHONY: all clean stage deploy deploy-engine
