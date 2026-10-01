<?php

namespace bbsengine6\router;

/**
 * router.php - Handler registry for routing requests.
 *
 * Handler order: index -> blurb -> folder -> markdown -> page
 *
 * Each handler entry may carry an optional `pattern` (PCRE regex).
 * The dispatch loop matches the URI against the pattern; on miss
 * the handler is skipped without invocation, avoiding filesystem
 * and DB probes for obviously non-matching URIs. A null/absent
 * pattern means "always try".
 *
 * As of 2026-09-29 the HTTP entry point no longer strips a trailing
 * ".md" before pattern matching. Handlers that don't care about the
 * .md suffix must pattern-gate or strip it themselves; the
 * dispatch loop passes the full URI (with extension) to every
 * handler. The router_handleRawMarkdown handler covers
 * raw text/plain .md URLs on every vhost (handbook and non-handbook):
 * htaccess-prod's SetEnv TEOSDIR points the resolver at the right
 * basedir for the active vhost (handbook vhost: /handbook/<v>/,
 * teos vhost: /teos/) and the rawmarkdown handler dispatches via
 * \bbsengine6\markdown\serveRawMarkdown().
 *
 * As of 2026-10-XX the raw-markdown library (\bbsengine6\markdown\serveRawMarkdown)
 * lives in php/markdown.php; engine/serve-md.php is gone — the
 * handbook vhost's htaccess-prod rewrites /handbook/<v>/<uri>.md
 * directly to /engine/router.php?uri=$2, no per-vhost shim needed.
 *
 * ROUTER_NEXT instructs the loop to continue on to the next handler.
 * ROUTER_RENDERED means "I rendered via displaypage() (or otherwise
 * emitted headers + body myself, as router_handleRawMarkdown does);
 * the body is already on stdout" -- the dispatcher maps this to
 * an empty return string so the HTTP entry-point emits nothing
 * more. Returning null or false continues to the next handler.
 * Returning a non-empty string short-circuits and emits the body.
 *
 * `error` is intentionally NOT in the registry: the dispatch loop
 * falls through to router_handleError($uri) when no handler
 * matches, so registering it would fire it twice on a miss.
 *
 * No handler may ever produce a WSOD.
 * The error handler must always produce either a return string or end the request.
 *
 * Directory listings (router_collectDirectoryItems + router_dedupeItems)
 * filter out editor backup files and case-variant duplicates via
 * router_isIgnoredEntry(). See handbook/ROUTER.md and
 * teos/SPEC.md section 9.6 for the policy and patterns covered.
 *
 * Shared by both the teos/www vhost (TEOSURL=/teos/) and the handbook
 * vhost at bbsengine.org (TEOSURL=/handbook/<v>/). Each vhost's
 * htaccess-prod rewrites its URIs to /engine/router.php?uri=<rel>
 * AND publishes TEOSURL/TEOSDIR/TEOSLABEL via SetEnv. The engine
 * is site-agnostic: it reads those env vars via
 * \bbsengine6\util\env() (which prefers getenv() over the constant
 * over the empty default) and never overrides them per-request.
 * Handlers that depend on teos-only helpers (bbsengine6\blurb\*,
 * bbsengine6\folder\*) no-op to ROUTER_NEXT when those helpers are absent.
 *
 * Menu choices are populated via the canonical bbsengine6 menu
 * extension point \bbsengine6\menu\buildchoices() (defined in
 * php/bbsengine6config.php, loaded transitively via php/engine.php).
 * bbsengine6 source code stays zoid6-agnostic; vhosts that want a
 * cross-site menu define their own bbsengine6\menu\hook_buildchoices()
 * function or load zoid6 themselves before this router runs.
 *
 * @since 2026
 * @since 2026-09-29 — VHOSTCONFIG resolver removed. The router is the
 * HTTP entry point for every vhost (teos + handbook + future). It loads
 * engine.php, which loads bbsengine6config.php, which expects
 * \config\SMARTYTEMPLATESDIR (and friends) to already be defined by
 * the vhost's config.php. bbsengine6config.php resolves config.php via
 * stream_resolve_include_path("config.php"), which depends on
 * bbsengine6\bootstrap() having prepended VHOSTDOCROOT to include_path.
 * If VHOSTDOCROOT is unset on FPM, getsmarty() throws its existing
 * "SMARTYTEMPLATESDIR is not configured" RuntimeException (the
 * pre-2026-09-24 failure mode).
 * @since 2026-10-XX — VHOSTCONFIG resolver restored. The 02eebac
 * removal turned out to be premature: on merlin's mod_proxy_fcgi +
 * FPM pool, Apache's SetEnv directives (VHOSTDOCROOT, TEOSDIR) do not
 * propagate to the FPM worker, so the include_path-only chain at
 * bbsengine6config.php:51 misses the vhost config and \config\SMARTYTEMPLATESDIR
 * is undefined. The fix is engine/vhostconfig.php, which loads the
 * vhost's config.php via VHOSTCONFIG env (absolute path; set by every
 * htaccess-prod in the repo) with a SCRIPT_FILENAME probe fallback for
 * deployments where Apache's env vars don't reach FPM at all.
 * Both code paths work without depending on FPM env propagation.
 */

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once('util.php');
require_once("vhostconfig.php");
\bbsengine6\router\router_resolve_vhost_config();

