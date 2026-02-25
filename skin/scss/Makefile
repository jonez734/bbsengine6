#SCSS = sass --stop-on-error --trace --style expanded --sourcemap=none

all:

.scss.css:
	$(SCSS) $< $@

stage: 
	$(SCSS) --update --watch .:$(STATICSTAGEDOCROOT)skin/css/

clean:
	-rm *~ *.css *.css.map

.SUFFIXES: .scss .css
