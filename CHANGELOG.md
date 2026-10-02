## [Unreleased]

### fix(engine/router): handbook version root no longer 404s

`https://bbsengine.org/handbook/6/` (and any
`/handbook/<v>/` URL with no trailing path) returned a styled 404
("Page not found: handbook/6/") with a literal `ROUTER_RENDERED`
appended after `</html>`. Two interacting bugs:

1. **engine/router.php HTTP entry-point** gated the handbook
   prefix-strip on `!isset($_GET['uri'])`. htaccess's catch-all
   rewrite (`bbsengine6/www/org/htaccess-prod:103`) pre-filled
   `$_GET['uri']` to the full `/handbook/<v>/` URI, so the
   dispatcher saw the prefixed URI, every handler pattern rejected
   it, and the version root fell through to the styled 404.

2. **engine/router.php dispatch loop** returned `router_handleError()`
   directly when no handler matched. `router_handleError()`
   returns `ROUTER_RENDERED` (a string), so the HTTP entry-point's
   `else echo $router_result` echoed the literal `"ROUTER_RENDERED"`
   after the styled chrome. Cosmetic but visible to anyone
   inspecting response bodies.

Fix:

- `engine/router.php`: drop the `!isset($_GET['uri'])` gate on
  the prefix-strip. REQUEST_URI is the canonical source for
  "what the client asked for" on the handbook vhost.
- `engine/router.php`: capture `router_handleError()` into
  `$err_result` and map `=== ROUTER_RENDERED` to `''` so the
  HTTP entry-point's `echo` is a no-op. Mirror of the existing
  in-loop mapping at line ~796.
- `www/org/htaccess-prod`: belt-and-suspenders explicit rule
  `^handbook/(\d+)/?$ /engine/router.php?uri=` so the
  version root reaches the router with `?uri=` empty even on
  htaccess variants that don't pre-fill `$_GET['uri']`.

Tests:

- `php/test_router.php` Test 3f pins the prefix-strip is
  unconditional (no `!isset($_GET['uri'])` gate in code).
- `php/test_router.php` Test 3g pins the post-loop fallback
  normalizes `ROUTER_RENDERED` to `''`.

### docs(changelog): regression-recovery commit pin

Pins the three commits that comprise the live 2026-10-XX fix for
the `/rec/arts/tv/wiz-kids`-class `SMARTYTEMPLATESDIR is not
configured` failure mode on the teos vhost, so a future operator
who hits the same symptom can `git checkout` straight to a known-good
state without piecing together history.

**Pin these commits if rolling back:**

| Repo             | SHA       | Subject                                                                              |
|------------------|-----------|--------------------------------------------------------------------------------------|
| inner bbsengine6 | `9678aad` | refactor(engine): restore VHOSTCONFIG resolver as FPM-env-propagation safety net      |
| inner deploytool | `fce3ed0` | test(deploytool): invert vhostconfig.php contract pin; assert existence with resolver  |
| meta-repo        | `229eb53b` | chore(meta): mirror inner bbsengine6 VHOSTCONFIG resolver restore                   |

All three must land together; deploytool's pytest will fail against
the new bbsengine6 source (or vice versa) if any one is missing.

**Regression symptoms that map back to this pin:**

  - URL `/rec/arts/tv/wiz-kids` (or any engine-rendered teos URL)
    returns `Error: router.http.100:bbsengine6\getsmarty():
    SMARTYTEMPLATESDIR is not configured. ... Router Error`
    with HTTP 500 instead of the chrome-rendered page.

  - URL `/<slug>.md` (e.g., `/rec/arts/tv/wiz-kids.md`,
    `/ec/investigated-psychics-fraud-pigasus.md`) returns the same
    SMARTYTEMPLATESDIR error wrapped in HTML chrome instead of
    `Content-Type: text/plain` raw markdown bytes.

  - `ssh merlin journalctl -u php-fpm --since "5 min ago" | grep NEEDINFO`
    shows the legacy `NEEDINFO.VHOSTCONFIG.router_resolve_vhost_config`
    sentinel as the env value (instead of `envconfig='<real-path>'`),
    indicating the VHOSTCONFIG resolver didn't find the vhost config.

**Root cause for both symptoms:** the inner commit `02eebac`
(2026-09-29 20:37) removed `engine/vhostconfig.php`, which was
the load-bearing fallback for vhost config resolution on merlin's
`mod_proxy_fcgi + FPM clear_env=yes` plumbing (Apache's `SetEnv`
directives don't propagate to the FPM worker, so
`VHOSTDOCROOT + include_path` was insufficient and
`bbsengine6config.php:51`'s `stream_resolve_include_path("config.php")`
missed the vhost's `config.php`).

**The fix** restores `engine/vhostconfig.php` with two resolution
paths that don't depend on FPM env propagation: (1) `VHOSTCONFIG`
env var (absolute path; set by every htaccess-prod in the repo
but unused by current code), (2) `SCRIPT_FILENAME` fallback that
walks up from `<docroot>/engine/<script>.php` to `<docroot>/` and
probes known vhost subdirs. Both work without FPM env propagation.

**Rollback procedure (if a future change reintroduces the bug):**

  1. `cd bbsengine6 && git checkout 9678aad -- engine/vhostconfig.php engine/router.php`
     (in the inner repo; replaces any accidental deletion).
  2. `cd bbsengine6 && git commit -m "fix(engine): restore VHOSTCONFIG resolver"`
  3. `cd deploytool && git checkout fce3ed0 -- tests/test_deploy_bbsengine6_engine.py`
  4. `cd deploytool && git commit -m "fix(deploytool): invert vhostconfig.php contract pin"`
  5. In the meta-repo: re-run `scripts/bump-submodule-pointers.sh` (or
     manually `git add -A bbsengine6/ && git commit -m "chore(meta):
     mirror inner bbsengine6 VHOSTCONFIG resolver restore"`), then
     `git push github main`.
  6. `deploy --with-deps teos.prod` on minotaur.

**Verification after rollback:**

  - `curl -sI https://zoidtechnologies.com/teos/ec/investigated-psychics-fraud-pigasus.md`
    expect: `HTTP/1.1 200 OK`, `Content-Type: text/plain; charset=utf-8`
  - `curl -sI https://zoidtechnologies.com/teos/ec/investigated-psychics-fraud-pigasus`
    expect: `HTTP/1.1 200 OK`, `Content-Type: text/html; charset=utf-8`
  - `ssh merlin journalctl -u php-fpm --since "5 min ago" | grep NEEDINFO.VHOSTCONFIG`
    expect: log lines showing `envconfig='<real-path>'` (e.g.,
    `/srv/www/vhosts/zoidtechnologies.com/html/teos/config.php`), NOT
    the `NEEDINFO.VHOSTCONFIG...` sentinel.

### refactor(engine): restore VHOSTCONFIG resolver as FPM-env-propagation safety net

The Sep 29 commit `02eebac` removed `engine/vhostconfig.php` on the
rationale that `VHOSTDOCROOT + include_path` was sufficient for resolving
the vhost's `config.php`. In production on merlin (mod_proxy_fcgi + FPM
with `clear_env = yes`, the PHP 7+ default), Apache's `SetEnv`
directives do not propagate to the FPM worker:

  - `bootstrap.php:50-57` reads `getenv('VHOSTDOCROOT')` — empty in FPM.
    The vhost root is not prepended to `include_path`.
  - `bbsengine6config.php:51` calls `stream_resolve_include_path("config.php")`
    — without the vhost root on the path, returns false. The vhost's
    `config.php` is never loaded.
  - `\config\SMARTYTEMPLATESDIR` (and friends) is never defined.
  - On any request that falls through `router_handleError` (e.g. a `.md`
    URL whose `rawmarkdown` handler missed because TEOSDIR was also
    stripped), `getsmarty()` throws its
    `RuntimeException "SMARTYTEMPLATESDIR is not configured"`, which
    `engine/router.php:846`'s outer catch re-emits as
    `router.http.100:<message>`.

