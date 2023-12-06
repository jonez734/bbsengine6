all:

clean:
	-rm *~
	$(MAKE) -C css clean
	$(MAKE) -C tmpl clean
	$(MAKE) -C art clean
	$(MAKE) -C scss clean

stage:
	$(MAKE) -C scss stage
	$(MAKE) -C tmpl stage
	$(MAKE) -C art stage
	$(RSYNC) htaccess-prod $(WWWSTAGE)html/skin/.htaccess
