# zoid6 router

## Overview

- Router location: `/srv/www/bbsengine6/php/router.php`
- Router URL: `https://zoidtechnologies.com/router.php`
- TEOSFILEPATH: `/srv/www/zoid6/teos/` (named constant)
- TEOSLABELPREFIX: `top` (named constant - can be set to "" to remove prefix)
- DOCROOT: `/srv/www/vhosts/zoidtechnologies.com/html/`

## URL Structure

```
https://zoidtechnologies.com/
├── achilles/      (static site - has own code)
├── empyre/        (static site - has own code)
├── murdermotel/   (static site - has own code)
├── teos/          (static files: seo.php, about.php, etc)
└── [everything else] → /router.php
```

## Static Site Prefixes

These paths are handled by their own directories/code and should be processed BEFORE the router:

- `/achilles/`
- `/empyre/`
- `/murdermotel/`

## Routing Logic

1. Apache checks if request matches a static site directory first
2. If not, routes to `/router.php?mode=...&uri=...`
3. Router checks:
   - Database (engine.sig table) for folder paths
   - TEOSFILEPATH (`/srv/www/zoid6/teos/`) for files/directories
4. If found: display content
5. If not found: show bbsengine6 404 error page

## htaccess Rules (in /teos/.htaccess)

```apache
RewriteEngine On
RewriteBase /teos/

# Static files within /teos/
RewriteRule ^robots.txt$ /teos/seo.php?mode=robotstxt [last,qsappend]
RewriteRule ^sitemap.xml$ /teos/seo.php?mode=sitemapxml [last,qsappend]
RewriteRule ^favicon\.ico$ - [last]
RewriteRule ^about[/]?$ /teos/about.php [last]
RewriteRule ^credits\.html$ /teos/page.php?mode=view&page=credits [last,qsappend]
RewriteRule ^credits$ /teos/page.php?mode=view&page=credits [last,qsappend]

# Route to router.php at root
RewriteRule ^detail$ /router.php?mode=detail&uri=/ [last,qsappend]
RewriteRule ^([a-zA-Z0-9/-]+)detail$ /router.php?mode=detail&uri=$1 [last,qsappend]

RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_FILENAME} !-f
RewriteRule ^([a-zA-Z0-9_/-]+)$ /router.php?mode=browse&uri=$1 [last,qsappend]

RewriteRule ^$ /router.php?mode=browse&uri=ec [last,qsappend]

RewriteRule ^login[/]?$ /teos/login.php [last]
RewriteRule ^logout[/]?$ /teos/logout.php [last]

RewriteRule ^([a-zA-Z0-9_/-]+/[-a-zA-Z0-9_]+-blurb\.md)$ /router.php?mode=blurb&path=$1 [last,qsappend]
```

## Requirements

- All modules must handle errors gracefully (never show 500 errors)
- If a required file fails to load, fall back to bbsengine6's 404 page
- Use named constants for file paths (TEOSFILEPATH, etc)

## teos

- teos shows the content of folders: `comp/lang/python/`, `alt/paranormal/`, `ec/`
- A folder can have blurbs in it (and eventually other content types)
- In processing, prepend a named constant to ltree paths so it can be set to "" (empty) instead of assuming "top"

## Future Phases

### Phase 3: Full Router Dispatch
- Route ALL paths through router.php (not just /teos/*)
- Dispatch based on URI prefix
- Static sites checked first via Apache config order

### Phase 4: Remove /teos/ Prefix
- Move .htaccess from /teos/ to root level
- Update TEOSURL constant from `/teos/` to `/`
- Router handles all non-static paths at root level
