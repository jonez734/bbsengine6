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
        "/srv/www/markdown",
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

// Backward compatibility: auto-run when included directly
if (function_exists('bbsengine6\bootstrap')) {
    bbsengine6\bootstrap();
}

?>
