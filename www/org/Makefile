all:

clean:
	-rm *~

stage:
	$(MAKE) -C php stage
	$(MAKE) -C skin stage
	$(MAKE) -C smarty stage
	$(MAKE) -C js stage

	$(RSYNC) config-prod.php $(ORGSTAGEDOCROOT)config.php
	-$(RSYNC) htpasswd-prod $(ORGSTAGEDOCROOT).htpasswd
	$(RSYNC) htaccess-prod $(ORGSTAGEDOCROOT).htaccess

prod: stage
	$(RSYNC) $(ORGSTAGE) $(ORGPROD)
	# Force templates_c/ to mode 2775 on the receiver.
	# rsync's --chmod=Dg=rwxs only applies when the dir is CREATED
	# on the receiver; if it already existed (e.g. from an older
	# deploy that landed the dir at mode 2755 before --chmod was
	# reliably honored), rsync's --archive --times preserves the
	# existing perms instead of chmod'ing them. install -d is
	# idempotent: it mkdir -p + chmod in one shot, no-op if the
	# mode already matches. Without this step the web user
	# (cyrus) cannot write compiled templates here and Smarty
	# fatals with 'unable to create directory'.
	#
	# @since 2026-09-26 — the previous version passed `-g www`
	# explicitly to chgrp the receiver dir. That hardcoded the
	# wrong group on merlin, where the deploy uses `www-data`
	# (minotaur uses `www`; see TODO-www-deploys.md). Rely on
	# the parent dir's setgid bit (the staging tree is
	# `drwxrwsr-x jam www` on minotaur / `drwxrwsr-x jam
	# www-data` on merlin) to set the new dir's group via
	# inheritance — that's the same mechanism `--no-group` uses
	# on rsync, per TODO-www-deploys.md "Step 2: --no-group".
	ssh $(ORGHOST) install -d -m 2775 $(ORGSTAGE)templates_c

.PHONY: stage
