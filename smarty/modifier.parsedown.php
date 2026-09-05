<?php
/**
 * Smarty modifier to convert Markdown to HTML using the shared
 * \bbsengine6\markdown renderer.
 *
 * The first heading is lifted out of the body and wrapped in a
 * <div class="header">; the remainder goes inside <div class="body">.
 * Templates that call `{$body|parsedown}` rely on this shape.
 *
 * Security settings are owned by \bbsengine6\markdown\renderHtml()
 * (setMarkupEscaped, setSafeMode) — this modifier does not set them.
 */

require_once(__DIR__ . "/../php/markdown.php");

function smarty_modifier_parsedown($str)
{
  $html = \bbsengine6\markdown\renderHtml((string) $str, breaks: false);

  $header = '';
  $html = preg_replace_callback('/<h([1-6])>(.*?)<\/h\1>/', function($m) use (&$header) {
    $header = '<div class="header"><h' . $m[1] . '>' . $m[2] . '</h' . $m[1] . '></div>';
    return '';
  }, $html);

  return $header . '<div class="body">' . trim($html) . '</div>';
}