The fix restores `engine/vhostconfig.php` as a robust fallback that
**does not depend on FPM env propagation**:

  1. `VHOSTCONFIG` env var (preferred) — set by every htaccess-prod in
     the repo as `SetEnv VHOSTCONFIG <abs-path>` (already present in
     teos/www/htaccess-prod:30 and bbsengine6/www/org/htaccess-prod:30
     but unused by current code). Honors Apache `mod_env` +
     `AllowOverride FileInfo` prerequisites.
  2. `SCRIPT_FILENAME` fallback — walks up from
     `<docroot>/engine/<script>.php` to `<docroot>/` and probes known
     vhost subdirs (`config.php`, `teos/config.php`, `org/config.php`,
     `com/config.php`, `bbsengine.org/config.php`). Works without any
     env vars; uses `is_file()` which is filesystem-only.
  3. Both fail — return false. `bbsengine6config.php:51`'s
     `stream_resolve_include_path` chain still runs as a tertiary
     fallback (CLI tests, partial deploys). If that also misses,
     `getsmarty()` throws the existing "not configured" exception
     (the pre-2026-09-24 failure mode, which is the correct behavior
     for genuinely misconfigured vhosts).

The resolver lives at `engine/vhostconfig.php` and is required from
`engine/router.php` immediately after `util.php` (before the engine,
blurb, page, folder, and serve-tmpl requires). It uses
`\bbsengine6\util\env('VHOSTCONFIG', 'NEEDINFO...')` so the read
follows the canonical `getenv() -> defined() -> default` precedence
(AGENTS.md "TEOSDIR resolution contract") and the
`NEEDINFO.VHOSTCONFIG.router_resolve_vhost_config` logentry sentinel
matches the pre-removal shape — any log probes that grep for
`NEEDINFO.VHOSTCONFIG` keep working.

**Files touched:**

  - `engine/vhostconfig.php` (restored)
  - `engine/router.php` (docblock + `require_once("vhostconfig.php")`
    + resolver call after util.php load)
  - `engine/Makefile` (canonical entry-points comment updated)
  - `Makefile:283` (deploy-handbook banner now lists `vhostconfig`)
  - `deploytool/tests/test_deploy_bbsengine6_engine.py`
    (`test_engine_vhostconfig_php_does_not_exist` inverted to
    `test_engine_vhostconfig_php_exists_with_resolver`; the
    regression-guard intent — prevent accidental removal of the
    safety net — is preserved under a new name)
  - `CHANGELOG.md` (this entry)

**Deploy impact:**

  - The `ENGINE_PHP = $(wildcard *.php)` wildcard in `engine/Makefile:33`
    auto-picks up `vhostconfig.php` and stages it alongside the other
    entry-points. No Makefile recipe changes.
  - The next `deploy --with-deps teos.prod` will rsync the new file to
    `/srv/www/vhosts/zoidtechnologies.com/html/engine/vhostconfig.php`
    (and the equivalent handbook path). FPM will pick it up on the
    next request; no reload strictly required, but `sudo systemctl
    reload php-fpm` is the standard post-deploy hygiene.

**Regression intent:** the new deploytool test
`test_engine_vhostconfig_php_exists_with_resolver` replaces the
`02eebac`-era `test_engine_vhostconfig_php_does_not_exist` test. Both
tests pin a single thing — but the new test pins the safety net
exists, while the old test pinned its absence. The 2026-09-29
removal turned out to be premature on merlin's specific FPM plumbing;
the restored file is the canonical fix.

### refactor(php/markdown): merge php/serve-md.php into php/markdown.php under \bbsengine6\markdown

`.md` handling now lives in one file under one namespace. The library at
`php/serve-md.php` (which had been library-only since the 2026-09-29
`98c3edc` refactor) and the handbook-vhost entry-point at
`engine/serve-md.php` are folded into `php/markdown.php` as
`\bbsengine6\markdown\serveRawMarkdown()` (generic raw-stream library
for `router_handleRawMarkdown`) and
`\bbsengine6\markdown\serveRawMarkdownForHandbook()` (HTTP entry-point
for the handbook vhost).

`php/serve-md.php` is **deleted**. `engine/serve-md.php` is now a 4-line
wrapper that `require_once`s `php/markdown.php` and calls
`serveRawMarkdownForHandbook()`. The handbook vhost's htaccess-prod
rewrite target (`www/org/htaccess-prod:78`,
`/handbook/<v>/<uri>.md -> /engine/serve-md.php?path=$2`) is unchanged,
as are the 404 body IDs (`engine.serve-md.validate-handbook-prefix.220`,
`engine.serve-md.resolve-handbook-md.240`) and the `serve-md.100/200/210`
logentry codes.

Side-effect-free on `require_once`: the merged `php/markdown.php`'s
`namespace {}` block has a `SCRIPT_NAME === '/engine/serve-md.php'` +
`PHP_SAPI !== 'cli'` guard that fires the entry-point only when the
file is invoked directly as the vhost entry-point shim. When required
from `engine/router.php`, `php/test_router_handleraemarkdown.php`, or
any other context, the entry-point stays dormant (the 2026-09-29
invariant pinned by `php/test_router.php` Test 6i).

**Two reasons for the merge:**

  1. Two libraries for one theme (`.md` files) is the kind of drift the
     2026-09-29 refactor was cleaning up. Both halves serve `.md` files;
     one renders them to HTML, the other streams them as raw bytes.
  2. The two libraries sat in different namespaces (`\bbsengine6` for
     the stream half, `\bbsengine6\markdown` for the render half).
     Folding the stream half into `\bbsengine6\markdown` makes one
     canonical home for all `.md` primitives.

