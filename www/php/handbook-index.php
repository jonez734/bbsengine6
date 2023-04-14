<?php

require_once("config.php");
require_once("bbsenginedotorg.php");
require_once("bbsengine3.php");

/* moved to handbook.php */

function main()
{

  $files = glob("/srv/www/vhosts/bbsengine.org/80/html/handbook/*.txt");
  if ($files === False)
  {
    return PEAR::raiseError("failed to list handbook chapters (code: handbook.100)");
  }

  $tmpl = getsmarty();
  $tmpl->assign("files", $files);

  $page = getpage("bbsengine3 handbook");
  $page->addBodyContent(fetchpageheader());
  $page->addBodyContent($tmpl->fetch("handbook-index.tmpl"));
  $page->addBodyContent(fetchpagefooter());
  $page->display();
  
  return;
}

$a = main();
if (PEAR::isError($a))
{
  displayerrorpage($a->getMessage());
  exit;
}

?>
