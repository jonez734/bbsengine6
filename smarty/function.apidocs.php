<?php

// @since 2026-09-26 — defensive include_path set-up.
//
// Smarty lazy-loads plugins from its pluginsdir; when this
// file is reached, the FPM worker's include_path does not
// necessarily have VHOSTDOCROOT on it, even when the vhost's
// config.php ran add_include_paths() earlier (VHOSTDOCROOT
// may not propagate to FPM under some mod_env + mod_rewrite
// + mod_proxy_fcgi combos). The bare require_once("config.php")
// below then fails with 'Failed to open stream: No such
// file or directory' and the rendering handler swallows
// the throwable.
//
// Fix: re-establish the vhost docroot on include_path right
// now, by reading VHOSTDOCROOT (preferred) or VHOSTCONFIG
// (fallback) and appending the paths the vhost's
// config-prod.php registers. file_exists() / function_exists()
// guards keep dev/test paths from breaking.
$vhostroot = getenv('VHOSTDOCROOT');
if (!is_string($vhostroot) || $vhostroot === '' || !is_dir($vhostroot)) {
    $vhostconfig = getenv('VHOSTCONFIG');
    if (is_string($vhostconfig) && $vhostconfig !== '' && is_file($vhostconfig)) {
        $vhostroot = dirname($vhostconfig);
    }
}
if (is_string($vhostroot) && $vhostroot !== '' && is_dir($vhostroot)) {
    if (function_exists('bbsengine6\\bootstrap')) {
        bbsengine6\bootstrap([$vhostroot]);
    }
    if (function_exists('bbsengine6\\util\\add_include_paths')) {
        bbsengine6\util\add_include_paths([
            $vhostroot,
            $vhostroot . 'teos/',
        ]);
    }
}

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once("config.php");
require_once("engine.php");

function smarty_function_apidocs($options, Smarty_Internal_Template $template)
{
//    logentry("function.apidocs.100: options=".var_export($options, True));
    $type = isset($options["type"]) ? $options["type"] : "function";
    $project = isset($options["project"]) ? $options["project"] : "bbsengine4";
    $name = isset($options["name"]) ? $options["name"] : "NEEDINFO";
    $title = isset($options["title"]) ? $options["title"] : $name;
    $file = isset($options["file"]) ? $options["file"] : "bbsengine4";
    $version = isset($options["version"]) ? $options["version"] : "current";

    $href = "/{$version}/apidocs/packages/{$file}.html#{$type}_{$name}";
    $link = "<a class=\"apidocs\" href=\"{$href}\">{$title}</a>";
    return $link;
}

?>