**Lazy Parsedown load.** `Parsedown.php` / `ParsedownExtra.php` were
eagerly required at the top of `namespace bbsengine6\markdown {}`; the
merge moves them into `renderHtml()`'s first-call path so a direct
invocation of the entry-point (where `include_path` may not yet be
primed for vendor/) does not fatal on Parsedown. The stream-half
entry-point does not use Parsedown, so the eager require was load-bearing
only for the render half.

**Caller updates:**

  - `engine/router.php:99` `require_once("serve-md.php")` deleted (router
    already requires `markdown.php` at line 79, which now carries the
    library).
  - `engine/router.php:489` call site renamed to
    `\bbsengine6\markdown\serveRawMarkdown()`.
  - `php/test_router_handleraemarkdown.php:29` now requires
    `markdown.php`; all seven call sites and the doc header use the
    new FQCN.
  - `php/test_router.php` Test 6h / 6i FAIL messages and comments
    use the new FQCN.
  - `tests/test_teos_md_url_text_plain.sh:20` comment uses the new FQCN.

### fix(engine/router): raw text/plain dispatcher for `.md` URLs across all vhosts

Closes the 2026-09-29 incident on `zoidtechnologies.com/teos/ec/<slug>.md`
which 404'd with a plain `text/plain "File not found"` body. Root cause:
the teos htaccess (line 54) rewrote every `.md` URL to `engine/serve-md.php`,
which since commit eecce7c (2026-09-16, "switch rewrite contract to ?path=
query string") only handles `/handbook/<v>/...` URLs. Meanwhile, the engine
router's HTTP entry-point stripped a trailing `.md` from the URI before
the dispatch loop, so even if the rewrite had targeted `engine/router.php`
the raw text/plain dispatch contract was unreachable: `.md` URIs were
coerced to bare URIs and routed through the chrome-rendered handlers.

**Five changes** (committed as a single fix; see commit message for the
split into router.php + tests + CHANGELOG/handbook/docs):

  1. `engine/router.php` HTTP entry-point no longer strips `.md` from
     the URI. The dispatch loop passes the full URI (with extension)
     to every handler; handlers that don't care about extensions
     pattern-gate or strip them themselves.

  2. New handler `router_handleRawMarkdown` (registered at the end of
     `router_gethandlers()` with pattern `/\.md$/`) dispatches `.md$-suffixed`
     URIs to `Content-Type: text/plain; charset=utf-8`. It reads
     `TEOSDIR` via `\bbsengine6\util\env("TEOSDIR")` (the canonical
     polymorphic read used by every other TEOSDIR consumer in
     `bbsengine6/`) and reuses the canonical library
     `\bbsengine6\serveRawMarkdown()` (defined in `php/serve-md.php`),
     which enforces realpath-based containment, `.md`-only extension,
     and file-only checks. On a hit the handler returns `ROUTER_RENDERED`;
     on a miss it returns `ROUTER_NEXT` so the chain falls through to
     the styled engine 404 via `router_handleError` / `page\error` /
     `errormessage.tmpl`.

  3. The `markdown` handler's pattern in `router_gethandlers()` is
     tightened by removing `.` from the URI character class. The
     `$` end-anchor naturally restricts matches to URIs that don't
     contain a dot, so `.md$` URIs no longer reach the chrome-rendered
     branch. No negative lookahead required. `router_handleMarkdown`'s
     body adds a defensive `preg_replace('/\.md$/', '', $reluri)`
     before its filesystem probe as belt-and-suspenders against
     future registry regressions.

  4. The handbook vhost still routes `.md` URLs to its dedicated
     `engine/serve-md.php` entry-point (which uses the stricter
     `handbook_resolve()` containment via `BBSENGINE6_HANDBOOK_HOME`).
     The teos vhost's htaccess is updated to route `.md` URLs to
     `engine/router.php` so the new router-side handler can fire.

  5. `bbsengine6\util\env()` is the canonical TEOSDIR read across
     `bbsengine6/`; the new handler does NOT hardcode any vhost path
     and does NOT introduce a teos-specific branch. The engine stays
     site-agnostic per the AGENTS.md "TEOSDIR resolution contract".

**Test coverage.**

  - `php/test_router.php` Tests 6f, 6g, 6h: pin the tightened
    `markdown` pattern (rejects `ec/foo.md`, accepts `ec/foo`),
    the `rawmarkdown` registry entry (pattern matches `\.md$`,
    handler FQCN is callable), and the handler body shape
    (calls `env("TEOSDIR")`, calls `serveRawMarkdown()`, returns
    `ROUTER_RENDERED`).
  - `php/test_router_handleraemarkdown.php` (new): pins the canonical
    library in isolation — hit/miss, traversal containment, .md-only
    extension, file-only (rejects directories), nonexistent basedir,
    nested subdirectory depth.
  - `php/test_router.php` Test 3 (handler order) and Test 6b
    (entry-point strip) are updated to reflect the new contract.

**Out of scope.** `engine/serve-md.php` (handbook-only entry-point),
`php/serve-md.php` (the canonical library reused by the new handler),
and `www/org/htaccess-prod` (handbook htaccess) are all unchanged.

### fix(smarty/function.teos): config-less load via BBSENGINEROOT + bootstrap

Closes the 2026-09-29 journal entry
`PHP Warning: require_once(config.php): Failed to open stream
in /srv/www/bbsengine6/smarty/function.teos.php on line 43`,
which surfaced under mod_env + mod_rewrite + mod_proxy_fcgi
combos where VHOSTDOCROOT / VHOSTCONFIG did not propagate to
FPM. The previous workaround (a9957a5) was a defensive
include_path re-establishment that kept the underlying
vhost-config dependency in place; this set of changes drops
that dependency entirely so `{teos}` works on any vhost that
publishes `BBSENGINEROOT`.

**Three changes** (committed as 49b5b70 + a fixup):

  1. `BBSENGINEROOT` (env, set in vhost htaccess) names the
     bbsengine6 install directory. The handbook vhost
     (`bbsengine6/www/org/htaccess-prod`) and the teos vhost
     (`teos/www/htaccess-prod`) both publish it.

  2. `smarty/function.teos.php` resolves util.php via the
     established include_path convention: first load
     `BBSENGINEROOT/php/bootstrap.php`, then bare-name
     `require_once('util.php')`. bootstrap.php already adds
     `/srv/www/bbsengine6/php/` (and `/usr/share/pear/` for
     `Log.php`) to include_path. This mirrors the load order
     in `engine/router.php`.

  3. `{teos}` re-uses the parent Smarty instance
     (`$template->smarty`) instead of constructing a fresh
     one via `\bbsengine6\getsmarty()`. The parent was already
     created by the upstream caller (engine/router.php or a
     legacy teos entry point) with all per-vhost `SMARTY*`
     dirs wired up, so re-using it means this plugin needs no
     engine-state at all.

`TEOSURL` is exposed as a PHP constant lazily inside the
render path so the template's `{$smarty.const.TEOSURL}`
syntax reads it. The default is the NEEDINFO marker
`NEEDINFO:function.teos.100:TEOSURL` rather than an empty
string so missing config surfaces visibly in the rendered
HTML and is greppable in production logs. A `defined()` guard
respects any value the vhost already defined (legacy teos
`config-prod.php` uses `define("TEOSURL", \config\TEOSURL)`).

**Test coverage.** New `php/test_teos_plugin_configless.php`
(11 assertions) renders `{teos}` without config.php /
database.php / engine.php on include_path and pins:
  - smarty_function_teos is defined after require_once
  - `\bbsengine6\util\env` is loaded lazily after first render
  - rendered href / data-contenturl use TEOSURL from env
  - missing TEOSURL surfaces the NEEDINFO marker
  - missing BBSENGINEROOT raises a caught RuntimeException
    (not an uncaught fatal at file-scope)
  - static guards: no bare `require_once("config.php")`,
    no bare `require_once("engine.php")`, plugin loads
    `bootstrap.php` + bare-name `util.php` (Option C pattern).

**Why bootstrap.php.** The plugin's fixup commit refined
49b5b70 to load util.php through `BBSENGINEROOT/php/bootstrap.php`
rather than via a direct path concat. This matches the
include_path convention `php/bootstrap.php:14-21` already
uses for itself (adding `/srv/www/bbsengine6/php/` and
`/usr/share/pear/` to include_path) and is the same
load pattern `engine/router.php` uses. The
`BBSENGINEROOT` env var still names the engine root (not
the php dir) — consistent with how `VHOSTDOCROOT` names the
vhost docroot — and the plugin concats `/php/bootstrap.php`
the same way bootstrap.php itself concats `/Log.php`
implicitly.

**Out of scope.** The same defensive-block pattern in
`smarty/function.repo.php`, `smarty/function.apidocs.php`,
and `smarty/modifier.datestamp.php` is intentionally left
untouched: those plugins need `database.php`, `session.php`,
or `DATEFORMAT` (the latter is a vhost `define()`, not an
env var). Their config-less refactor is a separate ticket
if/when their deps get env-var-ified.

### feat(engine): per-vhost /engine/ install via ENGINE_DOCROOT env var

`bbsengine6/engine/Makefile` and `bbsengine6/Makefile` (parent) now
honor a `ENGINE_DOCROOT` env var so operators can stage and prod-push
the engine entry-point PHP install onto a non-default vhost without
patching the Makefile:

```sh
ENGINE_DOCROOT=/srv/www/vhosts/<vhost>/html/engine/ \
  deploy bbsengine6.engine-stage
ENGINE_DOCROOT=/srv/www/vhosts/<vhost>/html/engine/ \
  deploy bbsengine6.engine-prod
```

When `ENGINE_DOCROOT` is unset, the existing zoidtechnologies.com
default is preserved -- no behavior change for current callers.

**Defense in depth.** `ENGINE_DOCROOT` is read by `?=` defaults at
two layers:

  - `bbsengine6/Makefile:34-40` (parent, `export`ed to sub-makes
    so any recipe that consumes `$(ENGINESTAGEDOCROOT)` at this
    layer -- `wwworg:`, `prod:`, the bare `deploy:` umbrella --
    inherits the env-var override automatically).
  - `bbsengine6/engine/Makefile:2-9` (sub-make; the engine
    `stage:` and `deploy:` rules).

Each layer chains `ENGINESTAGEDOCROOT ?= $(ENGINE_DOCROOT)` so a
single env var flips both the local rsync destination
(`$(ENGINESTAGEDOCROOT)`) and the merlin push destination
(`$(ENGINEPRODDOCROOT)` = `$(ENGINEHOST):$(ENGINESTAGEDOCROOT)`).

**Inline overrides still win.** Make's command-line > environment >
file precedence is preserved, so the existing
`bbsengine6/Makefile:135-136` `wwworg` recipe (which sets
`ENGINESTAGEDOCROOT=/srv/www/vhosts/www.bbsengine.org/html/engine/`
inline) keeps pointing the engine sub-make at the bbsengine.org
vhost -- the env var only takes effect when no inline override is
present.

**Plumbing on the deploytool side** lives in
`src/deploytool/lib.py:run_make_deploy` (set/strip block, mirroring
the existing `DEPLOY_EDITABLE` / `DEPLOY_WITH_DEPS` / `DEPLOY_UPGRADE`
contract). No CLI flag; env var only.

### feat(router): use folder.tmpl for directory listings; escape yaml titles

`router_displayDirectoryListing` in `engine/router.php` switched
from `browse.tmpl` (which lived only in the zoid6/teos docroot)
to `folder.tmpl` (which now ships in `bbsengine6/skin/tmpl/`).
The 36-line `try`/`catch` + inline-HTML fallback that existed to
gracefully degrade when `browse.tmpl` was missing has been
deleted, since `folder.tmpl` is in the engine tree. The
`$sigs`/`$currentsig` projection that fed the currentsig-shaped
`browse.tmpl` is removed; `folder.tmpl` reads `$data.items`
directly. If `\bbsengine6\displaypage()` is unavailable the
function now returns a 500 via `router_handleError` rather than
emitting bare HTML.

In `router_collectDirectoryItems`, YAML-derived titles are now
`htmlspecialchars`-escaped (with an empty/whitespace-title
fallback to the filename). `folder.tmpl` prints
`{$item.title}` raw, so an unescaped YAML `title:` was a stored
XSS vector. Mirror of the existing escape in
`php/folder.php:228` and the live blurb path at
`php/markdown.php::splitFrontmatter` callers.

### fix(markdown): splitFrontmatter accepts ---<EOF>; strip CRLF from values

Loosen `\bbsengine6\markdown\splitFrontmatter`'s
closing-delimiter regex from `\n---\s*\n` to
`\n---(?:\s*\n|\s*$)`. Files whose frontmatter block ends at
EOF without a trailing newline (`---\ntitle: foo\n---`) are no
longer treated as body-only. Backwards-compatible: every input
the previous regex accepted is still accepted.

Also extend the per-line value `trim()` from `"\"' "` to
`"\"' \r"` so CRLF input
(`---\r\ntitle: foo\r\n---\r\nbody`) does not leak a trailing
carriage return into rendered titles.

### test(frontmatter+router): pin edge cases for splitFrontmatter and yaml title escape

New `php/test_frontmatter.php` (20 cases) covers the
splitFrontmatter regex and value handling: embedded ` ---` and
trailing ` ----` in titles, quoted titles containing `---`,
CRLF input, multi-line-title limitation, multi-block input,
empty / comment-only / no-frontmatter edges, and the explicit
rejection cases (non-whitespace garbage after closing `---`,
leading whitespace before opening `---`, missing whitespace
between `---` and the first key).

`php/test_router.php` gains 5 cases pinning
`router_collectDirectoryItems`' XSS-escape contract: HTML
tags, ampersands, and quote chars are escaped; empty and
whitespace-only titles fall back to the filename.

### refactor(bbsengine6): template/plugin registries with priority enum

Introduces the `\bbsengine6\template` and
`\bbsengine6\template\plugin` namespaces (replacing the
single-purpose `\bbsengine6\templatedirs` namespace) and a
priority-enum registry for cross-app template/plugin-dir
contributions. `\zoid6\template` mirrors the same shape so
zoid6 fits cleanly into the registry when loaded.

**New namespaces.** Each exposes the same shape:

```
\bbsengine6\template            \bbsengine6\template\plugin
├── PRIORITY_APP                 ├── PRIORITY_APP
├── PRIORITY_APP_INTEGRATION     ├── PRIORITY_APP_INTEGRATION
├── PRIORITY_ENGINE              ├── PRIORITY_ENGINE
├── _registry() (private)        ├── _registry() (private)
├── register(priority, hook)     ├── register(priority, hook)
├── extra()                      ├── extra()
└── normalize(raw, registry,     └── normalize(raw)  [wrapper]
    engineFallback, nsLabel)
```

The 4-arg `normalize` is the canonical body. The plugin
namespace's `normalize` and zoid6's `\zoid6\template\normalize`
are thin wrappers that delegate to the canonical with their
own registry and engine-fallback path.

**Resolved search order.**

1. `PRIORITY_APP` — vhost's `SMARTYTEMPLATESDIR` (or
   `SMARTYPLUGINSDIR`) array.
