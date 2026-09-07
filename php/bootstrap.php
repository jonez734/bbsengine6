<?php

namespace bbsengine6 {

/**
 * Set PHP include_path for bbsengine6.
 *
 * @param array $paths Optional additional paths to prepend to defaults.
 * @return bool True on success, false on failure.
 * @since 20250619
 */
function bootstrap(array $paths = []): bool
{
    $defaults = [
        __DIR__,
        dirname(__DIR__),
        // @since 2026-09-07 — `www/org/php/handbook.php:145` does
        // `require_once("router.php")` (bare name). The router
        // lives under the project root's `engine/` sibling, which
        // is not covered by `__DIR__` (php/) or `dirname(__DIR__)`
        // (project root) on its own. Without this entry the bare
        // require would fail with `Failed opening required
        // 'router.php'` even when the prod engine/ tree is
        // correctly shipped via `engine/Makefile deploy-engine`.
        dirname(__DIR__) . "/engine/",
        "/srv/www/markdown/",
        "/srv/www/smarty/",
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

namespace {
require_once('Log.php');

// Backward compatibility: auto-run when included directly
if (function_exists('bbsengine6\bootstrap')) {
    bbsengine6\bootstrap();
}
}
?>
