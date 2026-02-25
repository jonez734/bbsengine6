all:

clean:
	-rm *~

stage:
	$(MAKE) -C php stage
	$(MAKE) -C skin stage
	$(MAKE) -C smarty stage
	$(MAKE) -C js stage

	mkdir -p $(ORGSTAGE)templates_c/
	$(RSYNC) config-prod.php $(ORGSTAGEDOCROOT)config.php
	-$(RSYNC) htpasswd-prod $(ORGSTAGEDOCROOT).htpasswd
	$(RSYNC) htaccess-prod $(ORGSTAGEDOCROOT).htaccess

prod: stage
	$(RSYNC) $(ORGSTAGE) $(ORGHOST):$(ORGPROD)

.PHONY: stage
