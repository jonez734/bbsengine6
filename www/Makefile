all:

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
	$(MAKE) -C ../handbook stage
	$(RSYNC) --exclude "releases" $(ORGSTAGE) $(ORGPROD)
	
com:
	$(MAKE) -C com stage
	$(RSYNC) --exclude "releases" $(COMSTAGE) $(COMPROD)

.PHONY: org com
