## [Unreleased]

### fix(wwworg, folder, zoid6config): /handbook/6/specs/ links to /handbook/6/specs/, not /teos/specs/

The handbook directory listing at
`https://www.bbsengine.org/handbook/6/specs/` rendered
200 with a populated body but every internal link —
breadcrumb crumb `specs`, every item link
(`architecture`, `auth-bank`, `blurb`, …) — pointed at
`/teos/specs/...` instead of `/handbook/6/specs/...`.
Following any link 404'd on this vhost because there is
no `/teos/` rewrite target on www.bbsengine.org (that's
the zoidtechnologies.com vhost).

**Root cause.** `zoid6/php/zoid6config.php` defines
`TEOSURL="/teos/"` unconditionally. That file is pulled
in by `bbsengine6/php/blurb.php` (via the
`../../zoid6/php/bootstrap.php` and `zoid6config.php`
requires), which `php/folder.php`'s `isFolderVisible()`
indirectly loads when handling a directory listing.
Once loaded, the `TEOSURL` constant is `/teos/` for the
remainder of the request, shadowing the per-request
`putenv('TEOSURL=/handbook/6/')` that `engine/router.php`
issues when it detects the `/handbook/<v>/` URI prefix.

Two callers read `TEOSURL` as a constant (not via the
env-first `bbsengine6\util\teos_url()` helper):

  - `bbsengine6/skin/tmpl/function.teos.tmpl` lines 2-4
    use `{$smarty.const.TEOSURL}` to render breadcrumb
    hrefs and tooltip data URLs.
  - `bbsengine6/php/folder.php:231` (now line 250) built
    item URIs as `\TEOSURL . $fileuri`.

Both landed on `/teos/...` for handbook requests,
producing the broken links.

**Fix.**

1. **`zoid6/php/zoid6config.php`** — `TEOSURL` now
   honors an env-var override (mirroring the
   `if (!defined("ENGINEURL"))` pattern already used
   a few lines above). When `getenv('TEOSURL')` is set
   and non-empty, the constant reflects it; otherwise it
   defaults to `/teos/` so every other zoid6 consumer
   (zoidtechnologies.com teos, atlas, achilles, empyre,
   murdermotel, soctools, socrates, vulcan, …) sees no
   behavior change.
2. **`bbsengine6/www/org/htaccess-prod`** — adds
   `SetEnv TEOSURL /handbook/6/` next to the existing
   `SetEnv TEOS_BASEDIR` / `SetEnv TEOS_BASEURI` lines.
   The htaccess is the per-vhost source of truth; the
   `engine/router.php` `putenv()` from the detected
   prefix still runs for routes that hit the regex, and
   this SetEnv covers everything else (legacy /handbook/
   redirects, static asset requests, error pages).
3. **`bbsengine6/php/folder.php:231`** — switches the
   item URI from `\TEOSURL` (constant-only) to
   `\bbsengine6\util\teos_url()` (env-first, then
   constant). `folder.php` now matches
   `router_buildBreadcrumbs`'s prefix-resolution
   strategy and is robust to any future bootstrap
   reordering.

**Result.** `https://www.bbsengine.org/handbook/6/specs/`
renders breadcrumbs and item links under
`/handbook/6/specs/...`, and clicking them serves the
expected handbook chapter (or, for subfolders, the
expected subdirectory listing).

### fix(engine/router, wwworg): namespace-prefix + ENGINEURL duplicate guard

### fix(engine/router, wwworg): namespace-prefix + ENGINEURL duplicate guard

After `fix(wwworg): render chrome` landed on merlin, the
.org vhost log started surfacing three cascading errors
on `/handbook/6/<dir>/` URLs (which dispatch to
`router_handleFolder`):

```
routererror:folder visibility check failed: Call to
  undefined function bbsengine6\router\bbsengine6\folder\isFolderVisible()
routererror:directory listing render failed: ...
Trace: Constant ENGINEURL already defined in
  /srv/www/vhosts/www.bbsengine.org/html/config.php line 80
```

