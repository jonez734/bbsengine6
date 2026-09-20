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
   - **index** — root `/` or empty URI (renders `TEOSDIR/index.php`
     or `TEOSDIR/index.md`); pattern `^/?$`.
   - **blurb** — `engine.__blurb` table (database-backed content);
     pattern `[A-Za-z0-9_][A-Za-z0-9_./-]*` (hierarchical
     dot-path shape).
   - **folder** — `TEOSDIR` (default `/srv/www/zoid6/teos/`) for
     directories; no pattern (filesystem probe decides).
   - **markdown** — `TEOSDIR` for `.md` files; pattern
     `[A-Za-z0-9_][A-Za-z0-9_./-]*` (same shape as blurb, no
     trailing slash). Single-pass probe: the HTTP entry-point
     strips a trailing `.md` once at the top of the script
     (`preg_replace('/\.md$/', '', $path)`), so the handler
     only needs the bare `$reluri` probe; the previous
     `$reluri . '.md'` branch was dead code. The pattern
     deliberately has no `.md` suffix because the URI is
     already post-strip when the dispatch loop matches it —
     see the inline comment at `router_gethandlers()`
     (engine/router.php) for the contrast with the `page`
     handler.
   - **page** — Smarty `.tmpl` under `DOCUMENTROOT/skin/tmpl/`
     (e.g. `/contact-us` → `contact-us.tmpl`); two-pass probe
     (`<slug>.tmpl` then `<slug>` as-is); pattern
     `[a-z][a-z0-9-]*` (narrowest — bare lowercase slug).
     Two-pass is required here because `.tmpl` is NOT
     stripped at the entry-point (htaccess rewrites bare
     slugs into the router with no extension, so the
     handler has to append `.tmpl` itself).
4. Each handler entry may carry an optional `pattern` (PCRE
   regex, anchored with `^...$`). The dispatch loop
   `preg_match()`es the URI against the pattern; on miss the
   handler is skipped without invocation, avoiding filesystem/DB
   probes for obviously non-matching URIs. Patterns match the
   post-`.md`-strip URI (so `/contact-us`, not
   `/contact-us.md`). A `null` pattern means "always try".
   Compile failure is logged and falls through to handler
   invocation rather than silently swallowing the URI.
5. The first handler that produces output wins.
6. If no handler matches, the dispatch loop falls through to
   `router_handleError($uri)`, which logs, calls
   `\bbsengine6\page\error($msg, 404)` (which renders styled
   chrome via `displaypage()`), sets `http_response_code(404)`,
   and returns `ROUTER_RENDERED`. `error` is intentionally NOT
   in the registry — registering it would fire it twice on a
   miss. The post-loop fallback is the single point of truth
   for 404s.

## Handler return-value contract

Handlers return either:

- A non-empty string — emitted as the response body. The router
  stops walking handlers.
- `ROUTER_NEXT` — the router continues to the next handler.
- `ROUTER_RENDERED` — the handler rendered via `displaypage()`
  and the body is already on stdout; the dispatcher returns an
  empty string so the HTTP entry-point emits nothing more.
