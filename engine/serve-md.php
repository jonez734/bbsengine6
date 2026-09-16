<?php

/**
 * serve-md.php - Stream a .md file as text/plain.
 *
 * Shim to the canonical library at php/serve-md.php, which
 * exposes \bbsengine6\serveRawMarkdown($basedir, $relpath)
 * and its own HTTP entry-point. This shim exists so the
 * htaccess rewrite `^(.+)\.md$ -> /engine/serve-md.php` has
 * a stable target under /engine/, while the real logic
 * lives in php/ and ships via php-deploy-prod. The previous
 * in-line implementation here used TEOS_BASEDIR (env) and a
 * bare realpath() that bypassed the canonical library shape;
 * that diverged from the htaccess rewrite, which passes
 * ?prefix=<dir>&path=<rel>. Routing through the php/
 * canonical version restores a single source of truth and
 * avoids the env-var mismatch.
 */

require_once("/srv/www/bbsengine6/php/serve-md.php");
