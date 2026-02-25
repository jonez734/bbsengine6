#export HOST = copper

#export WWWPROD = $(HOST):/srv/www/vhosts/www.bbsengine.com/
#export WWWPRODDOCROOT = $(WWWPROD)html/

#export WWWSTAGE = /srv/www/vhosts/www.bbsengine.com/
#export WWWSTAGEDOCROOT = $(WWWSTAGE)html/

all:

clean:
	-rm *~
	$(MAKE) -C skin clean
	$(MAKE) -C php clean
	$(MAKE) -C smarty clean

stage:
	$(MAKE) -C php stage
	$(MAKE) -C skin stage
	$(MAKE) -C smarty stage
	$(MAKE) -C js stage

	mkdir -p $(COMSTAGE)templates_c/
	$(RSYNC) config-prod.php $(COMSTAGEDOCROOT)config.php
	-$(RSYNC) htpasswd-prod $(COMSTAGEDOCROOT).htpasswd
	$(RSYNC) htaccess-prod $(COMSTAGEDOCROOT).htaccess

prod:  stage
	$(RSYNC) $(WWWSTAGE) $(COMHOST):$(COMPROD)
#release:
#	$(MAKE) -C php release;
#	$(MAKE) -C smarty release;
#	$(MAKE) -C skin release;
