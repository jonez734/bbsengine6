<?php

// @since 2026-09-29 — VHOSTCONFIG fallback removed. The plugin now
// relies on VHOSTDOCROOT alone for include_path setup. If VHOSTDOCROOT
// is unset on FPM, the bare require_once()s below will fail and the
// rendering handler will swallow the throwable (same pre-2026-09-26
// failure mode).
$vhostroot = getenv('VHOSTDOCROOT');
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
