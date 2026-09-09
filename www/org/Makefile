all:

clean:
	-rm *~

stage:
	$(MAKE) -C php stage
	$(MAKE) -C skin stage
	$(MAKE) -C smarty stage
	$(MAKE) -C js stage

	mkdir -p $(ORGSTAGE)templates_c/
	touch $(ORGSTAGE)templates_c/.gitkeep
	$(RSYNC) config-prod.php $(ORGSTAGEDOCROOT)config.php
	-$(RSYNC) htpasswd-prod $(ORGSTAGEDOCROOT).htpasswd
	$(RSYNC) htaccess-prod $(ORGSTAGEDOCROOT).htaccess

	# @since 2026-09-09 — single-install symlinks. The canonical
	# install of engine/{router,join,login,logout,serve-md}.php
	# lives at /srv/www/bbsengine6/ on merlin (shipped via
	# engine/Makefile deploy-engine, which deploy-handbook-prod
	# runs before wwworg so the install lands first). This stage
	# step creates symlinks at the .org docroot pointing at the
	# canonical install, so the .org vhost serves /router.php,
	# /serve-md.php, /join.php, /login.php, /logout.php directly
	# (no /engine/ URL prefix; see htaccess-prod). The symlinks
	# are created on the build host in the local stage so
	# $(RSYNC) (which carries --archive, including -l) carries
	# them as symlinks to the prod docroot. -f overwrites
	# existing symlinks on re-runs; -n (no-dereference) is a
	# safety net if the target is accidentally a real file. The
	# build host's local stage may have broken symlinks (if
	# /srv/www/bbsengine6/ doesn't exist locally); that's fine
	# because rsync carries the symlink itself, not the target,
	# and the prod host is where the symlink resolves.
	ln -sfn /srv/www/bbsengine6/router.php   $(ORGSTAGEDOCROOT)router.php
	ln -sfn /srv/www/bbsengine6/serve-md.php $(ORGSTAGEDOCROOT)serve-md.php
	ln -sfn /srv/www/bbsengine6/join.php     $(ORGSTAGEDOCROOT)join.php
	ln -sfn /srv/www/bbsengine6/login.php    $(ORGSTAGEDOCROOT)login.php
	ln -sfn /srv/www/bbsengine6/logout.php   $(ORGSTAGEDOCROOT)logout.php

prod: stage
	$(RSYNC) $(ORGSTAGE) $(ORGHOST):$(ORGPROD)

.PHONY: stage