require_once('markdown.php');
require_once('blurb.php');
require_once('engine.php');
require_once("page.php");
require_once("folder.php");

// @since 2026-09-16 — hands page-namespace URIs
// (e.g. /contact-us -> DOCUMENTROOT/skin/tmpl/contact-us.tmpl)
// to bbsengine6\servepage\router_handlePage via the
// router_gethandlers() chain below.
require_once("serve-tmpl.php");

if (!defined('ROUTER_NEXT')) { define('ROUTER_NEXT', 'ROUTER_NEXT'); }
// @since 2026-09-19 — explicit sentinel for "I rendered via
// displaypage() and the body is already on stdout; the HTTP
// entry-point should emit nothing more". Replaces the implicit
// empty-string-as-success contract (an empty string used to
// short-circuit the chain, which was a foot-gun for future
// handlers that returned '' unintentionally).
if (!defined('ROUTER_RENDERED')) { define('ROUTER_RENDERED', 'ROUTER_RENDERED'); }

router_log("router.300: ".var_export(get_include_path(),true));

function router_log(string $message, string $level = "info"): void
{
  \bbsengine6\util\logentry("router.".strtolower($level).':'.$message);
}

///function router_get_teosurl(): string
///{
  // @since 2026-09-09 — thin wrapper kept for backward compat.
  // Prefer \bbsengine6\util\teos_url() in new code; this function
  // delegates to it.
///  return \bbsengine6\util\teos_url();
//}

///function router_get_teosdir(): string/
///{
///  // @since 2026-09-09 — thin wrapper kept for backward compat.
///  // Prefer \bbsengine6\util\teos_dir() in new code; this function
///  // delegates to it.
///  return \bbsengine6\util\teos_dir();
///}

/**
 * Wrapper around bbsengine6\util\safe_path_web that no-ops to
 * false when the helper is undefined.
 *
 * The router's bootstrap chain may fail on a partial
 * php-deploy-prod (where util.php hasn't landed yet); in
 * that case the require_once raises a Warning to the error
 * log, the helper isn't defined, and downstream handler
 * code would fatal with "Call to undefined function". The
 * wrapper lets the handler chain fall through to
 * handleError's 404 page instead. PHP still raises on the
 * missing require_once -- this helper doesn't suppress
 * that warning; it only guards the secondary call-site
 * fatal.
 *
 * @param array $components Path components relative to base_dir.
 * @param array $opts       Options (base_dir, must_exist, resolve_symlinks).
 * @return string|false     Resolved path string, or false on
 *                          failure (including when the helper
 *                          isn't loaded).
 */
function router_safe_path_web(array $components, array $opts = []): string|false
{
  return \bbsengine6\util\safe_path_web($components, $opts);
}

function router_buildBreadcrumbs(string $uri): array
{
  $segments = array_values(array_filter(explode("/", trim($uri, "/"))));
  if (empty($segments)) {
    return [];
  }

  $teosurl = rtrim(\bbsengine6\util\env("TEOSURL", "NEEDINFO:teosurl"));


  // Build breadcrumbs from URI segments
  $autoCrumbs = [];
  $path = '';
  foreach ($segments as $segment) {
    $path = $path === '' ? $segment : $path . '.' . $segment;
    $title = str_replace(['-', '_'], ' ', $segment);
    $uri_path = $teosurl . '/' . implode('/', array_slice($segments, 0, count($autoCrumbs) + 1)) . '/';
    $autoCrumbs[] = [
      'title' => $title,
      'path' => $path,
      'uri' => $uri_path,
    ];
  }

  $rootlabel = \bbsengine6\util\env("TEOSLABEL", "NEEDINFO:TEOSLABEL.buildbreadcrumbs.100");
  // Root crumb: title is per-vhost via TEOSLABEL (default
  // "teos", overridden to "bbsengine6 handbook" on the .org
  // vhost by that vhost's htaccess-prod SetEnv TEOSLABEL); the
  // internal path identifier stays "teos" to match blurb.php's
  // buildbreadcrumbs() (line 80) -- both consumers of the
  // breadcrumb list need a consistent ltree-path-rooted
  // identifier so the DB-driven and filesystem-driven paths
  // are interchangeable.
  array_unshift($autoCrumbs, [
    'title' => $rootlabel,
    'path'  => 'teos',
    'uri'   => $teosurl . '/',
  ]);

  return $autoCrumbs;
}