Two compounding root causes, both fixed in this commit.

**1. engine/router.php cross-namespace call sites were
missing the leading backslash.** router.php declares
`namespace bbsengine6\router;` (bfaca68). Unqualified
namespaced calls like `bbsengine6\folder\isFolderVisible($uri)`
resolve to `bbsengine6\router\bbsengine6\folder\isFolderVisible()`,
which doesn't exist (the function lives in
`bbsengine6\folder`). PHP's variable-function dispatch (used
in the handler chain via FQCN strings in
`router_gethandlers()`) honors call-site namespace
separately, but bare names in function bodies do not. The
fix adds a leading-backslash prefix on every
cross-namespace call site inside router.php that was
missed in bfaca68:

  - `router_handleFolder`: `\bbsengine6\folder\isFolderVisible`
    and `\bbsengine6\folder\isSysop` (the visible-cascade
    source).
  - `router_handleBlurb`: `\bbsengine6\blurb\display`. The
    sibling `isBlurb()` call directly above already used
    the leading backslash; `display()` was missed.
  - `router_displayDirectoryListing`:
    `\bbsengine6\displaypage`. The two other `displaypage()`
    call sites (`router_displayMarkdownFile` and the
    `route()` return) already use the leading backslash;
    this one was missed.
  - `router_handleIndex` and the HTTP entry-point catch
    block: `catch (Throwable $e)` → `catch (\Throwable $e)`.
    The bare `Throwable` typehint resolves to
    `bbsengine6\router\Throwable` which does not exist, so
    PHP refuses to bind the catch.

**2. www/org/config-prod.php line 80 bare-defined
ENGINEURL.** `php/zoid6/php/zoid6config.php` line 36
defines it first (with a `!defined()` guard). When
`engine/router.php → blurb.php → zoid6config.php` loads
(blurb is required at engine/router.php line 40),
ENGINEURL is already defined. When `page.php → session.php
→ config.php` loads later (page.php is required at
engine/router.php line 42; session.php line 12 requires
config.php), the bare
`define("ENGINEURL", "/engine/")` at config.php line 80
emits PHP `E_NOTICE` "Constant ENGINEURL already defined".
That notice surfaces via
`\bbsengine6\util\echo_traceback("folder visibility check
failed")` (engine/router.php:280) as the "Trace:" string
in the same log line. The fix wraps the define in
`if (!defined("ENGINEURL"))` so the engineurl is
idempotent across `zoid6config.php` + `config.php` load
order.

`tests/test_page_routes_chrome.sh` extended with a new
section [6] that probes `/handbook/6/specs/` and asserts
the response is the styled listing (chrome + render)
NOT the inline-list fallback, plus static checks that
engine/router.php's `bbsengine6\<ns>\<fn>()` call sites
all use the leading backslash (an `awk`-based
comment-stripped grep, the same approach as the
auth-bank render test) and that config-prod.php's
ENGINEURL define is guarded.

### fix(wwworg): render chrome (pageheader + topbar + content + pagefooter) on /contact-us, /about-us, /credits

Pre-fix, those three URIs all dispatched to
`engine/router.php` correctly and returned HTTP 200, but
the response body was a chrome shell wrapped around the
literal `NEEDINFO:content` placeholder (or, for
`/about-us`, a 404 with a stale `errormessage.tmpl`
fallback). Two compounding bugs:

1. `www/org/skin/tmpl/page.tmpl` was flattened in commit
   `2c818d8` ("Assign ENGINEURL in getsmarty") from a
   nested `{block name="content"}<main>{block name="main"}...{/block}</main>{/block}`
   shape to a single
   `{block name="content"}NEEDINFO:content{/block}` -- but
   the child templates that defined the now-orphaned
   `main` block were never updated.
   `www/org/skin/tmpl/contact-us.tmpl` was the most visible
   casualty: it extended `page.tmpl` with
   `{block name="main"}...{/block}`, so Smarty silently
   dropped the block (child block whose name does not
   match any parent block is ignored) and the parent's
   `NEEDINFO:content` placeholder rendered in the body
   slot. `www/org/skin/tmpl/credits.tmpl` had a different
   version of the same bug: it had no `{extends}` line at
   all, so it never inherited `page.tmpl`'s chrome. And
   `www/org/skin/tmpl/about-us.tmpl` didn't exist, so
   `/about-us` 404'd.

