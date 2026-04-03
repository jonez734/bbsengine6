# Runtime Markdown Conversion for BBSEngine Handbook

This guide explains how to serve markdown files with **runtime conversion** instead of pre-converting to HTML. This approach converts markdown to HTML on-the-fly when requests are made.

## Overview

Runtime conversion has advantages:
- **No build step** - Changes to markdown are immediately visible
- **Automatic updates** - No need to regenerate files
- **Smaller storage** - Only markdown files stored, HTML generated per-request
- **Single source** - One version of documentation (the markdown)

And tradeoffs:
- **Slightly slower** - First request conversion has latency (cached afterwards)
- **Memory usage** - Caching adds memory overhead
- **Server load** - More CPU-intensive than serving static HTML

## Architecture

The solution uses Flask with Python markdown conversion:

```
Request → Apache mod_wsgi → Flask app.py → Markdown converter → HTML response
                                           ↓
                                      (cached results)
```

## Installation

### 1. Install Dependencies

```bash
# Python packages
pip install flask markdown pygments

# Apache mod_wsgi
sudo apt-get install libapache2-mod-wsgi-py3

# Enable the module
sudo a2enmod wsgi
```

### 2. Set Up Flask Application

The solution is already in place:
- `app.py` - Main Flask application
- `wsgi.py` - WSGI entry point for Apache

### 3. Configure Apache

#### Option A: Using mod_wsgi (Recommended)

```bash
# Copy Apache configuration
sudo cp handbook/handbook-wsgi.conf /etc/apache2/sites-available/

# Enable the site
sudo a2ensite handbook-wsgi.conf

# Restart Apache
sudo systemctl restart apache2
```

#### Option B: Using Flask development server (Testing only)

```bash
cd handbook
python3 app.py
```

Then visit `http://localhost:5000/handbook/`

#### Option C: Using uWSGI with Apache

Install and configure:
```bash
pip install uwsgi
```

Then create a service file and proxy configuration.

## Features

### Runtime Features

1. **Markdown Processing**
   - Automatic conversion on request
   - LRU cache for performance (128 items max)
   - Automatic title extraction from H1 headings

2. **Directory Listing**
   - Lists markdown files in directories
   - Parent directory navigation
   - File type icons
   - Clickable links to subdirectories

3. **Breadcrumb Navigation**
   - Shows current location in document tree
   - Clickable breadcrumbs for quick navigation
   - Auto-generated from file path

4. **Smart URL Handling**
   - `/handbook/database/` serves `database.md`
   - `/handbook/specs/` lists contents or serves `specs/index.md`
   - `/handbook/specs/architecture` serves `specs/architecture.md`
   - No need for file extensions

5. **Responsive HTML Output**
   - Mobile-friendly styling
   - Code syntax highlighting
   - Markdown extensions: tables, fenced code, TOC, etc.

### Performance Optimizations

1. **LRU Cache**
   - Caches converted markdown (128 max items)
   - Reduces conversion CPU on repeated requests
   - Automatic eviction of least-used items

2. **HTTP Caching**
   - 1-hour cache headers by default
   - Configurable in `handbook-wsgi.conf`

3. **Compression**
   - Gzip compression for HTML and text
   - Reduces bandwidth by 60-80%

## Usage

### Serving Files

The Flask app automatically serves:

```
handbook/
├── README.md              → /handbook/readme/ or /handbook/
├── database.md            → /handbook/database/
├── specs/
│   ├── index.md          → /handbook/specs/ or /handbook/specs/index/
│   ├── architecture.md    → /handbook/specs/architecture/
│   └── database.md        → /handbook/specs/database/
└── csrf/
    └── README.md         → /handbook/csrf/ or /handbook/csrf/readme/
```

### Adding New Documentation

1. Create markdown file:
   ```bash
   vim handbook/specs/new-feature.md
   ```

2. View immediately in browser:
   ```
   https://bbsengine.org/handbook/specs/new-feature/
   ```

3. No rebuild or conversion needed - it's automatic!

### Markdown File Structure

Each markdown file should start with a title:

```markdown
# Feature Documentation

This is the feature docs...

## Subsection

More details...
```

The `# Feature Documentation` heading becomes:
- The page title in `<title>` tag
- The H1 heading on the page
- The last breadcrumb item

## Configuration

### Cache Settings

Modify `app.py` to change cache behavior:

```python
# Current setting: cache 128 converted markdown files
MAX_CACHE_SIZE = 128
```

Larger cache = more memory usage but better performance on repeated requests.

### HTML Styling

The HTML template is in `app.py` as `HTML_TEMPLATE`. Modify CSS directly to change appearance.

### Caching Headers

In `handbook-wsgi.conf`:

```apache
ExpiresDefault "access plus 1 hour"
```

Change to adjust browser caching duration.

### Markdown Extensions

In `app.py`, modify `get_markdown_extensions()`:

```python
def get_markdown_extensions():
    return [
        'toc',              # Table of contents
        'tables',           # GitHub-flavored tables
        'fenced_code',      # ``` code blocks
        'codehilite',       # Syntax highlighting
        'extra',            # Extra formatting
    ]