function router_gethandlers(): array
{
  // FQCN strings so the variable-function dispatch below resolves
  // each handler in the right namespace. Before the 2026-09-15
  // namespace refactor (bfaca68) these were bare names that
  // resolved correctly in the global namespace; once router.php
  // declared `namespace bbsengine6\router;`, the same bare names
  // broke because PHP variable-function calls do not apply the
  // call-site namespace. Production saw the regression on
  // 2026-09-16 as `Call to undefined function router_handleIndex()`
  // in engine/router.php, traced from frame #0 in the dispatch
  // loop. Fixed in ccbe268.
  //
  // @since 2026-09-19 — entries may carry an optional `pattern`
  // (PCRE regex, anchored). The dispatch loop preg_match()es the
  // URI against it and skips the handler on miss, avoiding
  // filesystem/DB probes for obviously non-matching URIs.
  // A null pattern means "always try". `error` is intentionally
  // omitted; the dispatch loop falls through to
  // router_handleError($uri) when nothing else matches.
  //
  // Pattern semantics:
  //   - matched against $path (the post-".md"-strip URI from the
  //     HTTP entry point, so "/contact-us" not "/contact-us.md")
  //   - full-match (anchored with ^...$)
  //   - compile-failure is treated as "always try" (defensive)
  return [
    'index' => [
      'fn'      => 'bbsengine6\\router\\router_handleIndex',
      'pattern' => '#^/?$#',
    ],
    'blurb' => [
      'fn'      => 'bbsengine6\\router\\router_handleBlurb',
      // hierarchical dot-paths like ec/john-edward
      'pattern' => '#^/?[A-Za-z0-9_][A-Za-z0-9_./-]*/?$#',
    ],
    'folder' => [
      'fn'      => 'bbsengine6\\router\\router_handleFolder',
      'pattern' => null, // filesystem probe decides
    ],
    'markdown' => [
      'fn'      => 'bbsengine6\\router\\router_handleMarkdown',
      // No '.md' (or any '.') in the character class on purpose:
      // the HTTP entry-point no longer strips a trailing '.md'
      // (since 2026-09-29), so the dispatch loop preg_match()es
      // the raw URI including any extension. Dot-containing
      // URIs (e.g. "/ec/foo.md") are routed to router_handleRawMarkdown
      // below via its /\.md$/ pattern, not this handler. URIs
      // with bare dots elsewhere (e.g. "ec/v2.0/foo") are also
      // excluded here — no legitimate catalog URI carries a dot,
      // since blurb IDs use dots as separators (blurb.php's
      // str_replace("/", ".", ...)) rather than URI paths. The
      // handler then probes the filesystem for the bare <reluri>
      // under TEOSDIR with a '.md' appended — see
      // router_handleMarkdown below.
      'pattern' => '#^/?[A-Za-z0-9_][A-Za-z0-9_/-]*$#',
    ],
    'page' => [
      'fn'      => 'bbsengine6\\servepage\\router_handlePage',
      // narrowest: bare lowercase slug (e.g. /contact-us)
      'pattern' => '#^/?[a-z][a-z0-9-]*/?$#',
    ],
    'rawmarkdown' => [
      'fn'      => 'bbsengine6\\router\\router_handleRawMarkdown',
      // /<uri>.md URLs across all vhosts (handbook + non-handbook).
      // The handbook vhost's htaccess-prod rewrites .md URLs to
      // /engine/router.php?uri=$2 (the same target the teos vhost
      // uses), so this handler is the single dispatch path for
      // raw .md across the entire codebase. The active vhost's
      // SetEnv TEOSDIR is the basedir against which
      // \bbsengine6\markdown\serveRawMarkdown() resolves the file;
      // htaccess-prod's per-vhost SetEnv drives the right basedir
      // automatically (handbook: /handbook/<v>/, teos: /).
      // The $ end-anchor naturally restricts the match to URIs
      // ending in '.md'; no negative lookahead is required to
      // exclude dot-bearing URIs from the other handlers (see
      // the markdown pattern comment above for the inverse gate).
      'pattern' => '/\.md$/',
    ],
  ];
}

