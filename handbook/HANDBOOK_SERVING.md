# Handbook Serving

> Status: canonical. Updated 2026-09-04.
> Replaces: `RUNTIME_CONVERSION.md`.

Two ways to serve the handbook Markdown under Apache:

1. **Runtime conversion (recommended)** — Flask app reads `.md` files
   on demand and renders them. No build step; edits go live
   immediately. Used on `bbsengine.org`.
2. **Pre-built static HTML** — `convert_markdown.py` walks the
   handbook tree, writes `<name>/index.html`, and Apache serves
   plain files. Faster first-byte but every edit needs a rebuild.

This document covers both, the `convert_markdown.py` tool, the
handbook Makefile, and the Flask app's WSGI entry point.

## Runtime conversion (Flask)

### Files

| File | Purpose |
|---|---|
| `handbook/app.py` | Flask application: routing, breadcrumb, LRU cache, HTML template |
| `handbook/wsgi.py` | WSGI entry point for mod_wsgi / uWSGI / gunicorn |
| `handbook/handbook-wsgi.conf` | Apache mod_wsgi config (use with [./DEPLOYMENT.md](./DEPLOYMENT.md)) |

### How it works

```
Request → Apache → mod_wsgi (or uwsgi) → wsgi.py → app.py
                                                ↓
                                          read .md file
                                                ↓
 convert_markdown (cached)
                                                ↓ render HTML template
                                                ↓
                                            Response
```

### URL routing

`app.py`'s single route `/handbook/<path:path>` resolves the request
to a Markdown file in the handbook directory, with these rules:

| URL | Resolves to |
|---|---|
| `/handbook/` | `index.md` |
| `/handbook/database` | `database.md` |
| `/handbook/database/` | `database.md` (trailing slash trimmed) |
| `/handbook/specs/architecture` | `specs/architecture.md` |
| `/handbook/specs/` | `specs/index.md` if present, else directory listing |
| `/handbook/specs` | same as above |

Directory listings are rendered by `list_directory()` when no
`index.md` is present. Each entry shows a file-type icon (folder,
markdown, other) and a link to the relative URL.

### Caching

`convert_markdown()` is wrapped in `@lru_cache(maxsize=128)`. The
cache is keyed by raw Markdown content, so re-rendering the same file
is free. Cache hits are typical: the handbook has fewer than 128
distinct pages and most requests touch the same few.

Tune `MAX_CACHE_SIZE` in `app.py` if the handbook grows past 128
files or if memory becomes tight:

```python
MAX_CACHE_SIZE = 256
```

### Security

The handler does these checks before serving a file:

- Path must resolve inside `HANDBOOK_DIR` (rejects `../` traversal
  with HTTP 403).
- File must exist and be a regular file.
- File reads are UTF-8 with explicit error handling (HTTP 500 on
  decode failure).

The breadcrumb labels and directory-listing labels are run through
`markupsafe.escape()` before interpolation. Markdown rendering uses
`extensions=['toc', 'tables', 'fenced_code', 'codehilite', 'extra']`;
`codehilite` uses Pygments for syntax highlighting.

### Running locally (development only)

```bash
cd handbook
python3 app.py
# Visit http://localhost:5000/handbook/
```

This uses Flask's built-in development server. Single-threaded, no
auto-restart, not safe for any traffic beyond the developer
themselves. For anything else, see [./DEPLOYMENT.md](./DEPLOYMENT.md).

### Running under Apache

Three deployment paths — full detail in [./DEPLOYMENT.md](./DEPLOYMENT.md):

| Path | Config snippet | Trade-off |
|---|---|---|
| **mod_proxy_uwsgi (production)** | uwsgi → Apache `ProxyPass uwsgi://...` | Best isolation |
| mod_wsgi | `handbook-wsgi.conf` | Simpler, no extra service |
| mod_proxy + gunicorn | systemd unit → Apache `ProxyPass http://...` | Familiar gunicorn ops |

