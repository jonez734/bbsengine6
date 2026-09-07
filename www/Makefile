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
	#
	# @since 2026-09-07 — exclude the four legacy handbook
	# artifacts (modules.adoc, modules.html, *.conf) from the
	# rsync. The `remove-legacy-handbook` target ssh-runs `rm`
	# on merlin to remove them once; these excludes prevent a
	# subsequent `make wwworg` from re-pushing them. The local
	# stage at /srv/www/vhosts/www.bbsengine.org/html/handbook/
	# is mounted read-only (cannot rm locally) and still
	# contains the four files, so without these excludes the
	# cleanup would be reverted on the next wwworg run. Patterns
	# are anchored at the transfer root (html/handbook/...) so
	# they match only the legacy files and not anything under
	# html/handbook/6/ (the new content's sibling). The new
	# content's specs/ subdir lives at html/handbook/6/specs/
	# and is unaffected by html/handbook/specs/ patterns. The
	# broader legacy cleanup (bbsengine.html,
	# bbsengine-modules.html, csrf/, migrations/, top-level
	# specs/) is intentionally not in this exclude set — those
	# are out of the operator's current scope (modules.adoc,
	# modules.html, *.conf) and can be added in a follow-up
	# commit if desired.
	$(RSYNC) --exclude "releases" --exclude "templates_c" \
	         --exclude "engine/" --exclude "html/engine/" \
	         --exclude "html/handbook/bbsengine-handbook.conf" \
	         --exclude "html/handbook/handbook-wsgi.conf" \
	         --exclude "html/handbook/modules.adoc" \
	         --exclude "html/handbook/modules.html" \
	         --chmod=Dg+rwxs $(ORGSTAGE) $(ORGPROD)

# @since 2026-09-07 — one-shot cleanup of the legacy Flask /
# gunicorn / mod_wsgi artifacts that survive under
# merlin:/srv/www/vhosts/www.bbsengine.org/html/handbook/.
# The current request-time PHP handbook (engine/router.php +
# engine/serve-md.php, both shipped via engine-deploy-prod)
# does not reference any of these files; they have been dead
# weight since the Flask stack was retired. The build host's
# local stage at /srv/www/vhosts/www.bbsengine.org/html/handbook/
# still contains them but is mounted read-only (cannot rm
# locally), so the `org` target's rsync carries --exclude
# patterns for the same four files (see above) that prevent
# re-introduction on subsequent runs. Run this target once to
# remove the files on merlin; after it runs, the `org` excludes
# keep them gone even if `make wwworg` is re-invoked from the
# read-only local stage. Uses ssh directly rather than rsync
# so the deletion is unambiguous and does not depend on
# rsync's source-side filter behavior; ssh invocation is
# identical in shape to the engine/Makefile ssh-pushes
# elsewhere in this deploy chain.
remove-legacy-handbook:
	ssh $(ORGHOST) 'cd /srv/www/vhosts/www.bbsengine.org/html/handbook/ && \
		rm -f bbsengine-handbook.conf handbook-wsgi.conf modules.adoc modules.html && \
		echo "removed legacy handbook artifacts" || echo "removal failed (rc=$$?)"'

com:
	$(MAKE) -C com stage
	$(RSYNC) --exclude "releases" --exclude "templates_c" --chmod=Dg+rwxs $(COMSTAGE) $(COMPROD)

.PHONY: org com remove-legacy-handbook