function router_handleIndex(string $uri)
{
  router_log('handleIndex called with uri=' . var_export($uri, true));

  if ($uri !== '/' && $uri !== '') {
    router_log('not root path');
    return ROUTER_NEXT;
  }

  $teosdir = \bbsengine6\util\env("TEOSDIR");
  $indexfile = $teosdir . 'index.php';
  if (file_exists($indexfile)) {
    try {
      include($indexfile);
      // @since 2026-09-19 — return ROUTER_RENDERED instead
      // of the (now retired) ROUTER_STOP. The included
      // TEOSDIR/index.php is expected to render to stdout
      // (either via displaypage() or direct echo); the
      // sentinel tells the dispatcher the body is already on
      // the wire and the HTTP entry-point should emit
      // nothing more.
      return ROUTER_RENDERED;
    // @since 2026-09-17 — qualify the catch type with a
    // leading backslash so it resolves the global \Throwable,
    // not the non-existent `bbsengine6\router\Throwable`.
    } catch (\Throwable $e) {
      router_log('index include failed: ' . $e->getMessage());
      return ROUTER_NEXT;
    }
  }

  $mdfile = $teosdir . 'index.md';
  if (file_exists($mdfile) && is_file($mdfile)) {
    return router_displayMarkdownFile($mdfile, $uri);
  }

  router_log('index.php and index.md both missing', 'warning');
  return ROUTER_NEXT;
}

function router_handleBlurb(string $uri)
{
  router_log('handleBlurb: ' . $uri);

  if (!function_exists('\bbsengine6\blurb\isBlurb')) {
    return ROUTER_NEXT;
  }

  if (\bbsengine6\blurb\isBlurb($uri)) {
      try {
        // @since 2026-09-17 — leading-backslash namespace
        // lookup. router.php is in `namespace bbsengine6\router;`;
        // bare `bbsengine6\blurb\display()` would resolve to
        // the non-existent
        // `bbsengine6\router\bbsengine6\blurb\display()`. The
        // sibling isBlurb() call above uses the leading
        // backslash; this display() call site was missed
        // by bfaca68.
        \bbsengine6\blurb\display($uri, null);
        // @since 2026-09-19 — return ROUTER_RENDERED (the new
        // sentinel) instead of ''. The dispatch loop emits
        // nothing on this return, same effect, but the
        // sentinel makes the contract explicit and removes
        // the foot-gun of empty-string-short-circuit.
        return ROUTER_RENDERED;
      } catch (\Throwable $e) {
        router_log('blurb display failed: ' . $e->getMessage(), 'error');
        return ROUTER_NEXT;
      }
  }
  return ROUTER_NEXT;
}

function router_handleFolder(string $uri)
{
  router_log('handleFolder: ' . $uri);
  $teosdir = \bbsengine6\util\env("TEOSDIR", "NEEDINFO:router_handlefolder:teosdir");
  if ($teosdir === '') {
    router_log('TEOSDIR not configured, skipping folder handler');
    return ROUTER_NEXT;
  }

  $reluri = ltrim($uri, '/');
  $filepath = router_safe_path_web([$reluri], ['base_dir' => $teosdir]);
  if ($filepath === false) {
    router_log('router_handleFolder.120: path validation failed', 'warning');
    return ROUTER_NEXT;
  }

  if (!is_dir($filepath)) {
    router_log('router_handleFolder.100: no directory found');
    return ROUTER_NEXT;
  }

  // folder visibility check (optional: only meaningful for the teos tree)
  $isVisible = true; $isSysop = false;
  try {
    // @since 2026-09-17 — qualify the namespace lookup with a
    // leading backslash. router.php declares `namespace
    // bbsengine6\router;` (bfaca68), so an unqualified
    // `bbsengine6\folder\isFolderVisible()` call resolves to
    // `bbsengine6\router\bbsengine6\folder\isFolderVisible()`,
    // which does not exist (the function lives in
    // `bbsengine6\folder`). Variable-function dispatch (line
    // ~600) honors call-site namespace because the call is
    // routed through the FQCN table returned by
    // router_gethandlers(), but bare names in this function
    // body do not.
    $isVisible = \bbsengine6\folder\isFolderVisible($uri);
    $isSysop = \bbsengine6\folder\isSysop();
  } catch (\Throwable $e) {
    \bbsengine6\util\echo_traceback("folder visibility check failed");
    router_log('folder visibility check failed: ' . $e->getMessage(), 'error');
    $isVisible = true;
    $isSysop = false;
  }

  if (!$isVisible && !$isSysop) {
    return ROUTER_NEXT;
  }

  // @since 2026-09-10 — wrap the listing render in a try/catch
  // so a database failure inside the renderer (the chain
  // bbsengine6\displaypage -> getsmarty -> ... -> zoid6\buildchoices
  // -> member\lib\checkflag -> engine.checkflag SQL function)
  // doesn't 500 the request. Log and let the next handler try.
  try {
    return router_displayDirectoryListing($filepath, $uri, (!$isVisible && $isSysop));
  } catch (\Throwable $e) {
    router_log('directory listing render failed: ' . $e->getMessage(), 'error');
    return ROUTER_NEXT;
  }
}

