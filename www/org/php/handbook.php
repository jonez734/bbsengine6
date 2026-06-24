<?php

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once("config.php");
require_once("engine.php");
require_once("database.php");
require_once("session.php");

require_once("Markdown.inc.php");

class handbook
{
  function displayindex()
  {
    $version = isset($_REQUEST["version"]) ? $_REQUEST["version"] : null;

    $handbookdir = \HANDBOOKDIR.$_REQUEST["version"]."/handbook/";
    \bbsengine6\logentry("handbookdir=".$handbookdir);
    $files = glob($handbookdir."*.txt");
    \bbsengine6\logentry("files=".var_export($files, True));
    if ($files === False)
    {
      return PEAR::raiseError("failed to list handbook chapters (code: handbook.100)");
    }

    $chapters = [];
    foreach ($files as $f)
    {
      logentry("handbook.100: f=".var_export($f, True));
      $chapters[] = ["file" => $f, "datemodifiedepoch" => filemtime($f)];
    }

    $page = getpage("bbsengine handbook");
    $data = [];
    $data["chapters"] = $chapters;
    $data["pagetemplate"] = "handbook-index.tmpl";
    $data["version"] = $version;
    displaypage($page, $data);

    return;
  }

  function displaychapter()
  {
    $chapter = isset($_REQUEST["chapter"]) ? $_REQUEST["chapter"] : null;
    $chapter = basename($chapter);
    $title = str_replace("-", " ", $chapter);

    $version = isset($_REQUEST["version"]) ? $_REQUEST["version"] : null;

    logentry("handbook.100: chapter=".var_export($chapter, True));
    $filepath = HANDBOOKDIR.$version."/handbook/".$chapter.".txt";
    logentry("handbook.102: filepath=".var_export($filepath, True));
    if (file_exists($filepath) === true && is_readable($filepath) === true)
    {
//      $title = "bbsengine handbook: ".basename($filepath, ".txt");


      $body = file_get_contents($filepath);
      $html = \Michaelf\Markdown::defaultTransform($body);
      $data = [];
      $data["html"] = $html;
//      $data["title"] = $title;
      $data["version"] = $version;
      $data["pagetemplate"] = "handbook-chapter.tmpl";
      $data["filename"] = basename($filepath);
      $data["title"] = $title;
      \bbsengine6\displaypage($data);
      return;
    }
    else
    {
      \bbsengine6\displayerrorpage("File Not Found (handbook)", 404);
      return;
    }
    return;

  }

  function main()
  {
    \bbsengine6\session\start();
    $mode = isset($_REQUEST["mode"]) ? $_REQUEST["mode"] : null;
    switch ($mode)
    {
      case "index":
      {
        $r = $this->displayindex();
        break;
      }
      case "chapter":
      {
        $r = $this->displaychapter();
        break;
      }
    }
    return $r;
  }
};

$a = new handbook();
$b = $a->main();
if (PEAR::isError($b))
{
  displayerrorpage($b->getMessage());
  exit;
}

?>
