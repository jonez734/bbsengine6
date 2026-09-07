all:

VERSION ?= 6

clean:
	-rm *~
	$(MAKE) -C skin clean
	$(MAKE) -C php clean
	$(MAKE) -C smarty clean

#release:
#	$(MAKE) -C php release;
#	$(MAKE) -C smarty release;
#	$(MAKE) -C skin release;

org:
	$(MAKE) -C org stage
	$(MAKE) -C ../handbook stage VERSION=$(VERSION)
	# @since 2026-09-06 — exclude engine/ from this rsync. The local
	# ORGSTAGE (/srv/www/vhosts/www.bbsengine.org/) is read-only on
	# the build host (owned jam:www mode 755), so engine/*.php is
	# never staged there — only engine/Makefile's `deploy` ssh-pushes
	# it straight to both prod docroots (see engine/Makefile:53-55 and
	# the top-level engine-deploy-prod target). Without these excludes
	# rsync deletes the remote html/engine/ tree on every `make wwworg`
	# because the source side has no engine/ to mirror. Both forms
	# (engine/, html/engine/) are required because ORGPROD carries the
	# html/ prefix while ORGSTAGE doesn't.
	$(RSYNC) --exclude "releases" --exclude "templates_c" \
	         --exclude "engine/" --exclude "html/engine/" \
	         --chmod=Dg+rwxs $(ORGSTAGE) $(ORGPROD)

# @since 2026-09-07 — one-shot cleanup of the legacy Flask /
# gunicorn / mod_wsgi artifacts that survive under
# merlin:/srv/www/vhosts/www.bbsengine.org/html/handbook/.
# The new request-time PHP handbook (handbook.php + engine/router.php)
# does not reference any of these files; they have been dead weight
# since the Flask stack was retired. The build host's local stage at
# /srv/www/vhosts/www.bbsengine.org/html/handbook/ still contains
# them but is mounted read-only (cannot rm locally), and the
# existing wwworg rsync would re-transfer them on every run since
# they are present in the source. Run this target once to remove
# them on merlin; subsequent `make wwworg` runs will then
# re-introduce them from the build host's read-only local stage
# unless the build host's stage is also cleaned (out of scope for
# this Makefile — that requires sudo / remount on the build host).
# Uses ssh directly rather than rsync so the deletion is
# unambiguous and does not depend on the source-side filter
# behavior; ssh invocation is identical in shape to the engine/Makefile
# ssh-pushes elsewhere in this deploy chain.
remove-legacy-handbook:
	ssh $(ORGHOST) 'cd /srv/www/vhosts/www.bbsengine.org/html/handbook/ && \
		rm -f bbsengine-handbook.conf handbook-wsgi.conf modules.adoc modules.html && \
		echo "removed legacy handbook artifacts" || echo "removal failed (rc=$$?)"'

com:
	$(MAKE) -C com stage
	$(RSYNC) --exclude "releases" --exclude "templates_c" --chmod=Dg+rwxs $(COMSTAGE) $(COMPROD)

.PHONY: org com remove-legacy-handbook
