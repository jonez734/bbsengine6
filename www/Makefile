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

remove-legacy-handbook:
	ssh $(ORGHOST) 'cd /srv/www/vhosts/www.bbsengine.org/html/handbook/ && \
		rm -f bbsengine-handbook.conf handbook-wsgi.conf modules.adoc modules.html && \
		echo "removed legacy handbook artifacts" || echo "removal failed (rc=$$?)"'

com:
	$(MAKE) -C com stage
	$(RSYNC) --exclude "releases" --exclude "templates_c" --chmod=Dg+rwxs $(COMSTAGE) $(COMPROD)

.PHONY: org com remove-legacy-handbook
