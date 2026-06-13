<?php
/**
 * Smarty modifier to convert Markdown to HTML
 *
 * Security: Uses $no_markup=true to block raw HTML in input, preventing XSS
 * from user-generated content. Only Markdown-generated HTML is output.
 *
 * Performance: Uses static parser caching. For high-traffic pages with
 * unchanging content, consider pre-compiling markdown to HTML.
 */

require_once("Markdown.inc.php");
// require_once("MarkdownExtra.inc.php");

function smarty_modifier_markdown($str)
{
  static $parser = null;
  if ($parser === null) {
    $parser = new Markdown();
    $parser->no_markup = true;
  }
  $html = $parser->transform($str);

  $header = '';
  $html = preg_replace_callback('/<h([1-6])>(.*?)<\/h\1>/', function($matches) use (&$header) {
    $header = '<div class="header"><h' . $matches[1] . '>' . $matches[2] . '</h' . $matches[1] . '></div>';
    return '';
  }, $html);

  $html = trim($html);
  return $header . '<div class="body">' . $html . '</div>';
}
