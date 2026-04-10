.PHONY: all clean convert convert-tmpl help watch stage stage-convert

# Default target
all: stage-convert

# Stage handbook files to webroot (rsync only, no conversion)
stage:
	@echo "Staging handbook files..."
	@mkdir -p /srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/
	@rsync --chmod=Dg=rwxs,Fgu=rw,Fo=r --times --verbose \
		--recursive --update --checksum \
		--exclude '*.md' \
		--exclude '*.pyc' \
		--exclude '__pycache__' \
		--exclude '.sass-cache' \
		--exclude 'Makefile' \
		--exclude '*.py' \
		--exclude '.*' \
		. /srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/
	@echo "✓ Handbook staged to /srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/"

# Convert markdown to .txt files and stage (all-in-one)
stage-convert:
	@echo "Converting markdown to txt and staging..."
	@mkdir -p /srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/
	@find . -name "*.md" -not -name "*.md~" | while read f; do \
		python3 -c "import markdown; content=open('$$f').read(); html=markdown.markdown(content, extensions=['extra','tables','fenced_code','codehilite']); print(html)" > /srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/$$(basename $$f .md).txt; \
	done
	@echo "✓ Converted and staged to /srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/"

# Convert markdown to HTML
convert:
	@echo "Converting markdown files to HTML..."
	@python3 convert_markdown.py . --recursive
	@echo "✓ Conversion complete"

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

# Watch for changes and convert automatically (requires watchdog)
watch:
	@command -v watchmedo >/dev/null 2>&1 || (echo "Install watchdog: pip install watchdog"; exit 1)
	@echo "Watching for markdown changes... (press Ctrl+C to stop)"
	watchmedo shell-command \
		--patterns="*.md" \
		--recursive \
		--command='python3 convert_markdown.py . --recursive' \
		.

# Install dependencies
install-deps:
	pip install markdown pygments

# Display help
help:
	@echo "Handbook Makefile targets:"
	@echo "  make stage          - Stage handbook files to webroot (rsync)"
	@echo "  make stage-convert - Convert markdown to txt and stage (default)"
	@echo "  make convert       - Convert markdown files to HTML"
	@echo "  make clean         - Remove backup files and temp content"
	@echo "  make watch         - Watch for changes and auto-convert"
	@echo "  make install-deps  - Install required dependencies"
	@echo "  make help          - Display this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make                      # Convert markdown to txt and stage"
	@echo "  make stage-convert        # Same as default"
	@echo "  make stage                # Rsync files without conversion"
	@echo "  python convert_markdown.py <file.md>  # Convert single file"
