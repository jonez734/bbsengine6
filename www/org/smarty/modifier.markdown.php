<?php

require_once("Markdown.inc.php");
// require_once("MarkdownExtra.inc.php");

function smarty_modifier_markdown($str)
{
  $html = Markdown::defaultTransform($str);  
  return $html;
}
?>
