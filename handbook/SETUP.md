# BBSEngine Handbook Apache2 Setup

This guide explains how to cleanly serve markdown documentation files through Apache2 for bbsengine.org.

## Overview

The handbook system provides:
- **Markdown serving** - Serve `.md` files with proper MIME types
- **HTML conversion** - Automatically convert markdown to styled HTML
- **Directory listing** - Clean navigation with Apache's fancy indexing
- **Caching & compression** - Performance optimization
- **Security** - Proper headers and file access control

## Architecture

```
bbsengine6/handbook/
├── .htaccess                    # Per-directory Apache configuration
├── bbsengine-handbook.conf      # Full Apache site configuration
├── convert_markdown.py          # Python markdown-to-HTML converter
├── Makefile                     # Build automation
├── index.md                     # Handbook index/home
├── specs/                       # Specifications
├── csrf/                        # CSRF documentation
└── *.md files...                # Documentation markdown files
```

## Installation

### 1. Install Dependencies

```bash
# Install markdown conversion tool
pip install markdown pygments

# For automatic watching (optional):
pip install watchdog
```

### 2. Choose Your Deployment Method

#### Option A: Alias in Existing Virtual Host (Recommended)

Add to your existing Apache configuration:

```apache
Alias /handbook/ "/home/opencode/data/work/bbsengine6/handbook/"

<Directory "/home/opencode/data/work/bbsengine6/handbook/">
    Options +Indexes +FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
```

Then restart Apache:
```bash
sudo systemctl restart apache2
```

#### Option B: Full Site Configuration

Use the provided `bbsengine-handbook.conf`:

```bash
# Copy configuration
sudo cp handbook/bbsengine-handbook.conf /etc/apache2/conf-available/

# Enable it
sudo a2enconf bbsengine-handbook

# Restart Apache
sudo systemctl restart apache2
```

#### Option C: Virtual Host

Use the virtual host section in `bbsengine-handbook.conf`:

```bash
# Copy and enable
sudo cp handbook/bbsengine-handbook.conf /etc/apache2/sites-available/
sudo a2ensite bbsengine-handbook.conf
sudo systemctl restart apache2
```

### 3. Set Permissions

```bash
# Make scripts executable
chmod +x handbook/convert_markdown.py

# Ensure Apache can read files
chmod -R 755 handbook/
```

## Usage

### Convert Markdown to HTML

#### Single File
```bash
python3 handbook/convert_markdown.py handbook/README.md
```

#### All Files
```bash
cd handbook
make convert
# or
python3 convert_markdown.py .
```

#### Watch for Changes
```bash
cd handbook
make watch
```

This will automatically convert markdown when files change (requires watchdog).

### View Documentation

- **Web**: Visit `http://localhost/handbook/` or `https://bbsengine.org/handbook/`
- **Direct**: Read markdown files directly at `handbook/*.md`
- **Converted**: View generated HTML at `handbook/*/index.html`

## Features

### Apache Configuration (.htaccess)

The `.htaccess` file provides:

1. **MIME Type Handling**
   - `.md` files served as `text/markdown`
   - `.html` files served as `text/html`
   - Backup files (`.md~`, `.bak`) blocked

2. **Directory Listing**
   - Fancy index with HTML table format
   - Sortable by name, version, date, size
   - UTF-8 encoding

3. **Performance**
   - Gzip compression for text files
   - 7-day cache for markdown and HTML
   - 1-day cache for JSON files

4. **Security**
   - Blocks backup and temporary files
   - Prevents directory traversal
   - Proper content headers
   - X-Content-Type-Options nosniff

### Markdown Converter

`convert_markdown.py` features:

- **Automatic Title Detection** - Extracts from first H1 heading
- **Responsive Design** - Mobile-friendly HTML output
- **Syntax Highlighting** - Code blocks with Pygments
- **Table of Contents** - Auto-generated from headings
- **Markdown Extensions**:
  - Fenced code blocks
  - Tables
  - Extra formatting
  - Code highlighting

- **Flexible Structure**:
  - Converts single files or entire directories
  - Preserves directory structure
  - Recursive conversion with `--recursive` flag
  - Custom output directories with `--output`

### Makefile Targets

```bash
make convert        # Convert all markdown to HTML
make clean          # Remove backup files
make watch          # Auto-convert on file changes
make install-deps   # Install Python dependencies
make help           # Show help
```

