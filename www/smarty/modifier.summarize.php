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
  //the default limit is 20 as in the old saying, "describe it in 20 words or less"
  $words = 0;
  $return = "";
  
  if ($limit < 1 || !is_int($limit))
  {
    return $return;
  } 
  
  $word = strtok($string, " \n\t");
  $return .= $word;
  
  //get the first word, initialize strtok
  while($word && (++$words < $limit)) 
  {
    // while there's more words to get and we're still under the limit
    $word = strtok(" \n\t");
    $return .= " " . $word;
  }
  return $return;

}

?>
