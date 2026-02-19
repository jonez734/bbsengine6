<?php
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
