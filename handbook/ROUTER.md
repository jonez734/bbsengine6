# zoid6 router

## Overview

- Router location: `/srv/www/bbsengine6/php/router.php` (source)
- Router URL: `https://zoidtechnologies.com/engine/router.php` (web-accessible)
- TEOSFILEPATH: `/srv/www/zoid6/teos/` (named constant)
- TEOSLABELPREFIX: `top` (named constant - can be set to "" to remove prefix)
- DOCROOT: `/srv/www/vhosts/zoidtechnologies.com/html/`

## Deployment

### Makefile Structure

The `bbsengine6/Makefile` now uses an `engine/` subdirectory for orchestration:

```
bbsengine6/
├── Makefile           # Main makefile - calls engine/Makefile
├── engine/
│   └── Makefile       # Orchestrates staging and deployment
├── php/
│   └── router.php     # Router source (backend library)
├── skin/
├── js/
└── smarty/
```

### Deployment Commands

```bash
# Deploy engine files (includes router.php to /engine/)
cd /home/opencode/data/work/bbsengine6 && make engine

# Deploy www site (includes htaccess with router rules)
cd /home/opencode/data/work/zoid6/sites/www && make prod
```

### What the engine target does

1. `stage` - Copies php/skin/js/smarty to staging (`/srv/www/bbsengine6/`)
2. `deploy` - Rsyncs staging to production
3. `deploy-router` - Copies `router.php` to web-accessible `/engine/` directory

## URL Structure

```
https://zoidtechnologies.com/
├── engine/            (web-accessible PHP from bbsengine6)
│   └── router.php     (router entry point)
├── achilles/          (static site - has own code)
├── empyre/            (static site - has own code)
├── murdermotel/       (static site - has own code)
└── [clean URLs]       → /engine/router.php
```

## htaccess Rules (in www/.htaccess)

```apache
RewriteEngine On
RewriteBase /

# Router for teos blurbs (clean URLs like /comp/, /ec/, etc.)
# Handler chain: blurb -> folder -> markdown -> error
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_FILENAME} !-f
RewriteRule ^([a-zA-Z0-9_/-]+)$ /engine/router.php?mode=browse&uri=$1 [last,qsappend]

# Teos routes (legacy - still works for /teos/ URLs)
RewriteRule ^teos/(.+)$ php/teos.php?path=$1 [last,QSA]
```

## Routing Logic

1. Apache checks if request matches a static file/directory first
2. If not, routes to `/engine/router.php?mode=browse&uri=...`
3. Router checks handlers in order:
   - **blurb** - Database (engine.__blurb table)
   - **folder** - TEOSFILEPATH (`/srv/www/zoid6/teos/`) for directories
   - **markdown** - TEOSFILEPATH for .md files
   - **error** - 404 page
4. If found: display content
5. If not found: show bbsengine6 404 error page

## Static Site Prefixes

These paths are handled by their own directories/code and should be processed BEFORE the router:

- `/achilles/`
- `/empyre/`
- `/murdermotel/`

## Requirements

- All modules must handle errors gracefully (never show 500 errors)
- If a required file fails to load, fall back to bbsengine6's 404 page
- Use named constants for file paths (TEOSFILEPATH, etc)

## teos

- teos shows the content of folders: `comp/lang/python/`, `alt/paranormal/`, `ec/`
- A folder can have blurbs in it (and eventually other content types)
- In processing, prepend a named constant to ltree paths so it can be set to "" (empty) instead of assuming "top"

## Engine Web Modules

The `/engine/` directory contains web-accessible PHP modules:

```
engine/
├── router.php    # Main request router
├── login.php     # Member authentication (functional style)
├── logout.php    # Member logout (functional style)
└── join.php      # Member registration (functional style)
```

### Security (2026-06-15)

- **Path Traversal Prevention**: Router uses `\bbsengine6\util\safe_path_web()` to validate all user-supplied paths before filesystem access
- **Cookie Domain**: Uses `\config\SESSIONCOOKIEDOMAIN` instead of hardcoded values
- **Credits Validation**: Non-SYSOP users cannot set credits field (always defaults to 42)
- **Session Safety**: Null checks on session variables in logout

### Code Style (2026-06-15)

- **Functional Style**: All modules use `*_run()` entry point pattern
- **Consistent Paths**: Uses `__DIR__` for require_once paths
- **Namespace Imports**: Uses `use` statements for bbsengine6 namespaces
- **Redirect Helper**: Uses `\bbsengine6\page\redirect()` instead of deprecated functions

## History

- **2026-06-15**: Security fixes + modernization (path traversal, functional style)
- **2025-06-15**: Router moved to `/engine/router.php` for clean URL support
- **Prior**: Router was at `/router.php` (web root) with shim file
