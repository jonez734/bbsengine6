# Router

> Status: canonical. Updated 2026-09-04.

The `/engine/router.php` entry point is the front door for the
public website (`zoidtechnologies.com`, `bbsengine.org`). It maps
clean URLs to handler functions and falls through to the
`browse.tmpl` template.

## Overview

| Item | Value |
|---|---|
| Source path | `/home/opencode/data/work/bbsengine6/engine/router.php` |
| **Current live path** | `/srv/www/vhosts/zoidtechnologies.com/html/engine/router.php` |
| Legacy path (now incorrect) | `/srv/www/bbsengine6/php/router.php` |
| Router URL (web) | `https://zoidtechnologies.com/engine/router.php` |
| `TEOSFILEPATH` | `/srv/www/zoid6/teos/` (named constant; set to `""` to disable the `top.` ltree prefix) |
| `TEOSLABELPREFIX` | `top` (named constant) |
| `DOCROOT` | `/srv/www/vhosts/zoidtechnologies.com/html/` |

**Note on deployment paths.** Two paths appear in the source
material:

- `handbook/ROUTER.md` (the older operational guide) lists the
  source path as `/srv/www/bbsengine6/php/router.php`.
- `bbsengine6/router.md` (the post-mortem of the WSOD fix) lists
  the live path as `/srv/www/vhosts/zoidtechnologies.com/html/engine/router.php`.

The live path under
`/srv/www/vhosts/zoidtechnologies.com/html/engine/` is the **current
canonical path** — the WSOD fix, the directory-listing hardening,
and the `make engine` deploy target all serve from there. The other
path is the historical location; both are documented here for
operators digging through older issues.

## Deployment

### Layout

```
bbsengine6/
├── Makefile                    # Root build orchestrator
├── engine/
│   ├── Makefile                # Stage + deploy engine files
│   ├── router.php              # Source for /engine/router.php
│   ├── login.php  logout.php  join.php
│   └── …
├── php/                        # Library (engine.php, util.php, …)
├── skin/  js/  smarty/
```

### Deploy commands

```bash
# Stage and deploy engine files (php/skin/js/smarty → /srv/www/bbsengine6/)
cd /home/opencode/data/work/bbsengine6 && make engine

# Deploy the www site (htaccess with router rules → /srv/www/vhosts/…)
cd /home/opencode/data/work/zoid6/sites/www && make prod
```

The `engine` target chains three steps:

1. `stage` — copies `php/`, `skin/`, `js/`, `smarty/` into the
   staging directory `/srv/www/bbsengine6/`.
2. `deploy` — rsyncs staging to production.
3. `deploy-router` — copies `engine/router.php` to the web-accessible
   `/engine/` directory under the live docroot.

## URL structure

```
https://zoidtechnologies.com/
├── engine/ (web-accessible PHP from bbsengine6)
│   ├── router.php              (router entry point)
│   ├── login.php  logout.php  join.php
├── achilles/                   (static site — has own code)
├── empyre/                     (static site — has own code)
├── murdermotel/                (static site — has own code)
└── [clean URLs]                → /engine/router.php
```

The static-site prefixes (`/achilles/`, `/empyre/`,
`/murdermotel/`) must be matched by their own directories and
**processed before** the router rewrite — they have their own code
and should never reach the router.

## htaccess rules (in `www/.htaccess`)

```apache
RewriteEngine On
RewriteBase /

# Router for teos blurbs (clean URLs like /comp/, /ec/, etc.)
# Handler chain: blurb → folder → markdown → error
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_FILENAME} !-f
RewriteRule ^([a-zA-Z0-9_/-]+)$ /engine/router.php?mode=browse&uri=$1 [last,qsappend]

# Teos routes (legacy — still works for /teos/ URLs)
RewriteRule ^teos/(.+)$ php/teos.php?path=$1 [last,QSA]
```

The first rule passes any non-static URI to the router with
`?mode=browse&uri=<path>`. The `!d` / `!f` conditions prevent
Apache from re-routing real files and directories.

## Routing logic

1. Apache checks if the request matches a static file or directory.
2. If not, it routes to `/engine/router.php?mode=browse&uri=…`.
3. The router walks handlers in order:
   - **blurb** — `engine.__blurb` table (database-backed content)
   - **folder** — `TEOSFILEPATH` (default `/srv/www/zoid6/teos/`) for
     directories
   - **markdown** — `TEOSFILEPATH` for `.md` files
   - **error** — 404 page (always returns a non-empty string)
4. The first handler that produces output wins.
5. If no handler matches, the router calls `router_handleError()`
   which always returns a 404 HTML page and sets
   `http_response_code(404)`.

