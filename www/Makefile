all:

VERSION ?= 6

clean:
	-rm *~
	$(MAKE) -C skin clean
	$(MAKE) -C php clean
	$(MAKE) -C smarty clean

org:
	$(MAKE) -C org stage
	$(MAKE) -C ../handbook stage VERSION=$(VERSION)
	$(RSYNC) \
		--exclude "html/handbook/bbsengine-handbook.conf" \
		--exclude "html/handbook/handbook-wsgi.conf" \
		--exclude "html/handbook/modules.adoc" \
		--exclude "html/handbook/modules.html" \
		--chmod=Dg+rwxs $(ORGSTAGE) $(ORGPROD)
	# Force templates_c/ to mode 2775 on the receiver.
	# rsync's --chmod (whether = or +) only applies when the dir
	# is CREATED on the receiver; if it already existed, rsync's
	# --archive --times preserves the existing perms instead of
	# chmod'ing them. install -d is idempotent: mkdir -p + chmod
	# in one shot, no-op if the mode already matches. Without
	# this step the web user (cyrus) cannot write compiled
	# templates here and Smarty fatals. Mirrors the same fix in
	# www/org/Makefile's prod target so both entry points
	# (`make -C www org` and `make -C www/org prod`) leave
	# templates_c/ correctly chmod'd.
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

remove-legacy-handbook:
	ssh $(ORGHOST) 'cd /srv/www/vhosts/www.bbsengine.org/html/handbook/ && \
		rm -f bbsengine-handbook.conf handbook-wsgi.conf modules.adoc modules.html && \
		echo "removed legacy handbook artifacts" || echo "removal failed (rc=$$?)"'

com:
	$(MAKE) -C com stage
	$(RSYNC) --exclude "releases" --exclude "templates_c" --chmod=Dg+rwxs $(COMSTAGE) $(COMPROD)

.PHONY: org com remove-legacy-handbook
