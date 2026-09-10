<?php
/**
 * router.php - Handler registry for routing requests.
 *
 * Handler order: index -> blurb -> folder -> error
 *
 * ROUTER_NEXT instructs the loop to continue on to the next handler.
 * Returning ROUTER_STOP will short-circuit the chain.
 * Returning null, false, or an empty string will also short-circuit the chain,
 * but handlers that render via displaypage() must not pass through its null
 * return value, as that would cause the next handler to render again.
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

if (!defined('ROUTER_NEXT')) { define('ROUTER_NEXT', 'ROUTER_NEXT'); }
if (!defined('ROUTER_STOP')) { define('ROUTER_STOP', 'ROUTER_STOP'); }

function router_log(string $message, string $level = "info"): void
{
  static $func = null;
  if ($func === null) {
    $func = function_exists('\bbsengine6\util\logentry') ? '\bbsengine6\util\logentry' : false;
  }
  if ($func) {
    $func('router.' . strtoupper($level) . ': ' . $message);
  }
}

function router_get_teosurl(): string
{
  // @since 2026-09-09 — thin wrapper kept for backward compat.
  // Prefer \bbsengine6\util\teos_url() in new code; this function
  // delegates to it.
  return \bbsengine6\util\teos_url();
}

function router_get_teosdir(): string
{
  // @since 2026-09-09 — thin wrapper kept for backward compat.
  // Prefer \bbsengine6\util\teos_dir() in new code; this function
  // delegates to it.
  return \bbsengine6\util\teos_dir();
}

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
  if (!function_exists('bbsengine6\util\safe_path_web')) {
    return false;
  }
  return bbsengine6\util\safe_path_web($components, $opts);
}

function router_buildBreadcrumbs(string $uri): array
{
  $segments = array_values(array_filter(explode("/", trim($uri, "/"))));
  if (empty($segments)) {
    return [];
  }

  $teosurl = rtrim(router_get_teosurl(), '/');

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

  // Prepend "teos" crumb
  array_unshift($autoCrumbs, [
    'title' => 'teos',
    'path' => 'teos',
    'uri' => $teosurl . '/',
  ]);

  return $autoCrumbs;
}

function router_gethandlers(): array
{
  return [
    'index'    => 'router_handleIndex',
    'blurb'    => 'router_handleBlurb',
    'folder'   => 'router_handleFolder',
    'markdown' => 'router_handleMarkdown',
    'error'    => 'router_handleError',
  ];
}

function router_handleIndex(string $uri)
{
  router_log('handleIndex called with uri=' . var_export($uri, true));

  if ($uri !== '/' && $uri !== '') {
    router_log('not root path');
    return ROUTER_NEXT;
  }

  $teosdir = router_get_teosdir();
  $indexfile = $teosdir . 'index.php';
  if (file_exists($indexfile)) {
    try {
      include($indexfile);
      return ROUTER_STOP;
    } catch (Throwable $e) {
      router_log('index include failed: ' . $e->getMessage());
      return ROUTER_NEXT;
    }
  }

  // @since 2026-09-07 — fall back to TEOSDIR/index.md and
  // delegate to the markdown handler when the vhost's TEOSDIR
  // ships a markdown index instead of a PHP one. The teos
  // vhost ships index.php; the handbook vhost (bbsengine.org)
  // ships handbook/<v>/index.md, so without this fallback
  // /handbook/<v>/ is unrenderable through the router.
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

  if (bbsengine6\blurb\isBlurb($uri)) {
    if (function_exists('bbsengine6\blurb\display')) {
      bbsengine6\blurb\display($uri, null);
      return '';
    }
    return ROUTER_NEXT;
  }
  return ROUTER_NEXT;
}

function router_handleFolder(string $uri)
{
  router_log('handleFolder: ' . $uri);
  $teospath = router_get_teosdir();
  if ($teospath === '') {
    router_log('TEOSDIR not configured, skipping folder handler');
    return ROUTER_NEXT;
  }

  // @since 2026-09-07 — strip any leading '/' before handing
  // the path to router_safe_path_web (which forwards to
  // bbsengine6\util\safe_path_web). safe_path_web treats
  // leading slashes as absolute-path attempts and rejects
  // them (see bbsengine6\util\safe_path_web lines 510-514),
  // but the router's URI shape is "leading-slash relative"
  // (e.g. "/6/specs/") as routed by the bbsengine.org
  // htaccess-prod (RewriteRule ^handbook/(\d+)/?(.*)$ ->
  // /engine/router.php?uri=$2 plus the leading '/' that
  // may be present on bare /handbook/6/), not "absolute" --
  // the absolute-root semantics are anchored to TEOSDIR,
  // not the OS root. ltrim converts the URI to the
  // bare-relative shape the rest of the function (and
  // safe_path_web) expect. The containment check inside
  // safe_path_web (str_starts_with($resolved, $base_real))
  // is the real security guard, so this ltrim does not
  // weaken path-traversal protection.
  $reluri = ltrim($uri, '/');
  $filepath = router_safe_path_web([$reluri], ['base_dir' => $teospath]);
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
  if (function_exists('bbsengine6\folder\isFolderVisible')) {
    $isVisible = bbsengine6\folder\isFolderVisible($uri);
    $isSysop = function_exists('bbsengine6\folder\isSysop') && bbsengine6\folder\isSysop();
    if (!$isVisible && !$isSysop) {
      return ROUTER_NEXT;
    }
  }

  return router_displayDirectoryListing($filepath, $uri, (!$isVisible && $isSysop));
}

function router_handleMarkdown(string $uri)
{
  router_log('handleMarkdown: ' . $uri);
  $teospath = router_get_teosdir();
  if ($teospath === '') return ROUTER_NEXT;

  // @since 2026-09-07 — see router_handleFolder for the
  // leading-slash rationale. The .md variant needs the same
  // ltrim so "specs/foo" (bare-relative) is appended rather
  // than "/specs/foo.md" (rejected as absolute).
  $reluri = ltrim($uri, '/');
  $filepath = router_safe_path_web([$reluri . '.md'], ['base_dir' => $teospath]);
  if ($filepath === false || !file_exists($filepath)) {
    $filepath = router_safe_path_web([$reluri], ['base_dir' => $teospath]);
  }
  if ($filepath !== false && file_exists($filepath) && is_file($filepath)) {
    return router_displayMarkdownFile($filepath, $uri);
  }
  return ROUTER_NEXT;
}

function router_handleError(string $uri)
{
  $msg = 'Page not found: ' . htmlspecialchars($uri);
  router_log($msg, 'error');

  if (function_exists('bbsengine6\page\error')) {
    $r = bbsengine6\page\error($msg, 404);
    if ($r !== null && $r !== false) {
      return $r;
    }
  }

  http_response_code(404);
  return '<html><head><title>404</title></head><body><h1>Page Not Found</h1><p>' . $msg . '</p></body></html>';
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

  if (function_exists('bbsengine6\setcurrentpage')) {
    bbsengine6\setcurrentpage(router_get_teosurl() . $uri);
  }

  $uri_parts = explode("/", $uri);
  array_pop($uri_parts);
  $breadcrumbs = router_buildBreadcrumbs(implode("/", $uri_parts));

  $choices = [];
  if (function_exists('\zoid6\buildchoices')) {
    $choices = \zoid6\buildchoices($choices);
  }

  $data = [
    'title' => $doc['title'],
    'date' => $doc['date'],
    'content' => $doc['html'],
    'breadcrumbs' => $breadcrumbs,
    'choices' => $choices,
  ];

  if (function_exists('bbsengine6\displaypage')) {
    bbsengine6\displaypage($data, 'page-markdown.tmpl', false);
    return '';
  }

  $date_html = $doc['date'] ? "<p class=date>{$doc['date']}</p>" : '';
  return "<html><head><title>{$doc['title']}</title></head><body>$date_html{$doc['html']}</body></html>";
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

  $teosurl = router_get_teosurl();
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
        if (!function_exists('\bbsengine6\markdown\splitFrontmatter')) {
          require_once("php/markdown.php");
        }
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
  $teosurl = router_get_teosurl();

  if (function_exists('bbsengine6\setcurrentpage')) {
    bbsengine6\setcurrentpage($teosurl . $uri);
  }

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
      $choices = \zoid6\buildchoices($choices);
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
      bbsengine6\displaypage([
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

  foreach (router_gethandlers() as $name => $handler) {
    $result = $handler($uri);
    router_log('handler ' . $name . ' returned ' . var_export($result, true));
    if ($result === ROUTER_NEXT) continue;
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

  // Detect the /handbook/<v>/... URI prefix and set TEOSURL/
  // TEOSDIR for that request so handlers below read from the
  // matching handbook tree. Same shape as teos: htaccess rewrites
  // the URI, this entry-point adapts the working dir, the
  // handlers do not need to know which vhost they're serving.
  // Env wins over constants --
  // \bbsengine6\util\teos_url()/teos_dir() (php/util.php)
  // prefer getenv() over the define() below, so
  // a handbook request that supplies its own env vars here
  // overrides the teos fallback. The define()s stay for the
  // teos case where neither env nor a prefix-derived override
  // is present.
  //
  // @since 2026-09-09 — $handbookhome now reads from
  // \bbsengine6\util\handbook_home() (the single source of
  // truth for the canonical install path; same constant used
  // by engine/serve-md.php). The handbook home can be
  // overridden via the BBSENGINE6_HANDBOOK_HOME env var or
  // constant (see php/util.php).
  //
  // @since 2026-09-09 — load php/util.php BEFORE calling
  // handbook_home(). The 2026-09-09 refactor that introduced
  // this call moved the function-call but left the
  // require_once at line ~601 below; the result was a
  // "Call to undefined function" fatal on every no-.md
  // URL (the .md raw path through engine/serve-md.php was
  // unaffected, which masked the regression behind a
  // partially-working handbook). The minimal fix is to
  // require util.php here so handbook_home() is in scope
  // for the prefix-detection block. The other requires
  // (markdown.php, blurb.php, engine.php, config.php) stay
  // below because they are not needed for handbook_home().
  require_once('/srv/www/bbsengine6/php/util.php');

  $requesturi = $_SERVER['REQUEST_URI'] ?? '';
  $handbookhome = \bbsengine6\util\handbook_home();
  if (preg_match('#^/handbook/(\d+)/(.*)$#', $requesturi, $m)) {
    putenv('TEOSDIR=' . $handbookhome . $m[1] . '/');
    putenv('TEOSURL=/handbook/' . $m[1] . '/');
    if (!isset($_GET['uri']) && !isset($_GET['path'])) {
      $_GET['uri'] = $m[2];
    }
  } elseif (preg_match('#^/handbook/(\d+)/?$#', $requesturi, $m)) {
    putenv('TEOSDIR=' . $handbookhome . $m[1] . '/');
    putenv('TEOSURL=/handbook/' . $m[1] . '/');
    if (!isset($_GET['uri']) && !isset($_GET['path'])) {
      $_GET['uri'] = '';
    }
  }

  if (!defined('TEOSURL')) define('TEOSURL', '/teos/');
  if (!defined('TEOSDIR')) define('TEOSDIR', '/srv/www/vhosts/zoidtechnologies.com/html/teos/');

  require_once('/srv/www/bbsengine6/php/util.php');
  require_once('/srv/www/bbsengine6/php/markdown.php');
  require_once('/srv/www/bbsengine6/php/blurb.php');
  require_once('/srv/www/bbsengine6/php/engine.php');
  require_once('config.php');

  $path = $_GET['path'] ?? $_GET['uri'] ?? '';
  $path = preg_replace('/\.md$/', '', $path);

  if (function_exists('bbsengine6\util\logentry')) {
    call_user_func('bbsengine6\util\logentry', "router.http: path=$path");
  }

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
    $router_result = \router($path);
    if ($router_result === null || $router_result === false) {
      http_response_code(500);
      echo 'Router Error (null)';
    } else {
      echo $router_result;
    }
  } catch (Throwable $e) {
    if (function_exists('bbsengine6\util\echo_traceback')) {
      call_user_func('bbsengine6\util\echo_traceback', 'router.error: ' . $e->getMessage());
    }
    http_response_code(500);
    echo 'Router Error';
  }
}
