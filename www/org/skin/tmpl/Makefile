all:

clean:
	-rm *~

stage:
	$(RSYNC) *.tmpl $(WWWSTAGEDOCROOT)skin/tmpl/
	# @since 2026-09-07 -- engine/router.php at the .org vhost
	# renders chapters via Smarty's displaypage(..., 'page-markdown.tmpl', ...)
	# which extends zoid6-page.tmpl + defines a {block name="main"}.
	# page-markdown.tmpl also {include}s youarehere.tmpl, which in
	# turn {include}s teos-breadcrumbs.tmpl. The .org vhost's
	# \config\SMARTYTEMPLATESDIR lists both $(DOCUMENTROOT)/skin/tmpl/
	# (this target's primary output) and /srv/www/bbsengine6/skin/tmpl/
	# (shipped via skin-prod).
	#
	# Why a new zoid6-page.tmpl instead of overwriting the existing
	# page.tmpl: bbsengine6/www/org/skin/tmpl/page.tmpl defines
	# {block name="content"} and is the extends target for many
	# legacy .org templates (archive-*, contact-us, dir, error-
	# message, file, index, ...). Overwriting it with the zoid6
	# page.tmpl (which uses {block name="main"}) would break those
	# extends targets. Renaming the extends target for page-
	# markdown.tmpl to zoid6-page.tmpl keeps both template trees
	# intact -- the legacy .org templates still extend page.tmpl,
	# and the router-rendered chapters extend zoid6-page.tmpl.
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
	$(RSYNC) $(CURDIR)/../../../../../zoid6/shared/skin/tmpl/page.tmpl $(WWWSTAGEDOCROOT)skin/tmpl/zoid6-page.tmpl
