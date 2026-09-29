<?php
/**
 * serve-md.php - Stream a .md file as text/plain.
 *
 * Library shape: any consumer that wants raw markdown over HTTP at
 * the script-level can require_once this file and call
 * \bbsengine6\serveRawMarkdown() directly with a basedir and a
 * relative path. The library is side-effect free: it defines the
 * function and nothing else.
 *
 * HTTP entry-point shape: the canonical handbook entry-point lives
 * at engine/serve-md.php (loaded by the handbook vhost's htaccess
 * rewrite). It calls \bbsengine6\util\handbook_resolve() to derive
 * the basedir from REQUEST_URI. The teos vhost's .md URLs go
 * through engine/router.php -> router_handleRawMarkdown, which
 * reads TEOSDIR via \bbsengine6\util\env() and passes it as the
 * basedir to \bbsengine6\serveRawMarkdown() here.
 *
 * Path-traversal guard: realpath comparison must show the resolved
 * file lives inside realpath($basedir). 404 on any violation, on
 * missing file, on non-md extension, or on directories.
 *
 * @since 2026-09-07 -- added HTTP entry point so rewritten .md URLs
 * actually serve content rather than 404 / no-op.
 * @since 2026-09-29 -- removed the namespace {} entry-point block;
 * the file is now library-only. The HTTP entry-point was duplicated
 * here, which made the file unsafe to require_once from any context
 * other than engine/serve-md.php itself (the namespace {} block
 * fired as a side effect of the require_once and aborted the request
 * with 404 'File not found' when $_GET['path'] was unset). The
 * canonical entry-point at engine/serve-md.php handles the handbook
 * vhost contract; the teos vhost uses engine/router.php ->
 * router_handleRawMarkdown with TEOSDIR via env().
 */

namespace bbsengine6 {

/**
 * Stream a .md file under $basedir as text/plain markdown.
 *
 * @param string $basedir Absolute base directory (e.g.
 *                        /srv/www/vhosts/www.bbsengine.org/html/handbook/6/
 *                        or \bbsengine6\util\env('TEOSDIR') for the
 *                        teos vhost).
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
