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
	$(RSYNC) --exclude "releases" --exclude "templates_c" --chmod=Dg+rwxs $(ORGSTAGE) $(ORGPROD)

com:
	$(MAKE) -C com stage
	$(RSYNC) --exclude "releases" --exclude "templates_c" --chmod=Dg+rwxs $(COMSTAGE) $(COMPROD)

.PHONY: org com
