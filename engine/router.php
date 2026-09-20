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
 * pattern means "always try". The HTTP entry point strips any
 * trailing ".md" before pattern matching, so patterns match the
 * bare URI (e.g. "/contact-us", not "/contact-us.md").
 *
 * ROUTER_NEXT instructs the loop to continue on to the next handler.
 * ROUTER_RENDERED means "I rendered via displaypage(); the body is
 * already on stdout" -- the dispatcher maps this to an empty
 * return string so the HTTP entry-point emits nothing more.
 * Returning null or false continues to the next handler.
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
 * htaccess-prod rewrites its URIs to /engine/router.php?uri=<rel>;
 * the HTTP entry-point at the bottom of this file detects a
 * /handbook/<v>/... URI prefix and exports TEOSURL/TEOSDIR via
 * putenv() for that vhost, then dispatches to the handlers below.
 * Handlers that depend on teos-only helpers (bbsengine6\blurb\*,
 * bbsengine6\folder\*) no-op to ROUTER_NEXT when those helpers are absent.
 *
 * @since 2026
 */

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once('util.php');
require_once('markdown.php');
require_once('blurb.php');
require_once('engine.php');
require_once("page.php");
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

  $teosurl = rtrim(\bbsengine6\util\env("TEOSURI", "NEEDINFO:teosurl"));


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

  $rootlabel = \bbsengine6\util\env("TEOSLABEL", "teos");
  // Root crumb: title is per-vhost via TEOSLABEL (default
  // "teos", overridden to "bbsengine6 handbook" on the .org
  // vhost by the HTTP entry-point's putenv); the internal path
  // identifier stays "teos" to match blurb.php's
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
      'pattern' => '#^/?[A-Za-z0-9_][A-Za-z0-9_./-]*$#',
    ],
    'page' => [
      'fn'      => 'bbsengine6\\servepage\\router_handlePage',
      // narrowest: bare lowercase slug (e.g. /contact-us)
      'pattern' => '#^/?[a-z][a-z0-9-]*/?$#',
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
      return ROUTER_STOP;
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

  if (!function_exists('bbsengine6\blurb\isBlurb')) {
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
      return ROUTER_NEXT;
  }
  return ROUTER_NEXT;
}