2. `PRIORITY_APP_INTEGRATION` — `\zoid6\template\extra`
   (auto-registered when zoid6 is loaded) plus any legacy
   `\bbsengine6\template\hook_extra_dirs()` v0 hook the
   vhost defined directly.
3. `PRIORITY_ENGINE` — `\bbsengine6\template\extra()` returns
   `<bbsengine6>/skin/tmpl/` for templates;
   `\bbsengine6\template\plugin\extra()` returns
   `<bbsengine6>/smarty/` for plugins. Self-registered.

**bbsengine6 has no hard dependency on zoid6.** The
`function_exists('\zoid6\template\extra')` check at
`bbsengine6config.php` load time is a no-op when zoid6 is
absent. Same opt-in pattern as the existing
`\bbsengine6\menu\buildchoices` shim.

**getsmarty() helper extraction.** The plugin-dir
auto-append (formerly inlined in `getsmarty()` at lines
392–402) moves into `\bbsengine6\template\plugin\normalize`
via the `extra()` canonical. The templatedir normalize call
moves into `_smarty_resolved_templatedir()` and
`_smarty_resolved_pluginsdir()` helpers that memoize the
resolved path keyed on the serialized input array. Caller
overrides still bypass the registry walk (existing semantic
preserved).

**Tests.** `php/test_smarty_templatedirs.php` renamed to
`php/test_smarty_template.php` (37 cases). Coverage:

- T1–T14: backward-compat (rename + namespace migration).
- T15–T16: cleanup audit (no `_getsmarty` references;
  `getsmarty()` returns a `Smarty` instance).
- T17–T22: priority-enum registry mechanics.
- T23–T28: engine fallback + wrapper symmetry.
- T29–T31: cache behavior + caller-override bypass.
- T32–T34: API surface symmetry across the three namespaces.
- T35–T37: error-message namespace labels.

`php/test_smarty_pluginsdir.php` updated to verify the new
registry-based plugin-dir resolution (5 cases). All 8
pluginsdir tests + 37 template tests pass.

**Files modified.**

| File | Change |
|---|---|
| `php/bbsengine6config.php` | Replace `\bbsengine6\templatedirs` with `\bbsengine6\template` + `\bbsengine6\template\plugin` namespaces; canonical 4-arg `normalize()`; auto-wiring for v0 hook + zoid6 hook |
| `php/engine.php` | Extract `_smarty_resolved_templatedir` and `_smarty_resolved_pluginsdir` cache helpers; inline plugin-dir enrichment removed |
| `php/test_smarty_templatedirs.php` → `php/test_smarty_template.php` | Renamed; namespace references updated; T17–T37 added |
| `php/test_smarty_pluginsdir.php` | Header updated; T4–T5 assertions updated to verify the new registry path |
| `php/test_router_vhostconfig.php` | Comment reference updated |
| `www/org/config-prod.php` | Comment updated to reference new namespace |
| `CHANGELOG.md` | This entry |

The companion change in the zoid6 submodule (adding the
`\zoid6\template` namespace and `\zoid6\plugin_extra()`)
lives in `zoid6/CHANGELOG.md` and is a separate commit.

### refactor(bbsengine6): SMARTYTEMPLATESDIR normalization, templatedirs hook, _getsmarty cleanup

A consolidated change set that centralizes Smarty template-dir
handling in `bbsengine6config.php`, removes dead code, fixes
two pre-existing bugs, and aligns the handbook vhost with the
convention used by every other zoid6 consumer.

**`getsmarty()` simplification (`php/engine.php`).**
Replaces the 50-line option-defaulting + array-key-exists
cascade with a small block of `??=` defaults plus a 12-line
input validator. `getsmarty()` now reads the vhost-supplied
`\config\SMARTYTEMPLATESDIR` and calls
`\bbsengine6\templatedirs\normalize()` to materialize the
final flat numeric-keyed list (engine fallback appended last).
The plugin-dir auto-append of `/srv/www/bbsengine6/smarty/`
moves into `getsmarty()` itself (was hardcoded inline). All
this is consistent with the existing `bbsengine6\menu\buildchoices`
pattern.

**Deferred validation.** If a vhost's `config.php` doesn't define
`config\SMARTYTEMPLATESDIR`, the first call to `getsmarty()`
throws `\RuntimeException` with a clear message ("SMARTYTEMPLATESDIR
is not configured. Define config\\SMARTYTEMPLATESDIR in your
vhost config.php..."). Previously this manifested as Smarty's
"Unable to load template `page.tmpl`" 500 error at render time.
`bbsengine6config.php` load itself is **non-fatal** (CLI scripts
that only need a constant still work).

**`templatedirs\normalize()` (`php/bbsengine6config.php`).**
New public function in the `bbsengine6\templatedirs` namespace.
Accepts the raw `\config\SMARTYTEMPLATESDIR` value (array or
scalar string), flattens accidental array-of-array wrapping
(legacy `array(SMARTYTEMPLATESDIR)` bug), validates each entry
is a string (throws on int/null/array entries), enforces
trailing `/` on each entry, dedups (case-sensitive — assumes
Linux ext4), appends the templatedirs hook's extra dirs (if
`hook_extra_dirs()` is defined), then appends the engine
fallback `bbsengine6/skin/tmpl/` as the last entry.