> The gunicorn path is **alternative / non-production** on
> `bbsengine.org`. The production host runs uWSGI; see
> [`DEPLOYMENT.md`](./DEPLOYMENT.md#gunicorn--mod_proxy-alternative)
> for the canonical deployment and a copy of the shipped
> `handbook-gunicorn.service`.

The `handbook/handbook-wsgi.conf` file is the mod_wsgi option:

```apache
WSGIDaemonProcess handbook user=www-data group=www-data threads=5 processes=2
WSGIScriptAlias /handbook /home/opencode/data/work/bbsengine6/handbook/wsgi.py

<Directory /home/opencode/data/work/bbsengine6/handbook>
    WSGIProcessGroup handbook
    WSGIApplicationGroup %{GLOBAL}
    Require all granted

    <IfModule mod_headers.c>
        Header set X-Content-Type-Options "nosniff"
        Header set X-Frame-Options "SAMEORIGIN"
        Header set X-XSS-Protection "1; mode=block"
        Header set Referrer-Policy "strict-origin-when-cross-origin"
    </IfModule>

    <IfModule mod_expires.c>
        ExpiresActive On
        ExpiresDefault "access plus 1 hour"
    </IfModule>

    <IfModule mod_deflate.c>
        AddOutputFilterByType DEFLATE text/html text/plain text/xml application/json text/javascript
    </IfModule>
</Directory>

<IfModule mod_alias.c>
    AliasMatch ^/handbook/(.*\.(?:css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot))$ \
        /home/opencode/data/work/bbsengine6/handbook/static/$1
</IfModule>
```

Enable and restart:

```bash
sudo a2ensite handbook-wsgi.conf
sudo systemctl restart apache2
```

To ship new code in the Flask app itself: restart the handbook
service (uWSGI / gunicorn) or the entire Apache (mod_wsgi).

### Customization

**HTML template** — `HTML_TEMPLATE` constant in `app.py`. Modify the
inline CSS to change appearance. The template uses Jinja
`{{ ... }}` and `{{ ... | safe }}` interpolation.

**Markdown extensions** — `get_markdown_extensions()` in `app.py`:

```python
def get_markdown_extensions():
    return [
        "toc",
        "tables",
        "fenced_code",
        "codehilite",
        "extra",
    ]
```

**HTTP cache TTL** — change `ExpiresDefault "access plus 1 hour"` in
the Apache config.

**Cache-Control on responses** — `app.config["JSON_SORT_KEYS"]` is
set to `False`; add per-route cache headers via Flask's
`make_response()` if needed.

### Performance characteristics

| Aspect | Runtime | Pre-built static |
|---|---|---|
| Build step | None | `make convert` (or watch) |
| First request | ~50-100ms (markdown parse) | <10ms |
| Cached request | <1ms (LRU hit) | <10ms |
| Storage | markdown only | markdown + html (+20-30%) |
| Update workflow | edit + reload browser | edit + `make convert` |

For the handbook (low traffic, frequent edits), runtime wins. For
high-traffic static docs that change once a deployment, pre-built
static wins.

## Pre-built static HTML

### Files

| File | Purpose |
|---|---|
| `handbook/convert_markdown.py` | Standalone Markdown → HTML converter |
| `handbook/Makefile` | Build automation (`convert`, `watch`, `stage`, `stage-convert`) |
| `handbook/bbsengine-handbook.conf` | Apache site config for static serving |

### Convert a single file

```bash
python3 handbook/convert_markdown.py handbook/README.md
```

`convert_markdown.py` accepts a file or directory path, walks the
tree, and writes `<filename>/index.html` for each Markdown source. It
auto-extracts the page title from the first H1, runs Pygments syntax
highlighting, generates a TOC, and embeds responsive CSS in the
output.

CLI flags:

| Flag | Effect |
|---|---|
| `--recursive` | Walk directories recursively |
| `--output DIR` | Custom output directory |
| `-v` | Verbose logging |

### Convert the whole handbook

```bash
cd handbook
make convert
```

Internally:

```bash
python3 convert_markdown.py . --recursive
```

### Watch for changes

```bash
cd handbook
make watch
```

Requires `watchdog` (`pip install watchdog`). Uses `watchmedo
shell-command` to invoke `convert_markdown.py` on every `.md` save.

### Stage to webroot

The `Makefile` `stage` and `stage-convert` targets rsync the
handbook (or pre-converted HTML) to the production webroot. They
expect `$(VERSION)` to be set:

```bash
cd handbook
make stage       # rsync .md files only
make stage-convert # convert markdown to .txt and stage
```

Targets:

| Target | Effect |
|---|---|
| `make convert` | Convert all Markdown to HTML in place |
| `make watch` | Auto-convert on file changes |
| `make stage` | rsync handbook files to `/srv/www/vhosts/www.bbsengine.org/html/handbook/$(VERSION)/` |
| `make stage-convert` | Convert Markdown to plain-text and stage |
| `make convert-tmpl` | Convert Markdown to Smarty `.tmpl` via `bbsengine6.md2tpl` |
| `make clean` | Remove `.md~`, `.bak`, `__pycache__` |
| `make install-deps` | `pip install markdown pygments` |
| `make help` | List targets |

### Apache static config

`bbsengine-handbook.conf` is the full Apache site config for static
serving. It enables MIME types for `.md` (`text/markdown`), gzip
compression for text, 7-day cache for HTML/Markdown, 1-day cache for
JSON, and blocks backup files (`.md~`, `.bak`) and dotfiles.

Three ways to install it:

```bash
# A) Alias into existing vhost
sudo cp handbook/bbsengine-handbook.conf /etc/apache2/conf-available/
sudo a2enconf bbsengine-handbook
sudo systemctl restart apache2

# B) Standalone site
sudo cp handbook/bbsengine-handbook.conf /etc/apache2/sites-available/
sudo a2ensite bbsengine-handbook.conf
sudo systemctl restart apache2

# C) Per-directory .htaccess (already shipped in handbook/.htaccess)
```

Required Apache modules: `mod_rewrite`, `mod_headers`, `mod_mime`,
`mod_deflate`, `mod_expires`, `mod_autoindex`, `mod_alias`. Enable:

```bash
sudo a2enmod rewrite headers mime deflate expires autoindex
sudo systemctl restart apache2
```

## Choosing a model

| Need | Use |
|---|---|
| Edit docs often, want changes live immediately | Runtime (Flask) |
| Want maximum page-load speed | Pre-built static |
| Want minimum operational surface | Pre-built static (`.htaccess` only) |
| Already running mod_wsgi or uWSGI for other apps | Runtime (Flask) — reuse the WSGI stack |
| Need to roll back to a known-good doc version | Pre-built static (version the HTML, not just the Markdown) |

The handbook on `bbsengine.org` runs runtime conversion (Flask +
mod_wsgi) — most docs change weekly and the live-reload saves a
deploy cycle per edit.

## Troubleshooting

**Flask app won't start.** `python3 -c "import flask, markdown;
print('OK')"` — if `ModuleNotFoundError`, `pip install flask markdown
pygments`.

**Pages load slowly.** Increase `MAX_CACHE_SIZE`. Profile
`convert_markdown()` with `time.time()` deltas to confirm the
converter (not Apache) is the bottleneck.

**Directory listing missing entries.** Backups and hidden files
(`*~`, `.bak`, dotfiles) are filtered. Make sure the files you
expect aren't editor leftovers.

**404 on `/handbook/specs/`.** No `specs/index.md` and the route
falls through to a directory listing. Add `specs/index.md` if you
want a real landing page.

**Apache serves raw `.md` instead of converting.** Runtime
conversion requires mod_wsgi/uWSGI/gunicorn. If you used the static
config, Apache hands out the raw Markdown file as `text/markdown`
(which is fine for the static model but not the runtime model).

**Pre-built HTML stale.** Re-run `make convert` or rely on `make
watch` to keep them in sync during editing.

## See also

- [./DEPLOYMENT.md](./DEPLOYMENT.md) — Apache deployment paths in
  detail (mod_proxy_uwsgi recommended).
- [./QUICKSTART.md](./QUICKSTART.md) — five-minute first-run.
- [./ROUTER.md](./ROUTER.md) — the public-website router, which
  serves `engine/*` URLs and is a separate code path from the
  handbook.