function router_handleMarkdown(string $uri)
{
  router_log('handleMarkdown: ' . $uri);
  $teosdir = \bbsengine6\util\env("TEOSDIR", "NEEDINFO:router_handlemarkdown");
  \bbsengine6\util\logentry("router_handleMarkdown.100: teosdir=".var_export($teosdir, true));
  if ($teosdir === '') return ROUTER_NEXT;

  // @since 2026-09-07 — see router_handleFolder for the
  // leading-slash rationale.
  //
  // @since 2026-09-26 — restore the `.md` append on the
  // filesystem probe. The HTTP entry-point strips a trailing
  // ".md" from the URI once at the top of this script
  // (preg_replace('/\.md$/', '', $path)) so the dispatch loop
  // walks handlers with bare segments. The handler must
  // re-append ".md" for the filesystem probe: every teos doc
  // on disk is named `<slug>.md`, never `<slug>`. There is no
  // extensionless-doc layout in this tree.
  //
  // @since 2026-09-29 — the entry-point strip is removed
  // (see top-of-file docblock). This handler's pattern in
  // router_gethandlers() no longer admits '.md' (or any '.')
  // in the URI character class, so the dispatch loop should
  // never deliver a '.md$'-suffixed URI here. The defensive
  // preg_replace below is belt-and-suspenders: if a future
  // registry change reintroduces dot-containing URIs to this
  // handler, the probe still resolves correctly rather than
  // double-appending to `<slug>.md.md`.
  //
  // A 2026-09-19 refactor previously dropped the `.md` append
  // after misreading the entry-point strip as a probe strip.
  // That commit was latent (no test pinned it; see
  // php/test_router.php which only covers the breadcrumb
  // helper) and only surfaced after the September TEOSDIR
  // audit landed the correct vhost path. Mirrors
  // engine/serve-tmpl.php's `.tmpl` probe for the page-
  // namespace URIs, where bare slugs (e.g. /contact-us) come
  // out of htaccess without any extension and the handler
  // has to re-attach it before the filesystem probe.
  $reluri = ltrim($uri, '/');
  $reluri = preg_replace('/\.md$/', '', $reluri);
  $filepath = router_safe_path_web([$reluri . '.md'], ['base_dir' => $teosdir]);
  if ($filepath !== false && file_exists($filepath) && is_file($filepath)) {
    // @since 2026-09-10 — same graceful-degradation wrapper as
    // router_handleBlurb / router_handleFolder: a DB failure
    // during markdown rendering (e.g. breadcrumb lookup) must
    // not 500 the request.
    try {
      return router_displayMarkdownFile($filepath, $uri);
    } catch (\Throwable $e) {
      router_log('markdown render failed: ' . $e->getMessage(), 'error');
      return ROUTER_NEXT;
    }
  }
  return ROUTER_NEXT;
}

function router_handleRawMarkdown(string $uri)
{
  router_log('handleRawMarkdown: ' . $uri);
  $teosdir = \bbsengine6\util\env("TEOSDIR");
  if ($teosdir === '') return ROUTER_NEXT;

  // @since 2026-09-29 — raw text/plain dispatcher for .md URLs.
  // Reuses the canonical library \bbsengine6\markdown\serveRawMarkdown()
  // at php/markdown.php (merged from php/serve-md.php on 2026-10-XX)
  // which enforces realpath-based containment under the supplied
  // base dir, .md-only extension, and file-only (rejects directories).
  // On a hit the library emits `Content-Type: text/plain; charset=utf-8`
  // itself and reads the body to stdout; we return ROUTER_RENDERED so the
  // HTTP entry-point emits nothing more. On a miss (or any
  // validation failure) the library returns false and we fall
  // through to ROUTER_NEXT so the dispatch chain reaches
  // router_handleError for the styled 404 — same shape as a
  // chrome-rendered URI miss.
  //
  // The handler's pattern in router_gethandlers() is /\.md$/ so
  // this branch only fires for .md-suffixed URIs. Per-vhost htaccess
  // rewrites are responsible for routing .md URLs here. The handbook
  // vhost's htaccess-prod rewrites /handbook/<v>/<uri>.md to
  // /engine/router.php?uri=$2 (same target as the teos vhost), and
  // the vhost's SetEnv TEOSDIR = /srv/www/vhosts/www.bbsengine.org/
  // html/handbook/<v>/ makes the resolver probe the right file under
  // the handbook home — no separate entry-point shim needed.
  $reluri = ltrim($uri, '/');
  if (\bbsengine6\markdown\serveRawMarkdown($teosdir, $reluri)) {
    return ROUTER_RENDERED;
  }
  return ROUTER_NEXT;
}