**`templatedirs\extra_dirs()` extension point.** Mirrors the
existing `bbsengine6\menu\buildchoices()` pattern. Default
returns `[]`. Consumer apps (e.g. teos) define
`\bbsengine6\templatedirs\hook_extra_dirs()` in their config.php
to contribute extra dirs (e.g. teos' `<TEOSDIR>/skin/tmpl/` for
the handbook vhost). A zoid6 hook shim is installed when zoid6
is loaded, parallel to the menu hook shim. The handbook vhost
currently doesn't load teos, so the hook gracefully no-ops
(the `is_dir()` check returns false for `<TEOSDIR>/skin/tmpl/`
when TEOSDIR points at the handbook's markdown root).

**`config\SHAREDTMPLDIR` constant.** New namespaced constant
defaulting to `/srv/www/vhosts/zoidtechnologies.com/html/shared/skin/tmpl/`.
Single source of truth for the cross-app shared tmpl path.
vhosts that want a different shared-dir layout override before
requiring `bbsengine6config.php`. Five vhost configs (bbsengine6
www/org, bbsengine6 www/com, teos, achilles, asimov, murdermotel,
zoid6 sites) now reference `\config\SHAREDTMPLDIR` instead of
hardcoding the path. Duplicate `/srv/www/zoid6/shared/skin/tmpl/`
entries in the zoid6 www config are deduped by `normalize()`.

**`_getsmarty()` and `bbsenginedotorg.php::getsmarty()` deleted.**
Both were near-duplicates of `\bbsengine6\getsmarty()` with a
buggy `array(SMARTYTEMPLATESDIR)` wrap (array-of-array) that
silently dropped template resolution on teos and other vhosts.
The bbsengine4.php fallback `getsmarty()` is also gone (was
reachable only when no other wrapper existed, but always did).
All 19 callers in `post.php` / `login.php` / `register.php` /
`archive.php` / `bbsengine4.php` updated to
`\bbsengine6\getsmarty()` directly.

**`\zoid6\getsmarty()` wrapper deleted (`zoid6/php/zoid6.php`).**
It had zero callers in the codebase and referenced `_getsmarty`,
a function not defined in zoid6 (broken in isolation). The dead
commented-out `getsmarty()` block in
`zoid6/sites/www/php/lib.php` is also removed.

**Handbook vhost (`bbsengine6/www/org/config-prod.php`).**
Two pre-existing bugs fixed as side-effects of the refactor:

1. The handbook's `htaccess-prod:6` sets `TEOSDIR` (no
   underscore) but `config-prod.php:12` (pre-refactor) read
   `TEOS_DIR` (with underscore). The env var name is now
   read correctly (`TEOSDIR` first, `TEOS_DIR` as legacy
   fallback).
2. `config\SMARTYTEMPLATESDIR` index 1 is now
   `\config\SHAREDTMPLDIR` instead of `$bbsengine_root."/skin/tmpl/"`.
   The trailing `bbsengine6/skin/tmpl/` entry is removed
   (auto-appended by `bbsengine6config.php`). The teos-dir
   entry is removed from this vhost (now supplied by the
   teos hook when teos is loaded). **Semantic change:**
   index 1 shifts from `bbsengine6/skin/tmpl/` to the
   shared dir. This aligns the handbook with the convention
   used by every other zoid6 consumer (bbsengine6 www/com,
   teos, achilles, asimov, murdermotel, zoid6 www/engine).
   `test_smarty_paths.sh` confirms common templates
   (`pageheader.tmpl`, `blurb.tmpl`, `breadcrumbs.tmpl`)
   still resolve in both the teos and handbook vhosts.

**New test (`php/test_smarty_templatedirs.php`).**
16 cases covering: namespaced-array normalization, scalar-string
coercion, array-of-array flattening, dedup, slash-normalization,
bare-vs-namespaced constant recognition, hook consultation,
engine-fallback-last guarantee, deferred validation (throw at
getsmarty, no throw at config-load), non-array/non-string/relative
input rejection, SHAREDTMPLDIR default, and a `_getsmarty()`
cleanup audit (grep ensures no live references remain after
the C4/C5 deletions).

**Files modified.**