2. `engine/serve-tmpl.php::servePage()` called
   `displaypage(["content" => $smarty->fetch($basename),
   "pagetemplate" => "page.tmpl"], "page.tmpl")`. But
   `bbsengine6\displaypage()` ignores the `$data["pagetemplate"]`
   key -- it always renders the literal second argument,
   which was `"page.tmpl"`. The fetched child body was
   available as `$data.content`, but `page.tmpl`'s content
   block never references `$data.content`; it renders
   `NEEDINFO:content` directly. The fetched string was
   unreachable. Even with bug (1) fixed, this design would
   render nested chrome (because `fetch($basename)` on a
   template that extends `page.tmpl` returns the *fully
   rendered* page chrome + body, which would then be
   wrapped in another chrome by `displaypage(...)`).

The two-part fix:

- `engine/serve-tmpl.php::servePage()` now calls
  `displaypage($data, $basename)` -- passing the child
  template as the entry point so Smarty's `{extends}` /
  `{block}` machinery merges the child's content block
  with `page.tmpl`'s chrome in a single render pass.
  This mirrors the flow that
  `engine/router.php::router_displayMarkdownFile()` uses
  for `page-markdown.tmpl`.
- `www/org/skin/tmpl/contact-us.tmpl`:
  `{block name="main"}` -> `{block name="content"}`.
- `www/org/skin/tmpl/credits.tmpl`: now begins with
  `{extends file="page.tmpl"}` and wraps the existing
  body markup in `{block name="content"}...{/block}`.
- `www/org/skin/tmpl/about-us.tmpl`: new, mirrors the
  chrome-wrapped shape of `contact-us.tmpl` and ships
  with a short project overview body (was 404 before).

After the fix:

- `/contact-us` returns 200 with chrome + `Contact Us`
  blurb body.
- `/about-us` returns 200 with chrome + `About bbsengine`
  blurb body.
- `/credits` returns 200 with chrome + `Site Credits`
  blurb body.

`tests/test_page_routes_chrome.sh` is the regression
test. It probes all three URIs against the live
endpoint, asserts the chrome is present in the right
order (pageheader -> topbar -> pagefooter), asserts
the page-specific h1 is in the body, asserts the
`NEEDINFO:content` placeholder is absent, and asserts
that the build-host's `www/org/htaccess-prod` and
`www/org/skin/tmpl/*.tmpl` still hold the correct
shapes (so a partial deploy that lands the engine edit
but not the template edits, or vice versa, is caught
before the next prod push).

### fix(www/org/htaccess-prod): route /handbook/<v>/<dir> through engine/router.php

`/handbook/6/specs/` (and any other real directory under
`html/handbook/<v>/`) was being served by Apache's
`DirectoryIndex`/autoindex as a raw file listing instead of
the styled `handleFolder` listing produced by
`bbsengine6\router\router_handleFolder` /
`bbsengine6\router\router_displayDirectoryListing`.

Root cause: the handbook chapter rule in `www/org/htaccess-prod`
(lines 60-62) was guarded by `RewriteCond %{REQUEST_FILENAME}
!-d !-f`. The intent was to skip the rewrite when the URI
already resolves to a real file or directory on disk, so
Apache's default handler could serve it. But the .org vhost
ships a real `html/handbook/6/specs/` directory (and others
as the handbook grows), so `!-d` skipped the rewrite and
autoindex served the raw listing. The companion `-d` rewrite
that would have routed real directories through
`engine/router.php` was dropped in commit `032878163`
("rewrite handbook tests for per-vhost /engine/ install"),
which consolidated the per-vhost install refactor; the
teos htaccess kept the equivalent pair (lines 49-51 +
55-58) but wwworg lost both halves of its prior
`-d` / `!-d` pair.