## Handler return-value contract

Handlers return either:

- A non-empty string — emitted as the response body. The router
  stops walking handlers.
- `ROUTER_NEXT` / `null` / `false` — the router continues to the
  next handler.

Returning `null` or `false` is treated as "try the next handler",
not "stop and emit this empty body" (this is the post-fix
contract; see "Recent fixes" below).

## Directory listing

When the folder handler renders a TEOS directory (e.g.
`/rec/arts/tv/mash/`), `router_collectDirectoryItems()` walks the
on-disk contents with `scandir()` and turns each entry into an item
record. The result is sorted by filename (case-insensitive) and
then passed through `router_dedupeItems()` to collapse any
remaining case-variant duplicates before the data is handed to the
`browse.tmpl` template.

### Skipping backup and junk files

`scandir()` returns every visible filesystem entry, which includes
leftovers from editors and patch tools. `router_isIgnoredEntry()`
filters out the following patterns before an entry is added to the
listing:

- `.`-prefixed entries (dotfiles), including `..` and `.`
- Anything ending in one or more `~` (emacs backup; multi-tilde
  like `.~~`)
- vim swap files: `.swp`, `.swo`, `.swn` (case-insensitive)
- `.bak`, `.orig`, `.rej` (patch rejects)
- `.tmp`, `.temp`, `.save` (case-insensitive)
- emacs lockfiles: `#name#`

This list is centralized in `router_isIgnoredEntry()` so additional
patterns can be added in one place. The companion test
(`/home/opencode/data/work/teos/www/php/test_www_mash_no_duplicates.php`)
covers the filter and the regression scenario (real mash directory
plus leftover `~` files yields exactly the 7 real blurbs, not 9).

## Engine web modules

The `/engine/` directory holds web-accessible PHP modules:

```
engine/
├── router.php     # Handler-registry router
├── login.php      # Member authentication
├── logout.php     # Member logout
└── join.php       # Member registration
```

All modules use the `*_run()` functional-style entry point pattern.
`__DIR__` is used for `require_once` paths. Cross-namespace imports
use `use` statements. `\bbsengine6\page\redirect()` is the canonical
redirect helper (replaces the deprecated bare `header()` redirect).

### Security (post Phase 3)

- **Path traversal prevention** — the router validates all
  user-supplied paths through `\bbsengine6\util\safe_path_web()`
  before filesystem access. A traversal attempt returns 404.
- **Cookie domain** — uses `\config\SESSIONCOOKIEDOMAIN` instead of
  hardcoded values.
- **Credits validation** — non-SYSOP users cannot set the credits
  field; it always defaults to 42.
- **Session safety** — null checks on session variables in logout;
  logout requires a CSRF token and calls `session_destroy()`
  (Phase 3 finding 3.11).

## Recent fixes

These were the post-mortems captured in the WSOD fix and the
`router_isIgnoredEntry()` work. They are kept here as a changelog
so operators diagnosing the same symptoms can match against known
fixes.

### WSOD on `/teos/rec/` (and similar)

**Symptom.** `https://zoidtechnologies.com/teos/rec/` returned a
WSOD (white screen of death — empty response body). Other paths
(`/teos/rec/rec/arts/`) also returned empty bodies.

**Root causes.** Five independent bugs:

1. `router_displayDirectoryListing` skipped subdirectories
   (`continue`d on `is_file($fullpath)`). The `rec/` directory
   contains only `arts/` (a subdirectory), so the listing was empty
   — and an empty string in the response body is a WSOD.
2. `router_displayDirectoryListing` called `safe_path_web()` with
   an absolute path. `safe_path_web()` rejects absolute paths in
   components (a security feature). The first call inside
   `router_handleFolder` succeeded; the second call inside
   `router_displayDirectoryListing` failed. The function returned
   `false`, the directory listing returned `null`, and the router
   emitted an empty string.
3. `router_handleError()` returned `null` when no handler matched.
   The HTTP layer echoed nothing — a 404 must be returned instead.
4. `TEOSURL` was defined early as `""` at the top of `router.php`,
   before the HTTP block tried to redefine it to `"/teos"`. The
   `if (!defined)` guard made the override a no-op. Directory
   listing links were rendered as relative paths
   (`rec/arts/`), which the browser resolved against the current
   URL, producing duplicated paths like `/rec/rec/arts/`.
5. The handler loop returned `null` / `false` as a successful
   result. Any handler returning `null` or `false` was treated as
   the response body.

**Fixes.**

- Removed the early `TEOSURL` and `TEOSDIR` `define` calls that
  pinned the constants to empty strings. They are defined only
  inside the HTTP execution block.
