<?php
/**
 * Smarty modifier to convert Markdown to HTML using ParsedownExtra
 *
 * Security: Uses setMarkupEscaped and setSafeMode to prevent XSS
 * from user-generated content.
 *
 * Features: Supports tables, footnotes, abbreviations, and other
 * Markdown Extra features.
 */

require_once("vendor/autoload.php");
// require_once("Markdown.inc.php"); // OLD - commented out for reference

function smarty_modifier_parsedown($str)
{
  static $parser = null;
  if ($parser === null) {
    $parser = new \ParsedownExtra();
    $parser->setMarkupEscaped(true);
    $parser->setSafeMode(true);
  }
  $html = $parser->text($str);

  $header = '';
  $html = preg_replace_callback('/<h([1-6])>(.*?)<\/h\1>/', function($matches) use (&$header) {
    $header = '<div class="header"><h' . $matches[1] . '>' . $matches[2] . '</h' . $matches[1] . '></div>';
    return '';
  }, $html);

  $html = trim($html);
  return $header . '<div class="body">' . $html . '</div>';
}