Fix: re-add the missing `-d` rule between the `.md` rule
(line 58) and the existing `!-d !-f` rule (now line 73).
The new rule mirrors `teos/www/htaccess-prod:49-51` and
forwards real directories to `engine/router.php?uri=$2`,
where the router's `handleFolder` produces the styled
listing.

Notes:

- No `RewriteCond %{REQUEST_URI} !^/engine/` cycle guard is
  needed: the inner pattern `^handbook/(\d+)/` cannot match
  the rewritten `/engine/router.php` URL on the second
  iteration. (The teos rule needs the guard because its
  inner pattern is the broader `^(.+)$`.)
- Ordering: the new `-d` rule must precede the existing
  `!-d !-f` rule. They are mutually exclusive
  (`-d` vs `!-d`), so the order between them is purely a
  readability/stability preference; mod_rewrite's RewriteCond
  evaluation decides which fires. Placing `-d` first matches
  the original `3a606cc` ordering and the teos htaccess
  layout.
- The `.md` rule (line 58) still takes precedence over both
  the new `-d` rule and the existing chapter rule because
  `(.+\.md)$` is more specific than `(.*)$` and rules in the
  same RewriteRule block are tried top-to-bottom. A URL
  like `/handbook/6/specs/foo.md` continues to route to
  `engine/serve-md.php` regardless of whether `specs/` is a
  real directory.

Tests:

- `tests/test_handbook_6_returns_200.sh:[3]` already probed
  `/handbook/6/specs/` with a `200` expectation; this commit
  extends that probe to additionally assert the response
  body is **not** Apache's autoindex (no `Index of /`
  heading, no `<address>Apache/x.y`). The 200 alone was
  not a sufficient regression check -- autoindex returns 200
  too, so a regression to the pre-fix behavior passed the
  old test while serving an ugly listing.

Verification:

- After `make wwworg` on the build host + apache reload on
  merlin, `curl -i https://www.bbsengine.org/handbook/6/
  specs/` should return HTTP 200 with a body that contains
  the heading "specs" (rendered by
  `router_displayDirectoryListing`) and does **not** contain
  `Index of /handbook/6/specs` (Apache autoindex).
- Adjacent URLs continue to dispatch correctly: `/handbook/
  6/specs/architecture.md` -> `serve-md.php` (`.md` rule),
  `/handbook/6/specs/architecture` -> `router.php` chapter
  (`!-d !-f` rule, file does not exist on disk), `/handbook/
  6/` -> `router.php` index (`handleIndex` + TEOSDIR/
  index.md fallback).



### fix(skin/tmpl): revert page-markdown.tmpl extends target from zoid6-page.tmpl to page.tmpl; align block name with parent's {block name="content"}

On 2026-09-07 the `page-markdown.tmpl` extends target was renamed
from `page.tmpl` to `zoid6-page.tmpl` (commit `cb41487`,
`fix(skin, wwworg): ship templates /engine/router.php requires +
change page-markdown.tmpl extends target to zoid6-page.tmpl`). The
rename was framed as a collision-avoidance measure: the legacy
`bbsengine6/www/org/skin/tmpl/page.tmpl` defines
`{block name="content"}` and is the extends target for many legacy
.org templates (`archive-*`, `contact-us`, `dir`, `errormessage`,
`file`, `index`, `pageshort`, `release`, `sidebar`,
`thankyouforregistering`); the rename was supposed to keep both
template trees intact. To make the rename work,
`bbsengine6/www/org/skin/tmpl/Makefile:39` (then-new) added an
rsync that copied `zoid6/shared/skin/tmpl/page.tmpl` to
`$(WWWSTAGEDOCROOT)skin/tmpl/zoid6-page.tmpl`, so the handbook
renderer (`engine/router.php::router_displayMarkdownFile` calling
`\bbsengine6\displaypage($data, 'page-markdown.tmpl', false)`)
could resolve the extends target on the .org vhost.

