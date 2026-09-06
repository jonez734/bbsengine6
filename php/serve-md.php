<?php
/**
 * serve-md.php - Stream a .md file as text/plain.
 *
 * Library, not an entry point: this file ships under
 * /srv/www/bbsengine6/php/ via the php-deploy chain, alongside
 * markdown.php, blurb.php, and the Form/* primitives. Handbook
 * (and any other consumer that wants raw markdown over HTTP)
 * requires_once it via the standard bootstrap-resolved include
 * and calls \bbsengine6\serveRawMarkdown() directly.
 *
 * Path-traversal guard: realpath comparison must show the
 * resolved file lives inside realpath($basedir). 404 on any
 * violation, on missing file, on non-md extension, or on
 * directories.
 *
 * No top-level execution. Calling this file directly via HTTP
 * would no-op (no script entry point), which is the intended
 * shape -- the handler decides whether to call the function,
 * not the request router.
 */

namespace bbsengine6 {

/**
 * Stream a .md file under $basedir as text/plain markdown.
 *
 * Used by handbook.php's `rawpath` branch: the .htaccess rule
 * for /handbook/<v>/<uri>.md rewrites to
 * /handbook.php?version=<v>&rawpath=<uri>.md, and the handler
 * calls this with $basedir = \config\HANDBOOKDIR . $version . "/".
 *
 * @param string $basedir Absolute base directory (e.g. \config\HANDBOOKDIR . "6/").
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