- Added `router_get_teosurl()` and `router_get_teosdir()` helpers
  that read from `TEOSURL` / `TEOSDIR` (constants or env vars) and
  fall back to sane defaults. Handlers and templates use these
  helpers so they always have a non-empty value.
- `router_displayDirectoryListing` now uses `realpath($dirpath)`
  (the caller has already validated the path), includes
  subdirectory entries (each with `is_dir => true` and a trailing
  `/` rendered next to the link), and always returns a non-empty
  string. On `scandir` failure or `realpath` failure it returns
  the result of `router_handleError` (a 404 page) rather than
  `null`.
- `router_handleError` always returns a 404 HTML string, calls
  `http_response_code(404)`, and falls back to a built-in 404 if
  `bbsengine6\page\error` is missing or returns null.
- The main handler loop continues to the next handler on
  `ROUTER_NEXT`, `null`, or `false`, and only returns a non-empty
  string. If no handler matches, it calls `router_handleError($uri)`.
- The HTTP entry point catches all `Throwable`s and emits a 500
  with a clean error message rather than a WSOD, and catches
  `null` / `false` returns and emits a 500 instead of an empty body.

**Regression tests** (`test_zoidtechnologies_comp.py`):

- `test_rec_index`, `test_rec_arts`, `test_rec_arts_magic` — rec
  blurb directory pages are non-empty (not WSOD).
- `test_nonexistent_404` — bogus paths (`rec/rec/arts`,
  `rec/arts/void`, `top/banana`, `rec/rec/rec`) return a non-empty
  response body.
- `test_rec_all_pages_nonempty` — every rec blurb subdirectory
  renders content.

### Directory listing duplicates (2026-07-29)

Editor backup files (e.g. `major-characters.md~`) and patch
rejects (`.rej`) were rendered as duplicates of the real blurbs in
folder listings.

**Fix.** `router_isIgnoredEntry()` (see "Skipping backup and junk
files" above) and `router_dedupeItems()` for case-variant
collapses. Regression test in
`/home/opencode/data/work/teos/www/php/test_www_mash_no_duplicates.php`.

## History

| Date | Change |
|---|---|
| 2026-07-29 | Directory listing skips editor backup / junk files (`router_isIgnoredEntry`) and dedupes case-variant filenames (`router_dedupeItems`). Fixes the `/rec/arts/tv/mash/` regression. |
| 2026-06-15 | Security fixes + modernization (path traversal, functional style, namespace imports, redirect helper). |
| 2025-06-15 | Router moved to `/engine/router.php` for clean URL support. The web root previously held `/router.php` with a shim. |

## Deployment checklist

- [ ] `bbsengine6/engine/router.php` is the source of truth.
- [ ] `make engine` from `bbsengine6/` to stage + deploy.
- [ ] `make prod` from `zoid6/sites/www/` to deploy the
      www-site `htaccess` with the router rewrite rule.
- [ ] Apache modules `mod_rewrite` and `mod_php` are enabled.
- [ ] `/srv/www/vhosts/zoidtechnologies.com/html/engine/router.php`
      is the live file (post-deploy).
- [ ] `TEOSFILEPATH` points at the directory that holds the on-disk
      blurbs (`/srv/www/zoid6/teos/` by default).
- [ ] Smarty can find the `browse.tmpl` template.
- [ ] Regression tests pass: `php test_zoidtechnologies_comp.php` (in the `teos` repo) and the manual smoke list below.

## Manual smoke test

```bash
# Browse to a known blurb
curl -fsSL https://zoidtechnologies.com/rec/arts/tv/mash/ | head

# Browse to a known folder
curl -fsSL https://zoidtechnologies.com/rec/ | head

# 404 is a non-empty body
curl -sS -o /dev/null -w '%{http_code}\n' \
    https://zoidtechnologies.com/rec/rec/arts/

# Static site prefix is NOT routed to engine/router.php
curl -fsSL https://zoidtechnologies.com/achilles/ | head
```

If any of these return empty bodies, the router is regressed —
re-run the regression tests in `test_zoidtechnologies_comp.py`.

## See also

- [`../ROBUSTNESS_REVIEW.md`](../ROBUSTNESS_REVIEW.md) — Phase 3
  covers PHP web layer hardening (cookie attributes, CSRF, safe
  paths, log redaction). Phase 5 has the regression test list.
- [`../SPEC.md`](../SPEC.md#4-php-web-layer) — engine/router.php's
  place in the PHP web layer.
- [./DEPLOYMENT.md](./DEPLOYMENT.md) — Apache deployment paths,
  systemd units, log rotation.
- [./SECURITY.md](./SECURITY.md) — security overview.
