<?php
/**
 * router.php - Handler registry for routing requests
 * 
 * Implements a handler registry pattern that checks handlers in order.
 * Each handler can return ROUTER_NEXT to pass to the next handler.
 * 
 * Handler order: blurb → folder → markdown → error
 * 
 * @since 2026
 */

if (!defined("ROUTER_NEXT")) {
    define("ROUTER_NEXT", "ROUTER_NEXT");
}
if (!defined("ROUTER_STOP")) {
    define("ROUTER_STOP", "ROUTER_STOP");
}
if (!defined("TEOSURL")) {
    define("TEOSURL", "");
}

/**
 * @since 2026
 */
function router_log(string $message, string $level = "info"): void
{
  $prefix = "router." . strtoupper($level);
  if (function_exists('\bbsengine6\util\logentry')) {
    \bbsengine6\util\logentry("$prefix: $message");
  }
}

/**
 * Get the list of registered handlers
 * @return array Array of handler callables
 */
function router_gethandlers(): array
{
  return [
    'blurb'    => 'router_handleBlurb',
    'folder'   => 'router_handleFolder',
    'markdown' => 'router_handleMarkdown',
    'error'    => 'router_handleError',
  ];
}

/**
 * Handle blurb requests
 * 
 * @param string $uri The request URI
 * @return string|bool Result or ROUTER_NEXT
 */
function router_handleBlurb(string $uri)
{
  router_log("router.001: handleBlurb called with uri=" . var_export($uri, true));

  if (function_exists('\bbsengine6\blurb\isBlurb') && \bbsengine6\blurb\isBlurb($uri))
  {
    router_log("router.010: blurb found for uri=" . var_export($uri, true));
    if (function_exists('\bbsengine6\blurb\display')) {
      return \bbsengine6\blurb\display($uri, null);
    }
    return ROUTER_NEXT;
  }

  router_log("router.011: no blurb found, passing to next handler");
  return ROUTER_NEXT;
}

/**
 * Handle folder/directory requests
 * 
 * @param string $uri The request URI
 * @return string|bool Result or ROUTER_NEXT
 */
function router_handleFolder(string $uri)
{
  router_log("router.012: handleFolder called with uri=" . var_export($uri, true));

  $teospath = defined('TEOSFILEPATH') ? TEOSFILEPATH : '/srv/www/zoid6/teos/';
  $filepath = \bbsengine6\util\safe_path_web([$teospath, $uri], ['base_dir' => $teospath]);

  if ($filepath === false)
  {
    router_log("router.013: path validation failed for uri=" . var_export($uri, true), "warning");
    return ROUTER_NEXT;
  }

  if (is_dir($filepath))
  {
    $isVisible = true;
    $isSysop = false;
    if (function_exists('\bbsengine6\folder\isFolderVisible')) {
      $isVisible = \bbsengine6\folder\isFolderVisible($uri);
      $isSysop = function_exists('\bbsengine6\folder\isSysop') && \bbsengine6\folder\isSysop();
      if (!$isVisible && !$isSysop) {
        router_log("router.014: folder not visible, passing to next handler");
        return ROUTER_NEXT;
      }
    }

    $hidden = isset($isVisible) && !$isVisible && $isSysop;
    router_log("router.015: directory found at filepath=" . var_export($filepath, true));
    return router_displayDirectoryListing($filepath, $uri, $hidden);
  }

  router_log("router.016: no directory found, passing to next handler");
  return ROUTER_NEXT;
}

/**
 * Handle markdown file requests
 * 
 * @param string $uri The request URI
 * @return string|bool Result or ROUTER_NEXT
 */
function router_handleMarkdown(string $uri)
{
  router_log("router.017: handleMarkdown called with uri=" . var_export($uri, true));

  $teospath = defined('TEOSFILEPATH') ? TEOSFILEPATH : '/srv/www/zoid6/teos/';
  
  // Try with .md extension
  $filepath = \bbsengine6\util\safe_path_web([$teospath, $uri . ".md"], ['base_dir' => $teospath]);
  if ($filepath === false || !file_exists($filepath))
  {
    // Try as-is (in case already has .md)
    $filepath = \bbsengine6\util\safe_path_web([$teospath, $uri], ['base_dir' => $teospath]);
  }

  if ($filepath !== false && file_exists($filepath) && is_file($filepath))
  {
    router_log("router.019: markdown file found at filepath=" . var_export($filepath, true));
    return router_displayMarkdownFile($filepath, $uri);
  }

  router_log("router.020: no markdown file found, passing to error handler");
  return ROUTER_NEXT;
}

/**
 * Handle errors - called when no other handler matches
 * 
 * @param string $uri The request URI
 * @return string|bool Result
 */
function router_handleError(string $uri)
{
  router_log("router.100: no handler found for uri=" . var_export($uri, true), "error");
  if (function_exists('\bbsengine6\page\error')) {
    return \bbsengine6\page\error("Page not found: " . htmlspecialchars($uri), 404);
  }
  return null;
}

