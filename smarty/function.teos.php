<?php

require_once("config.php");
require_once("database.php");
require_once("engine.php");

function buildpluginfilepath($smarty, $name)
{
  foreach ($smarty->getPluginsDir() as $plugindir)
  {
    $p = $plugindir.DIRECTORY_SEPARATOR.basename($name);
    if (file_exists($p))
    {
      return $p;
    }
  }
  return null;
}

function smarty_function_teos($options, Smarty_Internal_Template $template)
{
  require_once(buildpluginfilepath($template->smarty, "modifier.escape.php"));
  require_once(buildpluginfilepath($template->smarty, "modifier.wpprop.php"));

  $path = isset($options["path"]) ? $options["path"] : null;
  $title = isset($options["title"]) ? $options["title"] : null;
  $itemprop = isset($options["itemprop"]) ? $options["itemprop"] : false;

  // Path is a dot-separated label: "rec.arts.tv.the-a-team"
  $segments = array_values(array_filter(explode(".", $path)));
  $uriSegments = array_map(function($s) { return str_replace("_", "-", $s); }, $segments);

  $uri = implode("/", $uriSegments) . "/";

  if ($title === null) {
    if (count($uriSegments) > 0) {
      $title = end($uriSegments);
    } else {
      $title = $path;
    }
    $title = str_replace(["-", "_"], " ", $title);
  }

  $title = smarty_modifier_escape($title);
  $title = smarty_modifier_wpprop($title);

  $tmpl = \bbsengine6\getsmarty();
  $tmpl->assign("uri", $uri);
  $tmpl->assign("title", $title);
  $tmpl->assign("itemprop", $itemprop);

  return $tmpl->fetch("function.teos.tmpl");
}
?>