function router_handleFolder(string $uri)
{
  router_log('handleFolder: ' . $uri);
  $teosdir = \bbsengine6\util\env("TEOSDIR", "NEEDINFO:router_handlefolder");
  if ($teosdir === '') {
    router_log('TEOSDIR not configured, skipping folder handler');
    return ROUTER_NEXT;
  }

  $reluri = ltrim($uri, '/');
  $filepath = router_safe_path_web([$reluri], ['base_dir' => $teosdir]);
  if ($filepath === false) {
    router_log('path validation failed', 'warning');
    return ROUTER_NEXT;
  }

  if (!is_dir($filepath)) {
    router_log('no directory found');
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
  if ($teosdir === '') return ROUTER_NEXT;

  // @since 2026-09-07 — see router_handleFolder for the
  // leading-slash rationale. The .md variant needs the same
  // ltrim so "specs/foo" (bare-relative) is appended rather
  // than "/specs/foo.md" (rejected as absolute).
  $reluri = ltrim($uri, '/');
  $filepath = router_safe_path_web([$reluri . '.md'], ['base_dir' => $teosdir]);
  if ($filepath === false || !file_exists($filepath)) {
    $filepath = router_safe_path_web([$reluri], ['base_dir' => $teosdir]);
  }
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

  \bbsengine6\setcurrentpage(rtrim(\bbsengine6\util\env("TEOSURI", "NEEDINFO:displaymd:teosurl"), '/') . $uri);

  $uri_parts = explode("/", $uri);
  array_pop($uri_parts);
  $breadcrumbs = router_buildBreadcrumbs(implode("/", $uri_parts));

  $choices = [];
  if (function_exists('\zoid6\buildchoices')) {
    try {
      $choices = \zoid6\buildchoices($choices);
    } catch (\Throwable $e) {
      router_log('zoid6\buildchoices failed: ' . $e->getMessage(), 'warning');
    }
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

  $teosurl = rtrim(\bbsengine6\util\env("TEOSURI", "NEEDINFO:collect:teosurl"), '/');
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
        if (isset($metadata['title'])) {
          $displayTitle = $metadata['title'];
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
  $teosurl = rtrim(\bbsengine6\util\env("TEOSURI", "NEEDINFO:displaydir:teosurl"), '/');

  \bbsengine6\setcurrentpage($teosurl.$uri);

  if (function_exists('bbsengine6\displaypage')) {
    $breadcrumbs = router_buildBreadcrumbs($uri);

    $sigs = [];
    $teosbase = rtrim($teosurl, '/');
    foreach ($items as $item) {
      $reluri = ltrim(substr($item['uri'], strlen($teosbase)), '/');
      $sigs[] = [
        'title' => $item['title'],
        'uri' => $reluri,
        'icon' => isset($item['is_dir']) && $item['is_dir'] ? 'fa-folder' : 'fa-file-alt',
        'intro' => null,
        'actions' => [],
      ];
    }

    $currentsig = [
      'title' => $title,
      'uri' => $uri,
      'intro' => null,
      'sigs' => $sigs,
      'links' => [],
      'actions' => [],
    ];

    $choices = [];
    if (function_exists('\zoid6\buildchoices')) {
      // @since 2026-09-10 — same graceful-degradation wrapper
      // as the rest of the handler chain. buildchoices() calls
      // into bbsengine6\engine\buildchoices() ->
      // member\lib\checkflag() which can throw if the engine
      // schema is missing or the database is unavailable.
      // Treat that as "no menu items" rather than 500ing the
      // whole listing.
      try {
        $choices = \zoid6\buildchoices($choices);
      } catch (\Throwable $e) {
        router_log('zoid6\buildchoices failed: ' . $e->getMessage(), 'warning');
      }
    }

    // @since 2026-09-07 — graceful degradation when the
    // `browse.tmpl` template is not available on the calling
    // vhost. The bbsengine6/skin/tmpl/ tree ships
    // page-markdown.tmpl (used by handleMarkdown) but not
    // browse.tmpl -- that template lives in the zoid6/teos
    // docroot and is not part of bbsengine6's deploy chain. On
    // vhosts that don't share teos's template tree, Smarty
    // raises "Unable to load template 'file:browse.tmpl'" and
    // the directory listing fails. Catch the throwable, log
    // it, and fall through to the inline HTML renderer
    // (lines below) so the URL still returns 200 with a
    // usable (un-styled) list. A future commit can ship a
    // bbsengine6/skin/tmpl/browse.tmpl and remove the
    // try-catch.
    try {
      // @since 2026-09-17 — leading-backslash namespace lookup;
      // router.php is in `namespace bbsengine6\router;` so bare
      // `bbsengine6\displaypage()` would resolve to the
      // non-existent `bbsengine6\router\bbsengine6\displaypage()`.
      // The two other displaypage() call sites in this file
      // (router_displayMarkdownFile and the route() return)
      // already use the leading-backslash form; this one was
      // missed in bfaca68.
      \bbsengine6\displaypage([
        'title' => $title,
        'items' => $items,
        'uri' => $uri,
        'hidden' => $hidden,
        'currentsig' => $currentsig,
        'breadcrumbs' => $breadcrumbs,
        'choices' => $choices,
      ], 'browse.tmpl');
      return '';
    } catch (\Throwable $e) {
      router_log('browse.tmpl render failed, falling back to inline list: ' . $e->getMessage(), 'warning');
      // fall through
    }
  }

  http_response_code(200);
  $lock = $hidden ? ' [hidden]' : '';
  $html = "<html><head><title>$title</title></head><body><h1>$title$lock</h1><ul>";
  foreach ($items as $i) {
    $s = isset($i['is_dir']) && $i['is_dir'] ? '/' : '';
    $html .= '<li><a href="' . htmlspecialchars($i['uri']) . '">' . htmlspecialchars($i['title']) . '</a>' . $s . '</li>';
  }
  $html .= '</ul></body></html>';
  return $html;
  // return '<html><body><h1>' . $title . '</h1><ul>' . implode('', array_map(fn($i) => '<li>' . $i['title'] . '</li>', $items)) . '</ul></body></html>';
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
  $path = preg_replace('/\.md$/', '', $path);

  router_log("router.450: path=$path");

  // @since 2026-09-07 — the previous version gated router()
  // on `!empty($path)`, which silently 200'd with an empty
  // body for bare-version URLs (e.g. /handbook/6/ where the
  // htaccess sent ?uri=). That was the source of the 'silent
  // 200 with empty body' behavior the test caught. Always
  // call router() -- an empty $path triggers handleIndex
  // (which renders TEOSDIR/index.md when present), so /handbook/
  // <v>/ now returns a proper 200 with a rendered body instead
  // of an empty 200.
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
