all:

clean:
	-rm *~

install:
	mkdir -p $(DOCROOT)js/
	$(RSYNC) --copy-links *.js $(DOCROOT)js/