function router_handleError(string $uri)
{
  $msg = 'Page not found: ' . htmlspecialchars($uri);
  router_log($msg, 'error');

  \bbsengine6\page\error($msg, 404);
  http_response_code(404);
  // @since 2026-09-19 — return ROUTER_RENDERED sentinel.
  // page\error() already rendered via displaypage(), so the
  // HTTP entry-point should emit nothing more. (Pre-2026-09-19
  // the function returned null, which the HTTP entry-point
  // translated to "Router Error (null)" with a 500.)
  return ROUTER_RENDERED;
}

function router_displayMarkdownFile(string $filepath, string $uri): string
{
  $content = file_get_contents($filepath);
  if ($content === false) {
    return '';
  }

  $parsed = \bbsengine6\markdown\parseDocument($content, split: false, breaks: true);

  $doc = $parsed['doc'];
  $doc['title'] = isset($doc['title']) ? htmlspecialchars($doc['title']) : basename($filepath, '.md');
  $doc['date']  = isset($doc['date'])  ? htmlspecialchars($doc['date'])  : '';

  \bbsengine6\setcurrentpage(rtrim(\bbsengine6\util\env("TEOSURL", "NEEDINFO:displaymd:teosurl"), '/') . $uri);

  $uri_parts = explode("/", $uri);
  array_pop($uri_parts);
  $breadcrumbs = router_buildBreadcrumbs(implode("/", $uri_parts));

  // @since 2026-09-24 — use the canonical bbsengine6 menu extension
  // point. bbsengine6config.php's zoid6 hook shim installs a
  // bbsengine6\menu\hook_buildchoices() when zoid6 is loaded, so
  // existing teos-vhost cross-site menu items continue to appear.
  $choices = [];
  try {
    $choices = \bbsengine6\menu\buildchoices($choices);
  } catch (\Throwable $e) {
    router_log('bbsengine6\menu\buildchoices failed: ' . $e->getMessage(), 'warning');
  }

  $data = [
    'title' => $doc['title'],
    'date' => $doc['date'],
    'content' => $doc['html'],
    'breadcrumbs' => $breadcrumbs,
    'choices' => $choices,
  ];

  \bbsengine6\displaypage($data, 'page-markdown.tmpl', false);
  // @since 2026-09-19 — return ROUTER_RENDERED sentinel; see
  // router_handleBlurb for the rationale.
  return ROUTER_RENDERED;
}

function router_isIgnoredEntry(string $entry): bool
{
  if ($entry === '' || $entry === '.' || $entry === '..') return true;

  if ($entry[0] === '.') {
    return true;
  }

  if (preg_match('/~+$/', $entry) === 1) {
    return true;
  }

  if (preg_match('/(^|\.)(swp|swo|swn|bak|orig|rej|tmp|temp|save)$/i', $entry) === 1) {
    return true;
  }

  if (preg_match('/^#.*#$/', $entry) === 1) {
    return true;
  }

  return false;
}

