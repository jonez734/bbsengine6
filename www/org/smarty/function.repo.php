<?php
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