/**
 * Display a markdown file
 * 
 * @param string $filepath Full filesystem path
 * @param string $uri The request URI
 * @return string|null Rendered HTML or null on error
 */
function router_displayMarkdownFile(string $filepath, string $uri): ?string
{
  if (!file_exists($filepath)) {
    return null;
  }
  
  $content = file_get_contents($filepath);

  $metadata = [];
  if (preg_match('/^---\s*\n(.*?)\n---/s', $content, $matches))
  {
    $metadata = router_parseYamlFrontmatter($matches[1]);
    $content = preg_replace('/^---\s*\n.*?\n---\s*\n/s', '', $content);
  }

  if (class_exists('\Markdown')) {
    $html = \Markdown::defaultTransform($content);
  } else {
    $html = $content;
  }

  $title = isset($metadata['title']) ? htmlspecialchars($metadata['title']) : basename($filepath, '.md');
  $date = isset($metadata['date']) ? htmlspecialchars($metadata['date']) : '';

  if (function_exists('\bbsengine6\setcurrentpage')) {
    \bbsengine6\setcurrentpage(TEOSURL . $uri);
  }

  $data = [];
  $data["content"] = $content;
  $data["title"] = $title;
  $data["date"] = $date;

  if (function_exists('\bbsengine6\displaypage')) {
    return \bbsengine6\displaypage($data, "page-markdown.tmpl");
  }
  
  return $html;
}

/**
 * Display a directory listing
 * 
 * @param string $dirpath Full filesystem path
 * @param string $uri The request URI
 * @param bool $hidden Whether folder is hidden (for sysop display)
 * @return string|null Rendered HTML or null on error
 */
function router_displayDirectoryListing(string $dirpath, string $uri, bool $hidden = false): ?string
{
  $safeDir = \bbsengine6\util\safe_path_web([$dirpath], ['base_dir' => dirname($dirpath)]);
  if ($safeDir === false)
  {
    router_log("router.016: directory path validation failed for dirpath=" . var_export($dirpath, true), "warning");
    return null;
  }
  
  $files = glob($safeDir . "/*.md");
  sort($files);

  $title = htmlspecialchars(basename($uri));
  $items = [];

  foreach ($files as $filepath)
  {
    $filename = basename($filepath, '.md');
    $fileuri = $uri . "/" . $filename;

    $metadata = [];
    $displayTitle = $filename;

    $filecontent = file_get_contents($filepath);
    if (preg_match('/^---\s*\n(.*?)\n---/s', $filecontent, $matches))
    {
      $metadata = router_parseYamlFrontmatter($matches[1]);
      if (isset($metadata['title']))
      {
        $displayTitle = htmlspecialchars($metadata['title']);
      }
    }

    $items[] = [
      'title' => $displayTitle,
      'uri' => TEOSURL . $fileuri,
      'filename' => $filename,
    ];
  }

  if (function_exists('\bbsengine6\setcurrentpage')) {
    \bbsengine6\setcurrentpage(TEOSURL . $uri);
  }

  $data = [];
  $data["title"] = $title;
  $data["items"] = $items;
  $data["uri"] = $uri;
  $data["hidden"] = $hidden;

  if (function_exists('\bbsengine6\displaypage')) {
    return \bbsengine6\displaypage($data, "directory-listing.tmpl");
  }

  $lockIcon = $hidden ? " 🔒" : "";
  return "<html><head><title>$title</title></head><body><h1>$title$lockIcon</h1><ul>" .
    implode("", array_map(fn($i) => "<li><a href=\"{$i['uri']}\">{$i['title']}</a></li>", $items)) .
    "</ul></body></html>";
}

/**
 * Parse YAML frontmatter from content
 * 
 * @param string $yaml The YAML content
 * @return array Parsed metadata
 */
function router_parseYamlFrontmatter(string $yaml): array
{
  $metadata = [];
  $lines = explode("\n", $yaml);
  foreach ($lines as $line)
  {
    if (preg_match('/^(\w+):\s*(.*)$/', $line, $matches))
    {
      $key = trim($matches[1]);
      $value = trim($matches[2]);
      $metadata[$key] = $value;
    }
  }
  return $metadata;
}

/**
 * Main router entry point
 * 
 * @param string $uri The request URI
 * @return string|bool Result
 */
function router(string $uri)
{
  router_log("router.021: routing uri=" . var_export($uri, true));

  $handlers = router_gethandlers();

  foreach ($handlers as $name => $handler)
  {
    router_log("router.002: trying handler $name for uri=" . var_export($uri, true));
    $result = $handler($uri);

    if ($result !== ROUTER_NEXT)
    {
      router_log("router.003: handler $name handled the request");
      return $result;
    }

    router_log("router.004: handler $name returned ROUTER_NEXT, trying next");
  }

  router_log("router.100: no handler found for uri=" . var_export($uri, true), "error");
  return router_handleError($uri);
}

/**
 * Alias for router() - backward compatibility
 * 
 * @param string $uri The request URI
 * @return string|bool Result
 */
function route(string $uri)
{
  return router($uri);
}
