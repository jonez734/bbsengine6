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

	# @since 2026-09-09 — single-install symlinks (PREVIOUSLY
	# created here via `ln -sfn`; REMOVED in this commit). The
	# local stage at /srv/www/vhosts/www.bbsengine.org/html/ is
	# mounted read-only on the build host (owned jam:www mode
	# 755, per the comment in ../../Makefile:19-29), so
	# `ln -sfn` fails with EROFS here. The rsync lines above
	# silently no-op for the same reason. The deploy model is:
	# `make -C www/org prod` rsyncs the build-host stage to
	# merlin via ssh; for the symlinks we cannot stage them
	# locally, so the new `prod-symlinks` target ssh-runs
	# `ln -sfn` directly on merlin, creating the symlinks in
	# the writable prod docroot. `prod` chains `stage` then
	# `prod-symlinks` so a single `make wwworg` brings up the
	# .org vhost end-to-end.

prod: stage prod-symlinks
	$(RSYNC) $(ORGSTAGE) $(ORGHOST):$(ORGPROD)

# @since 2026-09-09 — create the single-install symlinks on
# merlin's .org docroot. The canonical install at
# /srv/www/bbsengine6/ on merlin is shipped by
# engine/Makefile deploy-engine, which wwworg chains
# (see ../../Makefile:185) so the install lands before these
# symlinks. `ln -sfn -f` overwrites existing symlinks on
# re-runs (idempotent). Each symlink resolves a docroot
# entry-point file (/router.php, /serve-md.php, /join.php,
# /login.php, /logout.php) to the canonical install, so the
# .org vhost serves them with no /engine/ URL prefix (see
# htaccess-prod). Mirrors the ssh-based pattern from
# ../../www/Makefile:remove-legacy-handbook (ssh $(ORGHOST)
# '...') so the deployment is unambiguous and not dependent
# on rsync's symlink-resolution behavior. Uses
# $(ORGSTAGEDOCROOT) (just the path, no ssh-prefix) for the
# remote `cd` target; $(ORGPRODDOCROOT) carries the
# `merlin:` ssh-prefix from $(WWWPROD) and would confuse
# the remote shell.
prod-symlinks:
	ssh $(ORGHOST) 'cd $(ORGSTAGEDOCROOT) && \
		ln -sfn /srv/www/bbsengine6/router.php   router.php && \
		ln -sfn /srv/www/bbsengine6/serve-md.php serve-md.php && \
		ln -sfn /srv/www/bbsengine6/join.php     join.php && \
		ln -sfn /srv/www/bbsengine6/login.php    login.php && \
		ln -sfn /srv/www/bbsengine6/logout.php   logout.php && \
		echo "installed engine entry-point symlinks" || echo "symlink install failed (rc=$$?)"'

.PHONY: stage prod-symlinks
