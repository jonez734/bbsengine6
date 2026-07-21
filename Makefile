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
export SCSSLOADPATH = --load-path $(PWD)/../zoidweb6/skin/scss/ \
                     --load-path $(PWD)/skin/scss/ \
                     --load-path $(PWD)/../zoid6/shared/skin/scss/
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
	-$(MAKE) -C handbook stage-convert

handbook-prod:
	-$(MAKE) VERSION=$(VERSION) -C handbook stage-convert
	$(RSYNC) $(WWWSTAGEDOCROOT)handbook/$(VERSION)/ $(WWWPRODDOCROOT)handbook/$(VERSION)/

prod:
##	$(MAKE) wwworg
	$(MAKE) engine
##	$(MAKE) handbook-prod
	$(MAKE) markdown

sql:
	tar zcvf $(PROJECT)-sql-$(datestamp).tar.gz sql/

markdown:
	$(RSYNC) --links --exclude 'vhosts' /srv/www/markdown $(MARKDOWNLIBPROD)


skin-prod:
	$(MAKE) -C skin stage
	$(RSYNC) $(ENGINESTAGE)skin/ $(ENGINEPROD)skin/
#wwwcom:
#	$(MAKE) -C www com

wwworg:
	$(MAKE) -C www org

engine:
	$(MAKE) -C engine all
push:
	git push -u gitlab
	git push -u github

backup:
	rsync --recursive --verbose --exclude=.venv . /run/media/jam/AEAB-CF37/projects/$(PROJECT)/

log:
	git log --graph --pretty=format:"%h %ad %s%d [%an]%n%B" --date=short > LOG_FULL.md
	git log --pretty=format:"%ad|%h %s%d [%an]" --date=short | awk -F'|' '{if ($$1!=date) {print "## " $$1; date=$$1} print "  " $$2}' > LOG_SUMMARY.md

.PHONY: handbook handbook-prod release sql prod www apidocs clean log engine prod skin-prod php-deploy php-deploy-prod parsedown-deploy parsedown-deploy-prod deploy



php-deploy:
	$(RSYNC) php/ $(ENGINESTAGE)php/

php-deploy-prod: php-deploy
	$(RSYNC) $(ENGINESTAGE)php/ $(ENGINEPROD)php/

parsedown-deploy:
	mkdir -p /srv/www/markdown/
	$(RSYNC) vendor/erusev/parsedown/Parsedown.php /srv/www/markdown/
	$(RSYNC) vendor/erusev/parsedown-extra/ParsedownExtra.php /srv/www/markdown/

parsedown-deploy-prod: parsedown-deploy
	$(RSYNC) /srv/www/markdown/ merlin:/srv/www/markdown/

markdown-deploy:
	mkdir -p /srv/www/markdown/
	$(RSYNC) markdown/Markdown*.php /srv/www/markdown/

markdown-deploy-prod: parsedown-deploy
	$(RSYNC) /srv/www/markdown/ merlin:/srv/www/markdown/

deploy:
	$(MAKE) -C engine stage
	$(MAKE) -C engine deploy-engine
	$(MAKE) -C skin stage
	$(MAKE) php-deploy
	mkdir -p $(ENGINESTAGE)smarty/
	$(RSYNC) smarty/*.php $(ENGINESTAGE)smarty/
	$(RSYNC) $(ENGINESTAGE) $(ENGINEPROD)
	$(RSYNC) $(ENGINESTAGEDOCROOT) $(ENGINEPRODDOCROOT)
