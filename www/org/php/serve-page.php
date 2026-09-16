<?php

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once("config.php");
require_once("database.php");
require_once("session.php");
require_once("engine.php");

//require_once("Markdown.inc.php");

class page
{
  function main()
  {
    startsession();

    $file = isset($_REQUEST["file"]) ? $_REQUEST["file"] : null;
    $version = isset($_REQUEST["version"]) ? $_REQUEST["version"] : null;
    if ($file === null)
    {
      logentry("page.200: 'file' is null");
      displayerrorpage("page not found", 404);
      return;
    }
    logentry("page.main.100: file=".var_export($file, true)." version=".var_export($version, true));


    $f = "/".joinpath(DOCUMENTROOT, $version, $file);
    $info = pathinfo($f);
    $fileextension = $info["extension"];
    $filename = $info["filename"];

    setreturnto(getcurrenturi());
    setcurrentsite(SITENAME);
    setcurrentaction("view");
    setcurrentpage($filename);

    switch ($fileextension)
    {
      case "md":
      {
        $pagetemplate = "page-markdown.tmpl";
        $content = Markdown::defaultTransform(file_get_contents($f));
        break;
      }
      case "txt":
      {
        $pagetemplate = "page-text.tmpl";
        $content = file_get_contents($f);
        break;
      }
      case "tmpl":
      {
        $pagetemplate = $file;
        $smarty = getsmarty();
        if ($smarty->templateExists($file) == false)
        {
          displayerrorpage("template does not exist", 404);
          return;
        }
        $content = $smarty->fetch($file);
        break;
      }
    }
    logentry("page.100: pagetemplate=".var_export($pagetemplate, true));

    $data = [];
    $data["content"] = $content;
    $data["pagetemplate"] = $pagetemplate;
    
    $res = displaypage(null, $data);
    return $res;
  }
};

$a = new page();
$b = $a->main();
if (PEAR::isError($b))
{
  displayerrorpage($b->getMessage());
  exit;
}
