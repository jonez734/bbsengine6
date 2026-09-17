all:

clean:
	-rm *~

stage:
	$(RSYNC) *.tmpl $(WWWSTAGEDOCROOT)skin/tmpl/
	# @since 2026-09-07 -- engine/router.php at the .org vhost
	# renders chapters via Smarty's displaypage(..., 'page-markdown.tmpl', ...)
<<<<<<< HEAD
	# which extends page.tmpl + defines a {block name="content"}.
	# page-markdown.tmpl also {include}s youarehere.tmpl, which in
	# turn {include}s teos-breadcrumbs.tmpl. The .org vhost's
	# \config\SMARTYTEMPLATESDIR lists both $(DOCUMENTROOT)/skin/tmpl/
	# (this target's primary output) and /srv/www/bbsengine6/skin/tmpl/
	# (shipped via skin-prod).
	#
	# Note on engine/serve-md.php: it does NOT require any templates.
	# It streams raw .md files as text/plain; the only thing it
	# needs on the .org vhost is filesystem reachability of the
	# handbook/<v>/<uri>.md tree (shipped via handbook-deploy-prod).
	#
	# Paths are relative to this Makefile's location. From
	# bbsengine6/www/org/skin/tmpl/, four levels up lands at the
	# meta-repo root (where bbsengine6/ and zoid6/ both live).
	$(RSYNC) $(CURDIR)/../../../../skin/tmpl/page-markdown.tmpl $(WWWSTAGEDOCROOT)skin/tmpl/
	$(RSYNC) $(CURDIR)/../../../../skin/tmpl/youarehere.tmpl $(WWWSTAGEDOCROOT)skin/tmpl/
	$(RSYNC) $(CURDIR)/../../../../skin/tmpl/teos-breadcrumbs.tmpl $(WWWSTAGEDOCROOT)skin/tmpl/
