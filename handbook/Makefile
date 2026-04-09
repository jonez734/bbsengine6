.PHONY: all clean convert help watch convert-tmpl

# Default target
all: convert convert-tmpl

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
	@echo "  make convert      - Convert all markdown files to HTML"
	@echo "  make clean        - Remove backup files and temporary content"
	@echo "  make watch        - Watch for changes and auto-convert"
	@echo "  make install-deps - Install required dependencies"
	@echo "  make help         - Display this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make                # Convert markdown to HTML"
	@echo "  python convert_markdown.py <file.md>  # Convert single file"
	@echo "  python convert_markdown.py .          # Convert all files"
