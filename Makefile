export ORGHOST = merlin
export COMHOST = copper
export ENGINEHOST = merlin
export STATICHOST = merlin
export PROJECT = bbsengine6

export datestamp = $(shell date +%Y%m%d-%H%M)
export archivename = $(PROJECT)-$(datestamp)
export PROJECTRELEASEDIR = /srv/repo/$(PROJECT)/
export PROJECTBUILDDIR = /home/jam/projects/$(PROJECT)/releases/$(archivename)/
export RSYNC = rsync --chmod=Dg=rwxs,Fgu=rw,Fo=r --times --verbose \
	--exclude '*~' \
	--archive --update --backup --recursive \
	--human-readable --checksum --rsh=ssh \
	--delete-after --mkpath \
	--exclude 'captchas'

export VERSION = 6

# @since 20230414
export SCSSLOADPATH = --load-path $(HOME)/projects/zoidweb6/skin/scss/ # --load-path $(HOME)/projects/bbsengine6/skin/scss/
export SCSS = sass --line-numbers --stop-on-error --trace --style expanded --sourcemap=none $(SCSSLOADPATH)

export MARDOWNLIBSTAGE = /srv/www/
export MARKDOWNLIBPROD = merlin:/srv/www/

# @since 20230424
export ENGINESTAGE = /srv/www/bbsengine6/
export ENGINESTAGEDOCROOT = /srv/www/vhosts/zoidtechnologies.com/html/engine/

export ENGINEPROD = $(ENGINEHOST):/srv/www/bbsengine6/
export ENGINEPRODDOCROOT = $(ENGINEHOST):/srv/www/vhosts/zoidtechnologies.com/html/engine/

export WWWPROD = $(ORGHOST):/srv/www/vhosts/www.bbsengine.org/
export WWWPRODDOCROOT = $(WWWPROD)html/

export WWWSTAGE = /srv/www/vhosts/www.bbsengine.org/
export WWWSTAGEDOCROOT = $(WWWSTAGE)html/

export ORGPROD = $(ORGHOST):/srv/www/vhosts/www.bbsengine.org/
export ORGPRODDOCROOT = $(WWWPROD)html/

export ORGSTAGE = /srv/www/vhosts/www.bbsengine.org/
export ORGSTAGEDOCROOT = $(ORGSTAGE)html/

export STATICSTAGE = /srv/www/vhosts/static.zoidtechnologies.com/
export STATICSTAGEDOCROOT = $(STATICSTAGE)html/
export STATICPROD = $(ORGHOST):/srv/www/vhosts/static.zoidtechnologies.com/

all:

clean:
	-$(MAKE) -C php clean
	-$(MAKE) -C handbook clean
	-$(MAKE) -C py clean
	-$(MAKE) -C www clean
	-$(MAKE) -C skin clean
	-rm *~

release:
	echo "-=- making a new release of $(PROJECT) -=-";
	mkdir -p $(PROJECTBUILDDIR);
	$(MAKE) -C www release;
	$(MAKE) -C handbook release;
	git log > CHANGELOG.txt;
	$(installfile) README.txt INSTALL.txt RELEASENOTES.txt CHANGELOG.txt composer.json $(PROJECTBUILDDIR);
	$(RSYNC) --verbose --recursive php py $(PROJECTBUILDDIR);
	pushd releases;\
	tar jcf $(archivename).tar.bz2 $(archivename)/*;\
	tar zcf $(archivename).tgz $(archivename)/*;\
	zip -r $(archivename).zip $(archivename)/*;\
	mkdir -p $(PROJECTRELEASEDIR);\
	install --mode=0644 $(archivename).tar.bz2 $(archivename).tgz $(archivename).zip $(PROJECTRELEASEDIR);\
	install --mode=0644 $(archivename)/README.txt $(PROJECTRELEASEDIR);\
	install --mode=0644 $(archivename)/CHANGELOG.txt $(PROJECTRELEASEDIR);\
	popd;\
	echo "[DONE]"

apidocs:
	mkdir -p $(STAGEDOCROOT)$(VERSION)/apidocs/
	phpdoc run \
	--target $(STAGEDOCROOT)$(VERSION)/apidocs/ \
	--directory php \
	--extensions php \
	--title "$(PROJECT) apidocs" \
	--defaultpackagename "$(PROJECT)" \
	--sourcecode \
	--progressbar \
	--template responsive

handbook:
	-$(MAKE) -C handbook stage
	$(RSYNC) --dry-run $(WWWSTAGEDOCROOT)handbook/$(VERSION)/ $(WWWPRODDOCROOT)handbook/$(VERSION)/

sql:
	tar zcvf $(PROJECT)-sql-$(datestamp).tar.gz sql/

markdown:
	$(RSYNC) --links --exclude 'vhosts' /srv/www/php-markdown-lib /srv/www/markdown $(MARKDOWNLIBPROD)

#wwwcom:
#	$(MAKE) -C www com

wwworg:
	$(MAKE) -C www org

engine:
	-$(MAKE) -C php stage
	-$(MAKE) -C skin stage
	-$(MAKE) -C js stage
	-$(MAKE) -C smarty stage
	$(RSYNC) $(ENGINESTAGE) $(ENGINEPROD)
	$(RSYNC) $(ENGINESTAGEDOCROOT) $(ENGINEPRODDOCROOT)

push:
	git push -u gitlab
	git push -u github

backup:
	rsync --recursive --verbose --exclude=.venv . /run/media/jam/AEAB-CF37/projects/$(PROJECT)/

.PHONY: handbook release sql prod www apidocs clean
