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
// file or directory' and the blurb handler swallows the
// throwable.
//
// Fix: re-establish the vhost docroot on include_path right
// now, by reading VHOSTDOCROOT (preferred) or VHOSTCONFIG
// (fallback) and appending the paths the vhost's
// config-prod.php registers. file_exists() / function_exists()
// guards keep dev/test paths from breaking.
if (file_exists('/srv/www/bbsengine6/php/bootstrap.php')
    && !function_exists('bbsengine6\\bootstrap')) {
    require_once('/srv/www/bbsengine6/php/bootstrap.php');
}
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
