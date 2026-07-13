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
//  logentry("options=".var_export($options, True));
//  $template->smarty->loadPlugin("modifier.escape.php");
//  $template->smarty->loadPlugin("modifier.wpprop.php");
//  \bbsengine6\logentry("function.teos.php: $template=".var_export($template, True));
  require_once(buildpluginfilepath($template->smarty, "modifier.escape.php"));
  require_once(buildpluginfilepath($template->smarty, "modifier.wpprop.php"));

  $path = isset($options["path"]) ? $options["path"] : null;
  $path = \bbsengine6\normalizelabelpath($path);
  
  $breadcrumbs = isset($options["breadcrumbs"]) ? $options["breadcrumbs"] : false;
  
  $itemprop = isset($options["itemprop"]) ? $options["itemprop"] : false;
  
//  logentry("function.teos.200: path=".var_export($options["path"], True)." labelpath=".var_export($labelpath, True));

  $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
/*
  if (($dbh === false))
  {
    logentry("function.teos.100: ". $dbh->toString());
    return "TEOS.100";
  }
*/
//  logentry("function.teos.101: labelpath=".var_export($labelpath, True));

  if ($breadcrumbs === false)
  {
    $sql = "select * from engine.sig where path=:path";
    $dat = ["path" => $path];
    $stmt = $dbh->prepare($sql);
    $stmt->execute($dat);
    if ($stmt->rowcount() === 0)
    {
      // Path not in engine.sig — render a fallback link using the path itself
      $segments = array_filter(explode(".", $path));
      $title = end($segments) ?: $path;
      $title = str_replace(["-", "_"], " ", $title);
      $uri = implode("/", $segments) . "/";

      $title = smarty_modifier_escape($title);
      $title = smarty_modifier_wpprop($title);

      $tmpl = \bbsengine6\getsmarty();
      $tmpl->assign("uri", $uri);
      $tmpl->assign("title", $title);
      $tmpl->assign("itemprop", $itemprop);

      return $tmpl->fetch("function.teos.tmpl");
    }
    
    $res = $stmt->fetch();

    $title = $res["title"];

    $uri = $res["uri"];

    $title = smarty_modifier_escape($title);
    $title = smarty_modifier_wpprop($title);

  //  logentry("title=".var_export($title, True));
    
    $tmpl = \bbsengine6\getsmarty();
    $tmpl->assign("uri", \bbsengine6\joinpath($uri)."/");
    $tmpl->assign("title", $title);
    $tmpl->assign("itemprop", $itemprop);
    
/*
    if ($itemprop === True)
    {
      $teos = "<a class=\"tooltip teosfolder\" data-contenturl=\"{$href}detail?bare\" itemprop=\"url\" href=\"{$href}\"><span itemprop=\"title\">{$title}</span></a>";
    }
    else
    {
      $teos = "<a class=\"tooltip teosfolder\" data-contenturl=\"{$href}detail?bare\" href=\"{$href}\"><span>{$title}</span></a>";
    }
*/
    return $tmpl->fetch("function.teos.tmpl");
  }
}
?>
