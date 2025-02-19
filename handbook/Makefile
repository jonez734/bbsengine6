all:

clean:
	-rm *~

stage:
	-$(RSYNC) *.txt *.md *.html *.adoc $(WWWSTAGEDOCROOT)handbook/$(VERSION)/
