<?php

require_once("config.prg");
require_once(SITENAME.".prg");
require_once("bbsengine5.prg");

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
  require_once(buildpluginfilepath($template->smarty, "modifier.escape.php"));
  require_once(buildpluginfilepath($template->smarty, "modifier.wpprop.php"));

  $path = isset($options["path"]) ? $options["path"] : null;
  $path = normalizelabelpath($path);
  
  $breadcrumbs = isset($options["breadcrumbs"]) ? $options["breadcrumbs"] : False;
  
  $itemprop = isset($options["itemprop"]) ? $options["itemprop"] : False;
  
//  logentry("function.teos.200: path=".var_export($options["path"], True)." labelpath=".var_export($labelpath, True));

  $dbh = dbconnect(SYSTEMDSN);
  if (PEAR::isError($dbh))
  {
    logentry("function.teos.100: ". $dbh->toString());
    return "TEOS.100";
  }

//  logentry("function.teos.101: labelpath=".var_export($labelpath, True));

  if ($breadcrumbs === False)
  {
    $sql = "select * from engine.sig where path=?";
    $dat = array($path);
    $res = $dbh->getRow($sql, array("text", "text"), $dat, array("text"));
    if (PEAR::isError($res))
    {
      logentry("function.teos.102: " . $res->toString());
      return "TEOS.102";
    }

    if ($res === null)
    {
      logentry("function.teos.104: path ".var_export($path, True)." not found");
      return "TEOS.104";
    }
//    logentry("function.teos.106: res=".var_export($res, true));
    
    $title = $res["title"];

    // http://stackoverflow.com/a/5448671
    $uri = $res["uri"];

    $title = smarty_modifier_escape($title);
    $title = smarty_modifier_wpprop($title);

//    logentry("title=".var_export($title, True));
    
    $tmpl = getsmarty();
    $tmpl->assign("uri", joinpath($uri, "/"));
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