## File Structure

After conversion, the directory structure looks like:

```
handbook/
├── index.md → index/index.html
├── database.md → database/index.html
├── specs/
│   ├── index.md → specs/index/index.html
│   ├── architecture.md → specs/architecture/index.html
│   └── ...
└── ... other markdown files
```

Each markdown file is converted to `filename/index.html`, allowing clean URLs like `/handbook/database/` instead of `/handbook/database.html`.

## Apache Modules Required

The configuration requires these Apache modules (usually enabled by default):

- `mod_rewrite` - URL rewriting
- `mod_headers` - Custom headers
- `mod_mime` - MIME type configuration
- `mod_deflate` - Gzip compression
- `mod_expires` - Cache control
- `mod_autoindex` - Directory listing
- `mod_alias` - URL aliasing (for the alias method)

To enable missing modules:
```bash
sudo a2enmod rewrite headers mime deflate expires autoindex
sudo systemctl restart apache2
```

## Development Workflow

### Adding New Documentation

1. Create markdown file in appropriate directory:
   ```bash
   vim handbook/specs/new-topic.md
   ```

2. Convert to HTML:
   ```bash
   cd handbook
   python3 convert_markdown.py specs/new-topic.md
   ```

3. View in browser at `http://localhost/handbook/specs/new-topic/`

### Updating Existing Documentation

1. Edit the markdown file
2. Regenerate HTML:
   ```bash
   cd handbook
   python3 convert_markdown.py .
   ```
   or use watch mode:
   ```bash
   make watch
   ```

### Markdown Guidelines

- Start files with `# Title` (H1 heading)
- Use descriptive headings for structure
- Include code examples in fenced blocks
- Use proper markdown syntax
- Keep lines reasonably short (especially for terminal viewing)

## Troubleshooting

### Files Not Converting

1. Check Python installation:
   ```bash
   python3 --version
   pip3 list | grep markdown
   ```

2. Run converter with verbose output:
   ```bash
   python3 convert_markdown.py . -v
   ```

### Apache Not Serving Files

1. Check Apache configuration:
   ```bash
   sudo apache2ctl configtest
   ```

2. Verify permissions:
   ```bash
   ls -la handbook/
   ```

3. Check Apache error logs:
   ```bash
   sudo tail -f /var/log/apache2/error.log
   ```

### MIME Types Not Working

1. Verify .htaccess is being read:
   ```bash
   touch handbook/.htaccess  # Update timestamp
   ```

2. Check module availability:
   ```bash
   sudo apache2ctl -M | grep mime
   ```

3. Verify AllowOverride in main config:
   - Should include `All` or specific options

## Performance Tips

1. **Pre-convert all markdown** - Run `make convert` once instead of converting on-demand
2. **Enable compression** - Gzip reduces transfer size by 60-80%
3. **Use caching** - 7-day cache for docs reduces bandwidth
4. **CDN integration** - Cache through CDN for static HTML files

## Security Considerations

1. **File Access** - `.htaccess` blocks backup files and hidden files
2. **Content Headers** - Proper MIME types prevent browser interpretation issues
3. **CSRF Protection** - Use the existing CSRF documentation if adding forms
4. **CORS Headers** - Already configured in parent `.htaccess` file

## Integration with CI/CD

To automatically convert markdown during deployment:

```bash
#!/bin/bash
# In your deploy script
cd /path/to/bbsengine6/handbook
python3 convert_markdown.py .
sudo systemctl reload apache2
```

Or add to your Makefile:
```makefile
deploy: convert
	rsync -av . /var/www/handbook/
	sudo systemctl reload apache2
```

## Related Files

- **bbsengine-handbook.conf** - Full Apache configuration example
- **.htaccess** - Per-directory Apache configuration
- **convert_markdown.py** - Markdown to HTML converter
- **Makefile** - Build automation
- **index.md** - Handbook index/home page

## Further Help

For Apache documentation:
- https://httpd.apache.org/docs/
- https://httpd.apache.org/docs/2.4/mod/mod_rewrite.html

For Markdown:
- https://python-markdown.github.io/
- https://daringfireball.net/projects/markdown/syntax

## License

This documentation system is part of BBSEngine and follows the same license.