| Repo | File | Change |
|---|---|---|
| bbsengine6 | `php/bbsengine6config.php` | SHAREDTMPLDIR default; templatedirs\normalize() + extra_dirs() + hook dispatcher; SMARTYTEMPLATESDIR/PLUGINSDIR normalization moved to runtime |
| bbsengine6 | `php/engine.php` | getsmarty() simplified; deferred validation; type/absoluteness input checks; engine plugin-dir auto-append |
| bbsengine6 | `php/test_smarty_templatedirs.php` | New file (16 test cases) |
| bbsengine6 | `www/org/php/bbsengine4.php` | Delete _getsmarty() (113-192) + fallback getsmarty() (194-209); 9 callsite updates |
| bbsengine6 | `www/org/php/bbsenginedotorg.php` | Delete legacy getsmarty() wrapper (lines 263-277) |
| bbsengine6 | `www/org/php/{post,login,register,archive}.php` | 10 callsites: `getsmarty()` -> `\bbsengine6\getsmarty()` |
| bbsengine6 | `www/org/config-prod.php` | TEOSDIR env var fix; simplified SMARTYTEMPLATESDIR (2 entries + engine auto-append); use SHAREDTMPLDIR |
| bbsengine6 | `www/com/config-prod.php` | Simplified SMARTYTEMPLATESDIR (2 entries); use SHAREDTMPLDIR; drop redundant global-alias defines |
| bbsengine6 | `CHANGELOG.md` | This entry |
| teos | `www/config-prod.php` | New hook: `\bbsengine6\templatedirs\hook_extra_dirs()`; simplified SMARTYTEMPLATESDIR (2 entries + engine auto-append); use SHAREDTMPLDIR |
| achilles | `www/config-prod.php` | Simplified SMARTYTEMPLATESDIR; use SHAREDTMPLDIR |
| asimov | `www/config-prod.php` | Simplified SMARTYTEMPLATESDIR (dedup'd duplicate shared entry); use SHAREDTMPLDIR |
| murdermotel | `www/config-prod.php` | Simplified SMARTYTEMPLATESDIR (dedup'd duplicate shared entry); use SHAREDTMPLDIR |
| zoid6 | `sites/www/config-prod.php` | Simplified SMARTYTEMPLATESDIR (dedup'd duplicate shared entry); use SHAREDTMPLDIR; removed duplicate ENGINEURL/etc block |
| zoid6 | `sites/www/config.php` | Same as config-prod.php |
| zoid6 | `sites/www/config-dev.php` | Same as config-prod.php |
| zoid6 | `sites/engine/config-prod.php` | Simplified SMARTYTEMPLATESDIR; use SHAREDTMPLDIR; add bbsengine6config.php require |
| zoid6 | `sites/engine/html/config.php` | Same as config-prod.php |
| zoid6 | `php/zoid6.php` | Delete `\zoid6\getsmarty()` wrapper (unused) |
| zoid6 | `sites/www/php/lib.php` | Delete dead commented-out getsmarty() block |

**Deploy.** Sandbox can't write to `/srv/www/...` directly. The
deploy script (`scripts/deploy_bbsengine6config_fix.sh` in the
meta-repo) needs to land the modified files on merlin. Sandbox
verification ran `test_smarty_templatedirs.php` (16/16 pass),
`test_smarty_pluginsdir.php` (8/8 pass), `test_checkflag_graceful.sh`
(10/10 pass), and `test_smarty_paths.sh` against deployed vhost
configs (13/13 pass). Live HTTP tests against bbsengine.org
require the deploy and were not run from the sandbox.

### fix(bbsengine6): bbsengine6config.php + menu extension point + drop zoid6 hard-require

Three compounding fixes that unblock the `errormessage.tmpl`
regression on vhosts whose `config.php` was no longer loaded by
the router entry-point, and decouple bbsengine6 from a hard
zoid6 dependency:

1. **Self-owned config defaults (`php/bbsengine6config.php`)**.
   `engine/router.php -> page\error() -> displaypage() -> getsmarty()`
   could not find `errormessage.tmpl` because
   `\config\SMARTYTEMPLATESDIR` was undefined on vhosts whose
   `config.php` was not on the include path when the router
   dispatched.

   **Regression timeline.** `engine/router.php` previously did
   `require_once('config.php')` to load the vhost config. That
   require was commented out in commit `45b0b71`
   (`chore(bbsengine6): router/util/htaccess-prod tweaks`,
   2026-09-11) along with several other requires; commit
   `27435ea` (`fix(engine/router): fix strlower typo, ...`,
   2026-09-14) re-enabled `markdown.php`, `blurb.php`,
   `engine.php` but **forgot to re-enable `config.php`**.
   `php/page.php`'s `require_once("config.php")` was
   independently removed in commit `26ca33e` (2026-09-16,
   "drop dead config.php require in page.php") on the
   rationale that it referenced no live `\config\*` constants.
   After that, no bbsengine6 source file loaded the vhost
   config — so the namespaced `config\SMARTY*` constants
   relied entirely on `engine.php`'s `getsmarty()` fallback to
   `[]` when undefined. The teos vhost lost its templates.
   The wwworg vhost was unaffected because its deployed
   `engine/router.php` was an older copy that still had
   `require_once("config.php");` on line 51.

   **The fix.** `php/bbsengine6config.php` (NEW file) ships
   bbsengine6-owned defaults for `config\SMARTYTEMPLATESDIR`
   (`/srv/www/bbsengine6/skin/tmpl/`), `config\SMARTYPLUGINSDIR`,
   `config\SMARTYCOMPILEDTEMPLATESDIR`, plus shared URL/path
   constants (`ENGINEURL`, `ENGINESKINURL`, `SHAREDSKINURL`,
   `STATICSKINURL`), `config\SYSTEMDSN`, and `config\LOGENTRYPREFIX`.
   All use the `if (!defined(...))` pattern so vhost
   `config.php` values win when defined first. The file
   attempts `require_once("config.php")` via include_path at
   the top, so vhosts whose include_path includes the vhost
   docroot (set up via `VHOSTDOCROOT` SetEnv + `bbsengine6\bootstrap()`)
   get their namespaced constants loaded automatically.

   Loaded transitively from `php/engine.php`. Vhost config-prod.php
   files (`www/org/`, `www/com/`) and the deployed teos/wwworg
   `config.php` files updated to `require_once('bbsengine6config.php')`
   after defining their namespaced constants, for symmetry.

2. **Menu extension point (`bbsengine6\menu\buildchoices()`)**.
   `engine/router.php` and `php/blurb.php` previously called
   `\zoid6\buildchoices($choices)` directly (or via
   `function_exists` guards). bbsengine6 now exposes a canonical
   menu-building function in the `bbsengine6\menu` namespace.
   Default implementation returns `$choices` unchanged (no menu).
   Vhosts that want a cross-site menu define their own
   `bbsengine6\menu\hook_buildchoices()` function (which the
   canonical `buildchoices()` delegates to via `function_exists`
   lookup).

3. **bbsengine6 no longer hard-requires zoid6.** Removed
   `require_once(zoid6/php/bootstrap.php)`,
   `require_once("zoid6config.php")`, `require_once("zoid6.php")`
   from `php/blurb.php`. The `function_exists('\zoid6\buildchoices')`
   guards in `engine/router.php` (lines 434, 613 pre-fix) are
   replaced with direct extension-point calls. `bbsengine6config.php`
   installs a zoid6 `hook_buildchoices` shim when zoid6 happens to
   be loaded — preserving the cross-site menu on vhosts that
   already use zoid6 without making bbsengine6 aware of zoid6
   at the call sites.

   **Verification of "no zoid6 references in bbsengine6 source".**
   After this commit:
   ```
   $ grep -rn "zoid6" bbsengine6/{php,engine,smarty,skin} \
       | grep -v "\.git/" | grep -v "/py/" | grep -v "/handbook/" \
       | grep -v "\.md:"
   bbsengine6/php/bbsengine6config.php:   (one reference inside
                                            the zoid6 hook shim block)
   ```
   The shim is opt-in: if zoid6 isn't loaded, the hook function
   isn't installed and the menu is empty. bbsengine6 source code
   at `php/engine.php`, `php/blurb.php`, `engine/router.php`,
   `php/page.php`, `php/session.php`, `php/folder.php`, and all
   of `php/smarty/` has zero `zoid6` references.

   Also cleaned up the dead `/// require_once('config.php')`
   comment in `php/session.php`, and the unrelated missing
   semicolon in `php/folder.php::getTopLevelFolders()`.

**Deploy.** The fix requires updating deployed paths via the
new `deploy_bbsengine6config_fix.sh` script (in the meta-repo
root). Sandbox can't write to `/srv/www/bbsengine6/` or
`/srv/www/vhosts/...` directly; run the script as the `jam`
user (or whoever owns those paths) to land:
- `/srv/www/bbsengine6/php/{bbsengine6config.php,engine.php,blurb.php,session.php,folder.php}`
- `/srv/www/vhosts/zoidtechnologies.com/html/engine/router.php`
- `/srv/www/vhosts/www.bbsengine.org/html/engine/router.php`
- in-place `require_once('bbsengine6config.php')` insertion in
  `/srv/www/vhosts/zoidtechnologies.com/html/teos/config.php`
  and `/srv/www/vhosts/www.bbsengine.org/html/config.php`

The script is idempotent — re-running is safe.

**Verification.** Regression tests at
`/tmp/test_regression.php` (vhost scenario with zoid6) and
`/tmp/test_nozoid6.php` (no-zoid6 scenario) both PASS. The
key assertion: `$s->templateExists("errormessage.tmpl") === true`
in both cases. (These test scripts are in `/tmp/` and not
checked in; they were scratch tests run during development.)

### feat(engine/router): 'pattern' attribute on handler registry

`router_gethandlers()` entries may now carry an optional
`pattern` (PCRE regex, anchored `^...$`). The dispatch loop
`preg_match()`es the URI against the pattern; on miss the
handler is skipped without invocation, avoiding
filesystem/DB probes for obviously non-matching URIs (e.g.
`/contact-us` should not probe for markdown files or
ltree-pathed blurbs). A `null` pattern means "always try".
Compile failure is logged and falls through to handler
invocation. `error` is intentionally removed from the
registry; the dispatch loop's post-loop fallback is the
single point of truth for 404s.

Pattern summary:

| Handler  | Pattern                                |
|----------|----------------------------------------|
| index    | `^/?$`                                 |
| blurb    | `[A-Za-z0-9_][A-Za-z0-9_./-]*`         |
| folder   | (null — filesystem probe)              |
| markdown | `[A-Za-z0-9_][A-Za-z0-9_./-]*`         |
| page     | `[a-z][a-z0-9-]*` (bare lowercase slug) |

### fix(engine/router, serve-tmpl): teospath typos, ROUTER_RENDERED sentinel, breadcrumb root path

Five related cleanups in router.php and serve-tmpl.php:

1. `router_handleMarkdown` used undefined `$teospath` (typo)
   in two `router_safe_path_web()` calls. Renamed to
   `$teosdir` to match the env() lookup at the top of the
   function. Latent bug — masked only because
   `router_safe_path_web` no-ops when
   `\bbsengine6\util\safe_path_web` isn't loaded.
2. Replaced the implicit empty-string-as-success contract
   with a `ROUTER_RENDERED` sentinel. Handlers that render
   via `displaypage()` (`router_handleBlurb`,
   `router_displayMarkdownFile`, `servePage`,
   `router_handleError`) now return the sentinel; the
   dispatcher maps it to `''`. Makes the contract explicit
   and removes the foot-gun where an accidental
   `return '';` would silently short-circuit the chain.
3. `router_handleError` now returns `ROUTER_RENDERED`
   instead of `null`. Previously the dispatcher would see
   `null` and the HTTP entry-point would emit
   "Router Error (null)" with a 500.
4. `router_buildBreadcrumbs` had an open-question comment
   ("why are there two attributes with the same value?")
   about the root crumb's `path` field. Hardcoded to
   `'teos'` to match `blurb.php::buildbreadcrumbs` (line
   80), which is the canonical reference for the
   ltree-rooted identifier.
5. `ROUTER_STOP` define removed; nothing returned it.

`serve-tmpl.php` declares `ROUTER_RENDERED` too (it loads
before router.php and its `servePage()` needs the sentinel
at return time).

### docs(router): markdown pattern comment documents the .md strip

The `markdown` handler entry's pattern
(`#^/?[A-Za-z0-9_][A-Za-z0-9_./-]*$#`) has no `.md`
anywhere. The reason is non-obvious: the HTTP entry-point
strips a trailing `.md` once at the top of the script
(`engine/router.php` line ~724:
`preg_replace('/\.md$/', '', $path)`), so by the time the
dispatch loop preg_match()es this pattern the URI never
carries a `.md` suffix. The handler then probes the
filesystem for the bare `<reluri>` under `TEOSDIR` (no
extension appended).

Without the comment, a reader scanning the registry sees
an asymmetry they can't explain: `page` has a two-pass
probe that appends `.tmpl`, but `markdown` has no `.md`
anywhere. The asymmetry is real and intentional — but
until this comment, only the dead-code removal commit
recorded why.

Adds an inline comment in the registry entry that names
the entry-point strip and the bare `<reluri>` probe
(`router_handleMarkdown` line ~371). Compare-and-contrast
to the `page` handler's two-pass probe. No behaviour
change.

### fix(engine/router, serve-tmpl): drop dead .md probe; replace ROUTER_STOP in handleIndex

Two related cleanups:

1. `router_handleMarkdown` did a two-pass extension probe
   (`$reluri . '.md'`, then bare `$reluri`) mirroring the
   `.tmpl` probe in `router_handlePage`. The `.md` branch
   was dead code: the HTTP entry-point strips a trailing
   `.md` once at the top of the script (`router.php`:
   `preg_replace('/\.md$/', '', $path)`), so by the time
   the dispatch loop walks handlers the URI never carries
   a `.md` suffix. The `.tmpl` branch in `serve-tmpl.php`
   is still legitimate because `.tmpl` is NOT stripped at
   the entry-point — htaccess rewrites bare slugs (e.g.
   `/contact-us`) into the router with no extension, so
   the handler has to append `.tmpl` itself.

   Updated `serve-tmpl.php`'s doc comments that referenced
   "router_handleMarkdown's two-pass extension probe" to
   describe the actual remaining two-pass handler (page)
   and explain why the markdown handler dropped it.

   Added regression guards in `php/test_router.php`:

   - **Test 6a** — handler body MUST NOT contain a
     `'$uri . .md'` probe (regression guard against
     re-introducing the dead branch).
   - **Test 6b** — HTTP entry-point MUST strip trailing
     `.md` before dispatch (the contract that makes the
     dead-code removal safe).

2. `router_handleIndex` returned `ROUTER_STOP` after
   including `TEOSDIR/index.php`. `ROUTER_STOP` was
   retired in the 2026-09-19 cleanup; the reference was
   missed (the LSP error showed up but no inner commit
   addressed it). In PHP 7 this returned the literal
   string `"ROUTER_STOP"` which the HTTP entry-point
   would echo (empty body); in PHP 8 it throws a fatal
   "Undefined constant" on every `/` request that hits
   an `index.php`. Replaced with `ROUTER_RENDERED`: the
   included `index.php` is expected to render to stdout
   (either via `displaypage()` or direct `echo`), and
   the sentinel tells the dispatcher the body is already
   on the wire.

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
