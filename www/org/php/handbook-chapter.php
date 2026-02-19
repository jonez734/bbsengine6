<?php

require_once("config.php");
require_once("bbsenginedotorg.php");
require_once("bbsengine3.php");

require_once("Markdown.inc.php");

// define("CHAPTERDIR", DOCUMENTROOT . "handbook/");

class chapter
{
  function main()
  {
    $chapter = isset($_REQUEST["chapter"]) ? $_REQUEST["chapter"] : null;
    $chapter = basename($chapter);
    $filepath = HANDBOOKDIR.$chapter.".txt";
    if (file_exists($filepath) === True && is_readable($filepath) === True)
    {
      $title = "bbsengine3 handbook: ".basename($filepath, ".txt");

      $body = file_get_contents($filepath);
      $tmpl = getsmarty();
      $tmpl->assign("body", $body);
      $tmpl->assign("name", basename($filepath));
      $tmpl->assign("title", $title);
      $page = getpage($title);
      $page->addBodyContent(fetchpageheader());
      $page->addBodyContent($tmpl->fetch("handbook-chapter.tmpl"));
      $page->addBodyContent(fetchpagefooter());
      $page->display();
      return;
    }
    else
    {
      displayerrorpage("File Not Found", 404);
      return;
    }
    return;
  }
}

$a = new chapter();
$b = $a->main();
if (PEAR::isError($b))
{
  displayerrorpage($b->getMessage());
  exit;
}