```

## Troubleshooting

### Flask App Not Starting

1. Check Python and dependencies:
   ```bash
   python3 --version
   python3 -c "import flask, markdown; print('OK')"
   ```

2. Run development server for better error output:
   ```bash
   cd handbook
   python3 app.py
   ```

3. Check Apache logs:
   ```bash
   sudo tail -f /var/log/apache2/error.log
   ```

### Markdown Not Converting

1. Check file encoding is UTF-8:
   ```bash
   file -i handbook/specs/*.md
   ```

2. Verify markdown syntax:
   ```bash
   python3 -c "
   import markdown
   with open('handbook/specs/test.md') as f:
       print(markdown.markdown(f.read()))
   "
   ```

### Pages Loading Slowly

1. Check if conversion is the bottleneck:
   ```bash
   # Add timing to app.py around convert_markdown()
   import time
   start = time.time()
   html = convert_markdown(content)
   print(f"Conversion took: {time.time() - start:.2f}s")
   ```

2. Increase cache size if needed:
   ```python
   MAX_CACHE_SIZE = 256  # More aggressive caching
   ```

3. Monitor Apache processes:
   ```bash
   sudo ps aux | grep wsgi
   ```

### Directory Listing Not Working

1. Verify file permissions:
   ```bash
   ls -la handbook/specs/
   ```

2. Check that no `index.md` is in the directory:
   ```bash
   ls -la handbook/specs/index.md  # Should not exist
   ```

3. Verify Flask is reading the directory:
   - Add debug code in `list_directory()` function
   - Watch server logs

### Breadcrumbs Not Showing

1. Verify path in URL matches file location
2. Check that special characters aren't breaking the parsing
3. Look at breadcrumb rendering code in `render_breadcrumb()`

## Performance Comparison

### Runtime vs. Pre-conversion

| Aspect | Runtime | Pre-converted |
|--------|---------|---|
| Build time | None | ~1s per 100 files |
| First request | 50-100ms | <10ms |
| Cached request | <1ms | <10ms |
| Storage | Small | +20-30% HTML files |
| Deployment | Copy markdown | Copy HTML + markdown |
| Update speed | Instant | Must rebuild |

**Recommendation**: Use runtime conversion for documentation that changes frequently, pre-conversion for stable, high-traffic docs.

## Mixed Approach

You can combine both approaches:

```bash
# Pre-convert some docs for maximum speed
python3 handbook/convert_markdown.py handbook/specs/

# Serve dynamic docs via Flask
# Flask will check if .html exists first, convert if needed
```

Modify `app.py` to check for pre-converted HTML files first.

## Security Considerations

The current implementation:

1. **Directory Traversal Protection**
   - Validates file paths don't escape handbook dir
   - Returns 403 on traversal attempts

2. **File Type Protection**
   - Only serves `.md` files or other safe types
   - Blocks `.py`, `.conf`, and dangerous files

3. **Content Escaping**
   - Escapes user-controlled content in breadcrumbs
   - HTML sanitization in markdown extensions

4. **Access Control**
   - Apache mod_wsgi runs as www-data user
   - Limited file system access
   - Configurable via `WSGIDaemonProcess user=...`

## Advanced Customization

### Custom Error Pages

Modify error handlers in `app.py`:

```python
@app.errorhandler(404)
def not_found(error):
    # Custom 404 page
    return render_template_string(...), 404
```

### Static File Serving

To serve CSS, images, JavaScript:

```apache
# In handbook-wsgi.conf
AliasMatch ^/handbook/(.*\.(?:css|js|png|jpg))$ \
    /home/opencode/data/work/bbsengine6/handbook/static/$1
```

Then add files to `handbook/static/` directory.

### Database Integration

Extend `app.py` to serve docs from database instead of files:

```python
@app.route('/handbook/<doc_id>')
def serve_from_db(doc_id):
    # Query database
    content = db.get_doc(doc_id)
    html = convert_markdown(content)
    return render_html(html, title)
```

### API Endpoint

Add JSON API for programmatic access:

```python
@app.route('/handbook/api/docs/<path:path>.json')
def api_get_markdown(path):
    # Return raw markdown as JSON
    return jsonify({'content': read_markdown(path)})
```

## Integration with CI/CD

To rebuild cache or warm up converter on deployment:

```bash
#!/bin/bash
# deploy.sh
cd /path/to/bbsengine6/handbook

# Install/update dependencies
pip install -r requirements.txt

# Restart Flask app via systemd
sudo systemctl restart handbook-wsgi

# Or via Apache
sudo systemctl restart apache2
```

## Related Files

- `app.py` - Main Flask application
- `wsgi.py` - WSGI entry point
- `handbook-wsgi.conf` - Apache configuration
- `Makefile` - Build automation (not needed for runtime)
- `convert_markdown.py` - For pre-conversion (optional with runtime approach)

## See Also

- [Build-time Conversion Guide](SETUP.md) - Pre-convert markdown
- [Apache mod_wsgi Documentation](https://modwsgi.readthedocs.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Python Markdown](https://python-markdown.github.io/)

## License

Part of BBSEngine project.