function router_collectDirectoryItems(string $dirpath, string $uri): array
{
  $safedir = realpath($dirpath);
  if ($safedir === false) {
    return [];
  }

  $entries = scandir($safedir);
  if ($entries === false) {
    return [];
  }

  $teosurl = rtrim(\bbsengine6\util\env("TEOSURL", "NEEDINFO:collect:teosurl"), '/');
  $items = [];

  foreach ($entries as $entry) {
    if (router_isIgnoredEntry($entry)) continue;
    $fullpath = $safedir . '/' . $entry;

    if (is_dir($fullpath)) {
      $dir_base = rtrim($teosurl, '/') . '/' . trim($uri, '/');
      if ($dir_base === rtrim($teosurl, '/') . '/') {
        $href = rtrim($teosurl, '/') . '/' . $entry . '/';
      } else {
        $href = $dir_base . '/' . $entry . '/';
      }
      $items[] = [
        'title' => $entry,
        'uri' => $href,
        'is_dir' => true,
        'filename' => $entry,
        'modified' => filemtime($fullpath),
      ];
      continue;
    }
    if (!is_file($fullpath)) continue;

    $ext = strtolower(pathinfo($entry, PATHINFO_EXTENSION));
    $name = pathinfo($entry, PATHINFO_FILENAME);
    $displayTitle = $name;
    $filename = $entry;
    $modified = filemtime($fullpath);

    if ($ext === 'md') {
      $filecontent = file_get_contents($fullpath);
      if ($filecontent !== false && strncmp($filecontent, '---', 3) === 0) {
        [$metadata, ] = \bbsengine6\markdown\splitFrontmatter($filecontent);
        // @since 2026-09-27 — escape the YAML-derived title.
        // folder.tmpl prints {$item.title} raw, so an unescaped
        // YAML `title: <script>...</script>` would be a stored
        // XSS. Mirror of php/folder.php:228 and the live blurb
        // path at php/markdown.php::splitFrontmatter callers.
        // Trim first so an empty or whitespace-only title
        // (`title:` / `title:   `) falls back to the filename
        // instead of rendering a blank link.
        $rawTitle = isset($metadata['title']) ? trim($metadata['title']) : '';
        if ($rawTitle !== '') {
          $displayTitle = htmlspecialchars($rawTitle, ENT_QUOTES | ENT_HTML5, 'UTF-8');
        }
      }
      $filename = $name;
    } else {
      $filename = $entry;
    }

    $file_href = rtrim($teosurl, '/') . '/' . trim($uri, '/');
    if ($file_href === rtrim($teosurl, '/') . '/') {
      $file_href = rtrim($teosurl, '/') . '/' . $name;
    } else {
      $file_href .= '/' . $name;
    }

    $items[] = [
      'title' => $displayTitle,
      'uri' => $file_href,
      'is_dir' => false,
      'filename' => $entry,
      'ext' => $ext,
      'size' => filesize($fullpath),
      'modified' => $modified,
    ];
  }

  usort($items, fn($a, $b) => strcasecmp($a['filename'], $b['filename']));

  return $items;
}

function router_dedupeItems(array $items): array
{
  $seen = [];
  $out = [];
  foreach ($items as $item) {
    $key = strtolower($item['filename'] ?? '');
    if ($key === '' || isset($seen[$key])) continue;
    $seen[$key] = true;
    $out[] = $item;
  }
  return $out;
}

function router_displayDirectoryListing(string $dirpath, string $uri, bool $hidden = false): string
{
  $safedir = realpath($dirpath);
  if ($safedir === false) {
    router_log('directory resolution failed', 'warning');
    return router_handleError($uri);
  }

  $items = router_collectDirectoryItems($dirpath, $uri);
  $items = router_dedupeItems($items);

  $title = basename($uri) ?: $uri;
  $teosurl = rtrim(\bbsengine6\util\env("TEOSURL", "NEEDINFO:displaydir:teosurl"), '/');

  \bbsengine6\setcurrentpage($teosurl.$uri);

  if (!function_exists('\bbsengine6\displaypage')) {
    router_log('displaypage unavailable; cannot render directory listing', 'error');
    return router_handleError($uri);
  }

  $breadcrumbs = router_buildBreadcrumbs($uri);

  // @since 2026-09-24 — use the canonical bbsengine6 menu
  // extension point. bbsengine6config.php's zoid6 hook shim
  // installs a bbsengine6\menu\hook_buildchoices() when zoid6
  // is loaded, so existing teos-vhost cross-site menu items
  // continue to appear.
  $choices = [];
  try {
    $choices = \bbsengine6\menu\buildchoices($choices);
  } catch (\Throwable $e) {
    router_log('bbsengine6\menu\buildchoices failed: ' . $e->getMessage(), 'warning');
  }

  // @since 2026-09-27 — render the directory listing through
  // bbsengine6/skin/tmpl/folder.tmpl (the canonical chrome'd
  // template that ships with the engine). Prior to this commit
  // the template name was 'browse.tmpl', which lived only in
  // the zoid6/teos docroot and forced a try/catch + inline-HTML
  // fallback. folder.tmpl now exists in bbsengine6's own
  // skin/tmpl/ tree (added 2026-09-17 alongside
  // php/folder.php::display()), so the fallback path is
  // obsolete and has been deleted. The data shape is now the
  // simple {title, items, uri, hidden, breadcrumbs, choices}
  // that folder.tmpl reads directly; the previous
  // $currentsig/$sigs projection (which existed only to feed
  // the currentsig-shaped browse.tmpl) has been removed.
  \bbsengine6\displaypage([
    'title' => $title,
    'items' => $items,
    'uri' => $uri,
    'hidden' => $hidden,
    'breadcrumbs' => $breadcrumbs,
    'choices' => $choices,
  ], 'folder.tmpl');
  return '';
}

