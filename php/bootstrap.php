<?php

namespace bbsengine6 {

// @since 2026-10-15 — guard the bbsengine6\bootstrap function
// declaration with function_exists() so the engine can be
// loaded from multiple on-disk paths in the same request
// without a "Cannot redeclare" fatal. The canonical case
// this unblocks: engine/router.php requires the production
// copy at `/srv/www/bbsengine6/php/bootstrap.php` (line 92)
// while the test suite (`php/test_router.php`,
// `php/test_breadcrumbs.php`) requires the in-tree copy at
// `/home/opencode/data/work/bbsengine6/php/bootstrap.php`;
// the two files are byte-identical, but PHP's require_once
// dedup is by path not by content, so both get loaded and
// the second declaration fatals. With this guard, the
// function is declared exactly once and the duplicate
// require_once is a no-op.
//
// The body of `bootstrap()` is unchanged — only the
// declaration is guarded. The existing call site at line
// 63 (`bbsengine6\bootstrap()`) still runs once on
// include.

/**
 * Set PHP include_path for bbsengine6.
 *
 * @param array $paths Optional additional paths to prepend to defaults.
 * @return bool True on success, false on failure.
 * @since 20250619
 */
if (!function_exists('bbsengine6\\bootstrap')) {
function bootstrap(array $paths = []): bool
{
    $defaults = [
        __DIR__,
        dirname(__DIR__),
        "/srv/www/markdown/",
        "/srv/www/smarty/",
        "/usr/share/pear/",
        "/srv/www/bbsengine6/php/",
    ];

    $current = array_filter(
        explode(PATH_SEPARATOR, get_include_path()),
        'strlen'
    );

    $current = array_map(
        static fn($p) => rtrim($p, DIRECTORY_SEPARATOR),
        $current
    );

    $newPaths = array_merge($paths, $defaults);

    foreach ($newPaths as $path) {
        $normalized = rtrim($path, DIRECTORY_SEPARATOR);
        if (!in_array($normalized, $current, true)) {
            $current[] = $normalized;
        }
    }

    $pathString = implode(PATH_SEPARATOR, $current);

    return set_include_path($pathString) !== false;
}
}
}

namespace {
$bbsengine6_vhostroot = getenv('VHOSTDOCROOT');
if (is_string($bbsengine6_vhostroot)
    && $bbsengine6_vhostroot !== ''
    && is_dir($bbsengine6_vhostroot)
    && function_exists('bbsengine6\\bootstrap'))
{
    bbsengine6\bootstrap([$bbsengine6_vhostroot]);
}

require_once('Log.php');

// Backward compatibility: auto-run when included directly
if (function_exists('bbsengine6\bootstrap')) {
    bbsengine6\bootstrap();
}
}
?>
