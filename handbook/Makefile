.PHONY: all clean convert-tmpl help stage

# Default target
all: stage

# Stage handbook sources to HANDBOOKDIR for runtime rendering by
# www/org/php/handbook.php via \bbsengine6\markdown\parseDocument
# (request-time path, matching teos's teospath chain). The handler
# reads .md files directly from the docroot, so this rsync MUST
# include them — no install-time conversion happens anywhere in
# the chain.
stage:
	@echo "Staging handbook sources..."
	@mkdir -p /srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/
	@rsync --chmod=Dg=rwxs,Fgu=rw,Fo=r --times --verbose \
		--recursive --update --checksum \
		--exclude '*.pyc' \
		--exclude '__pycache__' \
		--exclude '.sass-cache' \
		--exclude 'Makefile' \
		--exclude '.*' \
		. /srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/
	@echo "✓ Handbook sources staged to /srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/"

# Convert markdown to Smarty templates
convert-tmpl:
	@echo "Converting markdown files to Smarty templates..."
	@find . -name "*.md" -not -name "*.md~" | while read f; do \
		PYTHONPATH=/home/opencode/data/work/bbsengine6/py/src python3 -m bbsengine6.md2tpl "$$f"; \
	done
	@echo "✓ Template conversion complete"

# Clean up generated files and backups
clean:
	@echo "Cleaning up..."
	-find . -name "*.md~" -delete
	-find . -name "*.bak" -delete
	-find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleanup complete"

# Display help
help:
	@echo "Handbook Makefile targets:"
	@echo "  make stage          - Stage handbook sources (.md etc.) to HANDBOOKDIR for runtime rendering"
	@echo "  make convert-tmpl  - Convert markdown files to Smarty templates (developer helper)"
	@echo "  make clean         - Remove backup files and temp content"
	@echo "  make help          - Display this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make                      # Stage handbook sources (default)"
	@echo "  make stage                # Same as default"
