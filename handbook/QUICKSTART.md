# Quick Start Guide - Markdown Handbook

Choose your approach based on your needs.

## Option 1: Runtime Conversion (Recommended for Development)

No build step - changes visible immediately.

### Setup (5 minutes)

```bash
# 1. Install dependencies
pip install flask markdown pygments

# 2. Run development server
cd /home/opencode/data/work/bbsengine6/handbook
python3 app.py

# 3. Visit http://localhost:5000/handbook/
```

### For Production with Apache

```bash
# 1. Install mod_wsgi
sudo apt-get install libapache2-mod-wsgi-py3
sudo a2enmod wsgi

# 2. Copy Apache config
sudo cp handbook/handbook-wsgi.conf /etc/apache2/sites-available/
sudo a2ensite handbook-wsgi.conf

# 3. Restart Apache
sudo systemctl restart apache2

# 4. Visit https://bbsengine.org/handbook/
```

**Advantages:**
- No build step
- Changes visible immediately
- Automatic caching
- Single source of truth

**Disadvantages:**
- Slightly slower on first request
- Uses more CPU

---

## Option 2: Pre-conversion to Static HTML

Build markdown once, serve fast.

### Setup (5 minutes)

```bash
# 1. Install dependencies
pip install markdown pygments

# 2. Convert all files
cd /home/opencode/data/work/bbsengine6/handbook
make convert

# 3. Enable Apache
sudo a2enmod rewrite
sudo cp handbook/.htaccess /etc/apache2/sites-available/handbook.conf
# or just copy .htaccess to handbook/ directory for per-directory config

# 4. Restart Apache
sudo systemctl restart apache2

# 5. Visit https://bbsengine.org/handbook/
```

### Workflow

When you update markdown:

```bash
# Regenerate HTML
cd handbook
make convert
```

Or watch for changes:

```bash
cd handbook
make watch  # Auto-converts on file changes
```

**Advantages:**
- Faster page loads (static files)
- Lower CPU usage
- Standard Apache serving
- Can cache aggressively

**Disadvantages:**
- Must rebuild on changes
- Two files per document
- Build step in deployment

---

## Adding Documentation

### 1. Create markdown file

```bash
# Example: Create new documentation
vim handbook/specs/my-feature.md
```

Start with a title:

```markdown
# My Feature Documentation

This is about my feature.

## Details

More details...
```

### 2. View it

**Runtime approach:**
- Just visit: `http://localhost:5000/handbook/specs/my-feature/`
- No build needed!

**Static approach:**
```bash
make convert
# Then visit: `http://localhost/handbook/specs/my-feature/`
```

### 3. Update existing docs

Same process - just edit the markdown file.

---

## Common Tasks

### View HTML output (runtime)

```bash
python3 app.py
# Visit: http://localhost:5000/handbook/
```

### Generate HTML files (static)

```bash
make convert
# Files appear at handbook/*/index.html
```

### Watch for changes (static)

```bash
make watch
```

### Clean up backups

```bash
make clean
```

### Show help

```bash
make help
```

---

## File Structure

After editing your markdown:

```
handbook/
├── index.md                    ← Homepage
├── README.md                   ← About handbook
├── database.md                 ← Database docs
├── specs/
│   ├── index.md               ← Specs overview
│   ├── architecture.md         ← Architecture
│   ├── console/
│   │   ├── index.md           ← Console overview
│   │   └── main-console.md    ← Main console
│   └── ...
└── csrf/                       ← CSRF docs
    ├── README.md
    └── ...
```

URLs map to file paths:
- `handbook/database.md` → `/handbook/database/`
- `handbook/specs/index.md` → `/handbook/specs/`
- `handbook/specs/architecture.md` → `/handbook/specs/architecture/`

---

## Troubleshooting

### Flask app won't start

```bash
# Check Python dependencies
python3 -c "import flask, markdown; print('OK')"

# If missing:
pip install flask markdown pygments
```

### Markdown not converting

```bash
# Check syntax
python3 convert_markdown.py handbook/test.md

# Or test directly
python3 -c "
import markdown
content = open('handbook/test.md').read()
html = markdown.markdown(content)
print(html[:100])
"
```

### Apache not serving

```bash
# Check Apache config
sudo apache2ctl configtest

# Check logs
sudo tail -f /var/log/apache2/error.log

# Verify .htaccess enabled
grep AllowOverride /etc/apache2/apache2.conf
```

---

## Which Approach?

| Need | Choose |
|------|--------|
| Want to test locally | **Runtime (app.py)** |
| Frequently updating docs | **Runtime (Flask)** |
| Maximum performance | **Pre-convert (static)** |
| Simple setup | **Pre-convert (.htaccess)** |
| Production use | **Either, with proper config** |

---

## Next Steps

### Read Full Guides

- **Runtime conversion:** See [RUNTIME_CONVERSION.md](RUNTIME_CONVERSION.md)
- **Static conversion:** See [SETUP.md](SETUP.md)

### Apache Configuration

- **Runtime with mod_wsgi:** `handbook-wsgi.conf`
- **Static with .htaccess:** `.htaccess` in handbook directory

### Build Automation

- **Makefile:** Run `make help` for all targets

---

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | Flask application (runtime) |
| `wsgi.py` | Apache mod_wsgi entry point |
| `convert_markdown.py` | Standalone converter |
| `Makefile` | Build automation |
| `.htaccess` | Apache per-directory config |
| `handbook-wsgi.conf` | Apache site config (runtime) |
| `bbsengine-handbook.conf` | Apache site config (static) |

---

## Example: Complete Setup (Runtime)

```bash
# 1. Install packages
pip install flask markdown pygments

# 2. Create first doc
echo "# Home" > handbook/index.md
echo "Welcome to docs" >> handbook/index.md

# 3. Run development server
cd handbook
python3 app.py

# 4. Open browser to http://localhost:5000/handbook/

# 5. Create more docs
echo "# Database" > handbook/database.md
echo "Database schema..." >> handbook/database.md

# 6. Reload browser - it's already there!
```

Done! Zero build steps, changes visible instantly.

---

## Example: Complete Setup (Static)

```bash
# 1. Install packages
pip install markdown pygments

# 2. Create docs directory with markdown
mkdir -p handbook/specs
echo "# Home" > handbook/index.md
echo "# Specs" > handbook/specs/index.md

# 3. Convert to HTML
cd handbook
make convert

# 4. Set up Apache
sudo cp .htaccess /var/www/handbook/
sudo systemctl restart apache2

# 5. Visit http://localhost/handbook/

# 6. Update and rebuild
echo "# Architecture" > handbook/specs/architecture.md
make convert
```

Done! Now docs are served as static files.

---

For more details, see the full documentation guides.