- `null` / `false` — the router continues to the next handler
  (treated identically to `ROUTER_NEXT`; preserved for callers
  that don't know about the sentinel).

Returning `null` or `false` is treated as "try the next handler",
not "stop and emit this empty body" (this is the post-fix
contract; see "Recent fixes" below).

`ROUTER_STOP` is no longer defined (no caller used it; the
empty-string foot-gun that motivated its retirement is replaced
by `ROUTER_RENDERED`).

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
  user-supplied paths through `router_safe_path_web()` (a
  thin wrapper around `\bbsengine6\util\safe_path_web()` that
  no-ops to `false` if the helper isn't loaded) before
  filesystem access. A traversal attempt returns 404.
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

### `router_handleError` double-body and the `ROUTER_RENDERED` sentinel (2026-09-19)

**Symptom.** After the 2026-09 fix (above), a 404 response
contained two `<title>` tags: the styled chrome from
`page\error()` and a trailing `<html><title>404</title>...`
fallback block emitted by the HTTP entry-point when
`router_handleError` returned `null`. Operators saw duplicate
chromes and `echo $router_result` printed an empty 500 instead
of stopping cleanly.

**Root cause.** The handler contract implicitly used an empty
string `''` as "I rendered via `displaypage()`; emit nothing
more." But the dispatch loop returned any non-empty string as
the response body and treated `null`/`false` as "try the next
handler". So `router_handleError` calling `page\error()` →
`displaypage()` (which echoes to stdout) and then returning
`null` left the dispatcher falling into "null → next handler",
the loop ended with `return router_handleError($uri)`, the
handler returned `null`, and the HTTP entry-point translated
`null` to "Router Error (null)" with a 500.

The same foot-gun existed for `router_handleBlurb`,
`router_displayMarkdownFile`, and `servePage` (in
`engine/serve-tmpl.php`): they each rendered via
`displaypage()` and returned `''`, which the dispatcher
treated as "short-circuit, emit empty body". Worked because
the HTTP entry-point's `echo ''` is a no-op, but the contract
was implicit and easy to break.

**Fix.** Introduced a `ROUTER_RENDERED` sentinel constant.
Handlers that render via `displaypage()` now return
`ROUTER_RENDERED`; the dispatch loop maps it to `''` and
short-circuits the chain. Removed `ROUTER_STOP` (no caller
returned it). Removed `error` from the registry — the
post-loop fallback is the single source of truth for 404s.

**Regression tests** (`php/test_router.php`):

- `Test 2` — `ROUTER_RENDERED` constant is defined.
- `Test 3b` — `error` is not in the registry.
- `Test 9` — `router()` returns `''` for a non-existent URI;
  stdout contains exactly one styled error (one `<title>`
  tag), not the pre-fix double-chrome shape.

### Dead `.md` probe in `router_handleMarkdown` (2026-09-19)

**Symptom.** Reading the dispatch chain: `router_handleMarkdown`
did a two-pass extension probe (`$reluri . '.md'`, then bare
`$reluri`) mirroring the `.tmpl` probe in
`router_handlePage`. The first pass was unreachable: the HTTP
entry-point already strips a trailing `.md` once at the top of
the script (`preg_replace('/\.md$/', '', $path)`), so by the
time the dispatch loop walks handlers the URI never carries
a `.md` suffix.

**Root cause.** Mirror reflex: the markdown handler was
written before the entry-point `.md`-strip existed. When the
strip was added, the markdown handler's `$uri . '.md'` branch
became dead code but stayed in place. The `.tmpl` branch in
`serve-tmpl.php` is still legitimate (`.tmpl` is NOT stripped
at the entry-point; htaccess rewrites bare slugs into the
router with no extension).

**Fix.** Removed the `$reluri . '.md'` probe from
`router_handleMarkdown`. Updated `serve-tmpl.php`'s doc
comments that previously referenced "router_handleMarkdown's
two-pass extension probe" to describe the actual remaining
two-pass handler (`page`) and explain why the markdown
handler dropped it.

**Regression tests** (`php/test_router.php`):

- `Test 6a` — handler body MUST NOT contain a `'$uri . .md'`
  probe (regression guard against re-introducing the dead
  branch).
- `Test 6b` — HTTP entry-point MUST strip trailing `.md`
  before dispatch (the contract that makes the dead-code
  removal safe).

### `router_handleIndex` referenced retired `ROUTER_STOP` (2026-09-19)

**Symptom.** After the `ROUTER_STOP` retirement in the same
release, `router_handleIndex` still returned `ROUTER_STOP`
after including `TEOSDIR/index.php`. In PHP 7 this returned
the literal string `"ROUTER_STOP"` which the HTTP entry-point
would echo (empty body); in PHP 8 it throws a fatal
"Undefined constant" on every `/` request that hits an
`index.php`.

**Root cause.** The C2 retirement of `ROUTER_STOP` was driven
by a global `define` removal but missed the call site at line
~228 of `router_handleIndex`. The variable-function dispatch
loop's `return ROUTER_STOP` was an unreachable shape
(`ROUTER_STOP` was never actually handled in the dispatcher),
but the literal constant name in the source was still valid
syntax until C2 removed the `define`.

**Fix.** Replaced with `ROUTER_RENDERED`. The included
`TEOSDIR/index.php` is expected to render to stdout (either
via `displaypage()` or direct `echo`); the sentinel tells the
dispatcher the body is already on the wire and the HTTP
entry-point should emit nothing more.

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
| 2026-09-19 | `pattern` attribute on handler registry entries (skip handler on URI regex miss); drop `error` from registry (single source of truth via post-loop fallback); `ROUTER_RENDERED` sentinel replaces the implicit empty-string-as-success contract; `ROUTER_STOP` retired; `teospath` → `$teosdir` typo fix in `router_handleMarkdown`; breadcrumb root `path` hardcoded to `'teos'` (matches `blurb.php::buildbreadcrumbs`); `router_safe_path_web()` wrapper extracted; `engine/serve-tmpl.php::servePage()` returns the new sentinel. |
| 2026-09-19 | Dead `$reluri . '.md'` probe dropped from `router_handleMarkdown` (HTTP entry-point strips `.md` once at the top of the script, so the branch was unreachable); `router_handleIndex` returns `ROUTER_RENDERED` after `include($indexfile)` instead of the retired `ROUTER_STOP`; `php/test_router.php` Tests 6a/6b pin the new contract. |
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
