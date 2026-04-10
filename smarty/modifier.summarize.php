<?php
/**
 * Smarty plugin
 * @package bbsengine4
 * @subpackage plugins
 * Smarty summarize modifier plugin
 * 
 * Type:     modifier<br>
 * Name:     sumamrize<br>
 * Purpose:  summarize a string down to $limit words<br>
 *  @link http://smarty.incutio.com/?page=Smarty
 *          summarize (Smarty Plugins Wiki)
 * Input:<br>
 *         - string: input string of words
 *         - limit: number of words to return
 *
 * @fix: this modifier does not know about HTML, so it winds up truncating
 * @fix: at inappropriate times.
 *
 * @param string
 * @param int
 * @return string
 */
function smarty_modifier_summarize($string, $limit=20)
{
  $words = 0;
  $return = "";

  $limit = (int)$limit;
  if ($limit < 1) {
    $limit = 20;
  }

  if (!is_string($string) || $string === '') {
    return $return;
  }

  $word = strtok($string, " \n\t");
  if ($word === false) {
    return $return;
  }
  $return .= $word;

  while($word !== false && (++$words < $limit))
  {
    $word = strtok(" \n\t");
    if ($word === false) {
      break;
    }
    $return .= " " . $word;
  }
  return $return;

}

?>
