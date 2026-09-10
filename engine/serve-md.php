<?php
/**
 * serve-md.php - Serve .md files as plain text
 *
 * Contract:
 *   htaccess-prod (see www/org/htaccess-prod:55) rewrites
 *     /handbook/<v>/<uri>.md  ->  /serve-md.php?prefix=handbook/<v>&path=<uri>.md
 *   and /serve-md.php on the docroot is a symlink to this file
 *   (created by `make -C www/org prod-symlinks`).
 *
 *   This handler reads ?prefix and ?path, resolves them to an
 *   absolute filesystem path under the handbook home (via
 *   \bbsengine6\util\handbook_resolve()), and readfile()'s the
 *   result with Content-Type: text/plain.
 *
 *   The handbook home is the single source of truth in
 *   \bbsengine6\util\handbook_home(); see php/util.php.
 *
 * @since 2026-09-09 — replaced the previous hardcoded TEOSDIR
 *   fallback (which pointed at the wrong docroot) with a call
 *   to \bbsengine6\util\handbook_resolve(). The rewrite
 *   contract (?prefix=...&path=...) was unchanged.
 */

if (php_sapi_name() === 'cli' && basename($_SERVER['PHP_SELF']) === 'serve-md.php') {
    echo "serve-md.php - serves .md files as text/plain\n";
    exit(0);
}

require_once('/srv/www/bbsengine6/php/util.php');

$prefix = $_GET['prefix'] ?? '';
$path = $_GET['path'] ?? '';

$filepath = \bbsengine6\util\handbook_resolve($prefix, $path);
if ($filepath === false) {
    http_response_code(404);
    echo "File not found";
    exit;
}

header('Content-Type: text/plain; charset=utf-8');
readfile($filepath);
