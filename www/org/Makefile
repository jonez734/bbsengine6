all:

clean:
	-rm *~

stage:
	$(MAKE) -C php stage
	$(MAKE) -C skin stage
	$(MAKE) -C smarty stage
	$(MAKE) -C js stage

	$(RSYNC) config-prod.php $(ORGSTAGEDOCROOT)config.php
	-$(RSYNC) htpasswd-prod $(ORGSTAGEDOCROOT).htpasswd
	$(RSYNC) htaccess-prod $(ORGSTAGEDOCROOT).htaccess

prod: stage
	$(RSYNC) $(ORGSTAGE) $(ORGPROD)
	# Force templates_c/ to mode 2775 group www on the receiver.
	# rsync's --chmod=Dg=rwxs only applies when the dir is CREATED
	# on the receiver; if it already existed (e.g. from an older
	# deploy that landed the dir at mode 2755 before --chmod was
	# reliably honored), rsync's --archive --times preserves the
	# existing perms instead of chmod'ing them. install -d is
	# idempotent: it mkdir -p + chmod in one shot, no-op if the
	# mode/group already match. Without this step the web user
	# (cyrus, not in group www) cannot write compiled templates
	# here and Smarty fatals with 'unable to create directory'.
	ssh $(ORGHOST) install -d -m 2775 -g www -o jam $(ORGSTAGE)templates_c

.PHONY: stage
