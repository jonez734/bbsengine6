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

com:
	$(MAKE) -C com stage
	$(RSYNC) --exclude "releases" --exclude "templates_c" --chmod=Dg+rwxs $(COMSTAGE) $(COMPROD)

.PHONY: org com
