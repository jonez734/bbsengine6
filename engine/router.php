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
  return getenv('TEOSURL') ?: (defined('TEOSURL') ? TEOSURL : '');
}

function router_get_teosdir(): string
{
  return getenv('TEOSDIR') ?: (defined('TEOSDIR') ? TEOSDIR : '');
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

  $indexfile = router_get_teosdir() . 'index.php';
  if (!file_exists($indexfile)) {
    router_log('index.php not found', 'warning');
    return ROUTER_NEXT;
  }

  try {
    include($indexfile);
    return ROUTER_STOP;
  } catch (Throwable $e) {
    router_log('index include failed: ' . $e->getMessage());
    return ROUTER_NEXT;
  }
}

function router_handleBlurb(string $uri)
{
  router_log('handleBlurb: ' . $uri);

  if (function_exists('bbsengine6\blurb\isBlurb') && bbsengine6\blurb\isBlurb($uri)) {
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

  $filepath = bbsengine6\util\safe_path_web([$uri], ['base_dir' => $teospath]);
  if ($filepath === false) {
    router_log('path validation failed', 'warning');
    return ROUTER_NEXT;
  }

  if (!is_dir($filepath)) {
    router_log('no directory found');
    return ROUTER_NEXT;
  }

  // folder visibility check
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

  $filepath = bbsengine6\util\safe_path_web([$uri . '.md'], ['base_dir' => $teospath]);
  if ($filepath === false || !file_exists($filepath)) {
    $filepath = bbsengine6\util\safe_path_web([$uri], ['base_dir' => $teospath]);
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
  if (!function_exists('\bbsengine6\markdown\parseDocument')) {
    require_once __DIR__ . '/../php/markdown.php';
  }

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
          require_once __DIR__ . '/../php/markdown.php';
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
  set_include_path(get_include_path()
    . PATH_SEPARATOR . "/srv/www/vhosts/zoidtechnologies.com/html/teos"
    . PATH_SEPARATOR . "/srv/www/bbsengine6/php"
    . PATH_SEPARATOR . "/srv/www/markdown/"
    . PATH_SEPARATOR . "/srv/www/zoid6/php"
    . PATH_SEPARATOR . "/srv/www/zoid6/markdown");

  if (!defined('TEOSURL')) define('TEOSURL', '/teos/');
  if (!defined('TEOSDIR')) define('TEOSDIR', '/srv/www/vhosts/zoidtechnologies.com/html/teos/');

  @require_once('PEAR.php');
  @require_once('Log.php');
  @require_once('util.php');
  @require_once('blurb.php');
  @require_once('config.php');

  $path = $_GET['path'] ?? $_GET['uri'] ?? '';
  $path = preg_replace('/\.md$/', '', $path);

  if (function_exists('bbsengine6\util\logentry')) {
    call_user_func('bbsengine6\util\logentry', "router.http: path=$path");
  }

  if (!empty($path)) {
    try {
      $router_result = \router($path);
      if ($router_result === null || $router_result === false) {
        http_response_code(500);
        echo 'Router Error';
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
}
