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
require_once("database.php");
require_once("session.php");
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

function smarty_function_repo($options, Smarty_Internal_Template $template)
{
//  logentry("options=".var_export($options, True));

  require_once(buildpluginfilepath($template->smarty, "modifier.escape.php"));
  require_once(buildpluginfilepath($template->smarty, "modifier.wpprop.php"));

  $dbh = \bbsengine6\database\connect(SYSTEMDSN);

  $project = isset($options["project"]) ? $options["project"] : null;

  if ($project === null || $project === '') {
    return "";
  }

  try
  {
    $sql = "select title from repo.project where name=:project";
    $dat = ["project" => $project];
    $stmt = $dbh->prepare($sql);
    $stmt->execute($dat);
  } catch (PDOException $e) {
    return "";
  }

  if ($stmt->rowcount() === 0)
  {
    \bbsengine6\logentry("function.repo.104: path ".var_export($project, True)." not found");
    return "REPO.104";
  }
  $res = $stmt->fetch();

  $title = isset($res["title"]) ? $res["title"] : $project;

  $href = htmlspecialchars(PROJECTURL.$project, ENT_QUOTES, 'UTF-8');

  $title = smarty_modifier_escape($title);
  $title = smarty_modifier_wpprop($title);

//  logentry("title=".var_export($title, True));

  $repo = "<a class=\"repo\" href=\"{$href}\">{$title}</a>";
  return $repo;
}

?>