function router(string $uri): ?string
{
  router_log('routing: ' . var_export($uri, true));

  foreach (router_gethandlers() as $name => $entry) {
    $fn      = is_array($entry) ? $entry['fn']      : $entry;
    $pattern = is_array($entry) ? ($entry['pattern'] ?? null) : null;

    if ($pattern !== null) {
      $matched = @preg_match($pattern, $uri);
      if ($matched === false) {
        // malformed pattern in the registry -- log and fall
        // through to invoking the handler rather than silently
        // swallowing the URI.
        router_log("handler $name has invalid pattern; ignoring",
                   'warning');
      } elseif ($matched === 0) {
        router_log("handler $name skipped (pattern miss)");
        continue;
      }
    }

    $result = $fn($uri);
    router_log('handler ' . $name . ' returned ' . var_export($result, true));
    if ($result === ROUTER_NEXT) continue;
    // ROUTER_RENDERED: handler rendered via displaypage() and
    // the body is already on stdout. Emit nothing more and
    // return '' so the HTTP entry-point's `echo $router_result`
    // is a no-op.
    if ($result === ROUTER_RENDERED) return '';
    if ($result === null || $result === false) continue;
    return $result;
  }

  return router_handleError($uri);
}

function route(string $uri): ?string
{
  return router($uri);
}

// === HTTP entry point ===
if (php_sapi_name() !== 'cli') {
  // include_path: portable absolute paths that resolve on both
  // the zoidtechnologies.com and www.bbsengine.org vhosts (both
  // ship php/markdown.php via php-deploy-prod and vendor/erusev
  // parsedown libs via parsedown-deploy-prod). The prior block
  // added per-vhost teos-tree paths that only resolve on the
  // .com vhost; drop them so the .org vhost can bootstrap the
  // same library set.
  set_include_path(get_include_path()
    . PATH_SEPARATOR . "/srv/www/bbsengine6/php"
    . PATH_SEPARATOR . "/srv/www/markdown/");


  $requesturi = $_SERVER['REQUEST_URI'] ?? '';
  if (preg_match('#^/handbook/(\d+)/(.*)$#', $requesturi, $m)) {
    if (!isset($_GET['uri']) && !isset($_GET['path'])) {
      $_GET['uri'] = $m[2];
    }
  } elseif (preg_match('#^/handbook/(\d+)/?$#', $requesturi, $m)) {
    if (!isset($_GET['uri']) && !isset($_GET['path'])) {
      $_GET['uri'] = '';
    }
  }

///  if (!defined('TEOSURL')) define('TEOSURL', '/teos/');
///  if (!defined('TEOSDIR')) define('TEOSDIR', '/srv/www/vhosts/zoidtechnologies.com/html/teos/');


  $path = $_GET['path'] ?? $_GET['uri'] ?? '';
  // @since 2026-09-29 — the previous version stripped a trailing
  // '.md' from the URI before passing it to the dispatch loop.
  // That kept the existing chrome-rendered handlers (markdown,
  // blurb) simple but silently killed the raw text/plain .md
  // dispatch contract: a /<uri>.md URL would be coerced to
  // /<uri>, the .md handler would never fire, and the user
  // got the rendered blurb page instead of the raw source. The
  // strip is removed; handlers that don't care about extensions
  // must pattern-gate or strip them themselves. See
  // router_gethandlers() and router_handleMarkdown /
  // router_handleRawMarkdown for the new contract.
  //
  // (Legacy note, kept for git-blame continuity: 2026-09-07 — the
  // previous version gated router() on `!empty($path)`, which
  // silently 200'd with an empty body for bare-version URLs.
  // Always call router() -- an empty $path triggers handleIndex
  // which renders TEOSDIR/index.md when present.)

  router_log("router.450: path=$path");
  try {
    $router_result = router($path);
    if ($router_result === null || $router_result === false) {
      http_response_code(500);
      echo 'Router Error (null)';
    } else {
      echo $router_result;
    }
  } catch (\Throwable $e) {
    // @since 2026-09-17 — leading-backslash namespace lookup;
    // see the comment at router_handleFolder for the rationale.
    // Also qualify the catch type with a leading backslash so
    // the catch resolves the global \Throwable instead of the
    // non-existent `bbsengine6\router\Throwable`.
    \bbsengine6\util\echo_traceback("router.http.100:".$e->getMessage());
    http_response_code(500);
    echo 'Router Error';
  }
}