That rsync was the load-bearing piece, and it isn't reliably
reaching the .org vhost. The handbook renders through
`page-markdown.tmpl` → `zoid6-page.tmpl`, but the latter is missing
on prod, so the Smarty render raises "Unable to load template
'file:zoid6-page.tmpl'" and the chapter body is served as bare
HTML with no bbsengine.org chrome.

The rename was, on inspection, **unnecessary** — and the block
name in `page-markdown.tmpl` was also wrong:

- `bbsengine6/skin/tmpl/page-markdown.tmpl` defined
  `{block name="main"}`. The legacy
  `bbsengine6/www/org/skin/tmpl/page.tmpl` only defines
  `{block name="content"}` and never defines `main`. Smarty's
  inheritance rule: a child block whose name does not match
  any parent block is **ignored**; the parent's default block
  content (`NEEDINFO:content` in this case) renders in its
  place. So even with the extends target resolved correctly,
  the handbook render would show the placeholder, not the
  rendered Markdown body. The `cb41487` rename avoided this
  only by accident — `zoid6-page.tmpl`
  (`zoid6/shared/skin/tmpl/page.tmpl`) defines
  `{block name="main"}` (line 82), so the renamed extends
  target happened to use the matching block name.
- The parallel blurb-rendered-sections template,
  `bbsengine6/skin/tmpl/page-markdown-sections.tmpl`, has been
  extending bare `page.tmpl` the whole time and renders
  successfully on the .org vhost. That template defines
  `{block name="content"}` (the legacy org block) and works
  without renaming. So the renaming pattern was inconsistent
  even at the time it was introduced — `page-markdown-sections.tmpl`
  already extended bare `page.tmpl` successfully because it
  used the matching block name.
- The org vhost's `SMARTYTEMPLATESDIR`
  (`bbsengine6/www/org/config-prod.php:41`) lists
  `DOCUMENTROOT/skin/tmpl/` as the first entry, so bare
  `page.tmpl` resolves to the legacy org layout that ships the
  bbsengine.org chrome (pageheader + topbar + pagefooter).

This commit reverts the rename and aligns the block name with
the parent's `{block name="content"}`, so the handbook chapters
inherit the .org vhost's native `page.tmpl` chrome directly,
with no separate `zoid6-page.tmpl` rsync to keep in lock-step
and with the rendered Markdown body actually replacing the
parent's default block content.

Changes:

- `bbsengine6/skin/tmpl/page-markdown.tmpl:1` —
  `{extends file="zoid6-page.tmpl"}` →
  `{extends file="page.tmpl"}`.
- `bbsengine6/skin/tmpl/page-markdown.tmpl:5` — rename the
  body block from `{block name="main"}` to
  `{block name="content"}` so it replaces the parent
  `page.tmpl`'s `{block name="content"}` body. Without this
  rename, the rendered chapter body would not appear (the
  parent's `NEEDINFO:content` placeholder would render
  instead).
- `bbsengine6/www/org/skin/tmpl/Makefile:39` — drop the
  `$(RSYNC) $(CURDIR)/../../../../../zoid6/shared/skin/tmpl/page.tmpl $(WWWSTAGEDOCROOT)skin/tmpl/zoid6-page.tmpl`
  line. The comment block at lines 8-26 explaining why
  `zoid6-page.tmpl` exists is no longer relevant and is
  trimmed (with the `{block name="main"}` reference at line 10
  corrected to `{block name="content"}` to match the new
  block name); the `page-markdown.tmpl` + `youarehere.tmpl` +
  `teos-breadcrumbs.tmpl` rsyncs (the templates the handbook
  actually needs that don't ship via the .org vhost's primary
  `*.tmpl` rsync) remain.
- `zoid6/shared/skin/tmpl/page.tmpl` and the .org vhost's
  `skin/tmpl/page.tmpl` are unchanged.
