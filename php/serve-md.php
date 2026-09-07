<?php
/**
 * serve-md.php - Stream a .md file as text/plain.
 *
 * Library + HTTP entry point. Library shape: any consumer that
 * wants raw markdown over HTTP at the script-level can
 * require_once this file and call \bbsengine6\serveRawMarkdown()
 * directly. HTTP-entry-point shape: the htaccess rule
 * `^(.+)\.md$ -> /engine/serve-md.php?prefix=<dir>&path=<rel>`
 * rewrites raw .md URLs here, and the bottom-of-file global-
 * namespace block reads the request, looks up the file under
 * the derived basedir, and streams its body.
 *
 * Path-traversal guard: realpath comparison must show the
 * resolved file lives inside realpath($basedir). 404 on any
 * violation, on missing file, on non-md extension, or on
 * directories.
 *
 * @since 2026-09-07 -- added HTTP entry point so rewritten
 * .md URLs actually serve content rather than 404 / no-op.
 */

namespace bbsengine6 {

/**
 * Stream a .md file under $basedir as text/plain markdown.
 *
 * @param string $basedir Absolute base directory (e.g.
 *                        /srv/www/vhosts/www.bbsengine.org/html/handbook/6/).
 * @param string $relpath  Path relative to $basedir; must end in .md
 *                        and resolve to a regular file inside $basedir.
 * @return bool true on success (headers + body sent), false on
 *              validation failure (caller emits the 404).
 */
function serveRawMarkdown(string $basedir, string $relpath): bool
{
  $realbasedir = realpath($basedir);
  if ($realbasedir === false) {
    return false;
  }
  $realbasedir = rtrim($realbasedir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR;

  $candidate = $realbasedir . $relpath;
  $realfile  = realpath($candidate);

  if ($realfile === false
      || strpos($realfile, $realbasedir) !== 0
      || !is_file($realfile)
      || pathinfo($realfile, PATHINFO_EXTENSION) !== 'md') {
    return false;
  }

  header('Content-Type: text/plain; charset=utf-8');
  readfile($realfile);
  return true;
}

}

namespace {
  if (php_sapi_name() !== 'cli') {
    $path = $_GET['path'] ?? '';
    $prefix = $_GET['prefix'] ?? '';
    $docroot = $_SERVER['DOCUMENT_ROOT'] ?? '';
    if ($path === '' || $docroot === '') {
      http_response_code(404);
      header('Content-Type: text/plain; charset=utf-8');
      echo 'File not found';
      return;
    }
    $basedir = rtrim($docroot, DIRECTORY_SEPARATOR)
             . DIRECTORY_SEPARATOR
             . trim($prefix, "/\\")
             . DIRECTORY_SEPARATOR;
    if (!bbsengine6\serveRawMarkdown($basedir, $path)) {
      http_response_code(404);
      header('Content-Type: text/plain; charset=utf-8');
      echo 'File not found';
    }
  }
}
