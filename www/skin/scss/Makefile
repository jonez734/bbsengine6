SCSS = sass --sourcemap=none --stop-on-error --trace --style expanded

all:

.scss.css:
	$(SCSS) $< $@

stage: 
	$(SCSS) --update --watch .:$(WWWSTAGEDOCROOT)skin/css/

clean:
	-rm *~ *.css *.css.map

.SUFFIXES: .scss .css
