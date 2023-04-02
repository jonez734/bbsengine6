all:

clean:
	-rm *~
	-$(MAKE) -C php clean
	-$(MAKE) -C py clean
