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
	$(RSYNC) --chmod=Dg+rwxs $(ORGSTAGE) $(ORGPROD)
	# Force templates_c/ to mode 2775 group www on the receiver.
	# rsync's --chmod (whether = or +) only applies when the dir
	# is CREATED on the receiver; if it already existed, rsync's
	# --archive --times preserves the existing perms instead of
	# chmod'ing them. install -d is idempotent: mkdir -p + chmod
	# in one shot, no-op if the mode/group already match. Without
	# this step the web user (cyrus, not in group www) cannot
	# write compiled templates here and Smarty fatals. Mirrors
	# the same fix in www/org/Makefile's prod target so both
	# entry points (`make -C www org` and `make -C www/org prod`)
	# leave templates_c/ correctly chmod'd.
	ssh $(ORGHOST) install -d -m 2775 -g www -o jam $(ORGSTAGE)templates_c

remove-legacy-handbook:
	ssh $(ORGHOST) 'cd /srv/www/vhosts/www.bbsengine.org/html/handbook/ && \
		rm -f bbsengine-handbook.conf handbook-wsgi.conf modules.adoc modules.html && \
		echo "removed legacy handbook artifacts" || echo "removal failed (rc=$$?)"'

com:
	$(MAKE) -C com stage
	$(RSYNC) --exclude "releases" --exclude "templates_c" --chmod=Dg+rwxs $(COMSTAGE) $(COMPROD)

.PHONY: org com remove-legacy-handbook
