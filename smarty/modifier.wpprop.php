<?php

/**
 * Smarty plugin to evaluate wpprop codes
 * @package bbsengine5
 */


/**
 * wp_prop.inc - code to work with props: formatting tags that are converted
 * into HTML.
 *
 * began Sat Jun 29 13:17:30 CDT 2002 by Chad Hendry.
 *
 * @package bbsengine5
 */


/* {{{ prop interpretation functions
 */

/* {{{ function _wp_prop_int_html */
// used for 'close tags' that do not have arguments
function _wp_prop_int_html($matches, $data)
{
   return $data;
}
/* }}} */

/* {{{ function _wp_prop_int_printf */
// accepts *one* argument
function _wp_prop_int_printf($matches, $data)
{
    $fmt_string = $data;
    $param = strlen($matches[3]) ? $matches[3] : '';
    $param = htmlentities($param);
    return sprintf($fmt_string, $param);
}
/* }}} */

/* {{{ function _wp_prop_int_printf_with_default */
function _wp_prop_int_printf_with_default($matches, $data)
{
   $fmt_string = $data[0];
   $default = $data[1];

   $param = strlen($matches[3]) ? $matches[3] : $default;

   return sprintf($fmt_string, $param);
}
/* }}} */

// aolbonics does not have a 'close' tag, accepts one argument
function _wp_prop_int_aolbonics($matches, $data)
{
    $fmt_string = $data;
    $param = strlen($matches[3]) ? $matches[3] : '';
    
    $buf = sprintf($fmt_string, $param, $param, $param);
    return $buf;
}
/* }}} */


function _wp_prop_int_link($matches, $data)
{
    logentry("_wp_prop_int_link.100: matches=".var_export($matches, true)." data=".var_export($data, true));
    $fmt_string = $data;
    $param = strlen($matches[3]) ? $matches[3] : '';
    
    $buf = sprintf($fmt_string, $param, $param);
    return $buf;
}

function _wp_prop_int_youtube($matches, $data)
{
  $tube = '<object id="flash"  type="application/x-shockwave-flash" data="http://www.youtube.com/v/%s&amp;rel=1" width="320" height="240" >';
//  $tube.= '<param name="flashvars" value="id={$vid.id}" />';
  $tube.= '<param name="allowscriptaccess" value="sameDomain" />';
  $tube.= '<param name="movie" value="http://www.youtube.com/v/%s&amp;rel=1" />';
  $tube.= '<param name="quality" value="high" />';
  $tube.= '<param name="bgcolor" value="#808080" />';
  $tube.= '<param name="menu" value="false" />';
  $tube.= '<param name="wmode" value="transparent" />';
  $tube.= '</object>';

    $fmt_string = $tube;
    $param = strlen($matches[3]) ? $matches[3] : '';
    
    $buf = sprintf($fmt_string, $param, $param);
    return $buf;
}

/* {{{ function _wp_prop_callback_func
 * a callback function to preg_replace_callback that returns the substitution
 * text for the supplied prop. */
function _wp_prop_callback_func($matches)
{
/* {{{ _wp_prop_interpretation_table
 * maps every prop name to an interpretation function and a parameter passed
 * to the interpretation function. */
$table = array
(
   /* {{{ colors of the rainbow
    */
   'red'     => ['_wp_prop_int_html',
                      '<span style="color: #FF0000">'],
   '/red'    => ['_wp_prop_int_html', '</span>'],
   'orange'  => ['_wp_prop_int_html',
                      '<span style="color: #FF8000">'],
   '/orange' => ['_wp_prop_int_html', '</span>'],
   'yellow'  => ['_wp_prop_int_html',
                      '<span style="color: #FFFF00">'],
   '/yellow' => ['_wp_prop_int_html', '</span>'],
   'green'   => ['_wp_prop_int_html',
                      '<span style="color: #00FF00">'],
   '/green'  => ['_wp_prop_int_html', '</span>'],
   'blue'    => ['_wp_prop_int_html',
                      '<span style="color: #0000FF">'],
   '/blue'   => ['_wp_prop_int_html', '</span>'],
   'purple'  => ['_wp_prop_int_html',
                      '<span style="color: #FF00FF">'],
   '/purple' => ['_wp_prop_int_html', '</span>'],
   'black'   => ['_wp_prop_int_html',
                      '<span style="color: #000000">'],
   '/black'  => ['_wp_prop_int_html', '</span>'],
   'white'   => ['_wp_prop_int_html',
                      '<span style="color: #FFFFFF">'],
   '/white'  => ['_wp_prop_int_html', '</span>'],
   /* }}} */

   /* {{{ fonts
    */
   'f'  => ['_wp_prop_int_printf',
                 '<span style="font-family: %s">'],
   '/f' => ['_wp_prop_int_html', '</span>'],
   /* }}} */

   /* {{{ font attributes
    */
   'b'  => ['_wp_prop_int_html',
                 '<span style="font-weight: bold">'],

   'bold' => ['_wp_prop_int_html',
   				 '<span style="font-weight: bold">'],

   '/b' => ['_wp_prop_int_html', '</span>'],

   '/bold' => ['_wp_prop_int_html', '</span>'],
   
   'br' => ['_wp_prop_int_html','<br />'],

   'i'  => ['_wp_prop_int_html',
                 '<span style="font-style: italic">'],
   '/i' => ['_wp_prop_int_html', '</span>'],

   'italics' => ['_wp_prop_int_html',
                 '<span style="font-style: italic">'],
   '/italics' => ['_wp_prop_int_html', '</span>'],

   'u'  => ['_wp_prop_int_html',
                 '<span style="text-decoration: underline">'],
   '/u' => ['_wp_prop_int_html', '</span>'],

   'underline'  => ['_wp_prop_int_html',
                 '<span style="text-decoration: underline">'],
   '/underline' => ['_wp_prop_int_html', '</span>'],

   's'  => ['_wp_prop_int_html',
                 '<span style="text-decoration: line-through">'],
   '/s' => ['_wp_prop_int_html', '</span>'],

   'strike'  => ['_wp_prop_int_html',
                 '<span style="text-decoration: line-through">'],
   '/strike' => ['_wp_prop_int_html', '</span>'],

   /* }}} */

   /* {{{ lists
    */
   'ol' => ['_wp_prop_int_html', '<ol>'],
   'ul' => ['_wp_prop_int_html', '<ul>'],
   'list'  => ['_wp_prop_int_html', '<ul>'],
   'item'  => ['_wp_prop_int_html', '<li>'],
   '/item' => ['_wp_prop_int_html', '</li>'],
   'li' => ['_wp_prop_int_html', '<li>'],
   '/li'  => ['_wp_prop_int_html', '</li>'],
   '/list' => ['_wp_prop_int_html', '</ul>'],
   '/ul' => ['_wp_prop_int_html', '</ul>'],
   '/ol' => ['_wp_prop_int_html', '</ol>'],
   /* }}} */

   /* {{{ quotes
    */
   'blockquote' => ['_wp_prop_int_html', '<blockquote>'],
   '/blockquote' => ['_wp_prop_int_html', '</blockquote>'],
   /* }}} */

   /* {{{ formatting
    */
   'pre' => ['_wp_prop_int_html', '<pre>'],
   '/pre' => ['_wp_prop_int_html', '</pre>'],
   /* }}} */

   /* {{{ links */
   'link'  => ['_wp_prop_int_link', '<a href="%s" title="%s">'],
   '/link' => ['_wp_prop_int_html', '</a>'],
   /* }}} */

    /* {{{ anchors */
    'anchor' => ['_wp_prop_int_printf', '<a name="%s"></a>'],

   /* {{{ indentation */
   'indent'  => ['_wp_prop_int_printf_with_default',
                      ['<div style="margin-left: %s">', '1em'],
   '/indent' => ['_wp_prop_int_html', '</div>'],
   /* }}} */

   /* {{{ font size */
   'small'   => ['_wp_prop_int_html',
                      '<span style="font-size: small">'],
   '/small'  => ['_wp_prop_int_html', '</span>'],

   'large'   => ['_wp_prop_int_html',
                      '<span style="font-size: large">'],
   '/large'  => ['_wp_prop_int_html', '</span>'],
   'h1' => ['_wp_prop_int_html', '<h1>'],
   '/h1' => ['_wp_prop_int_html', '</h1>'],
   'h2' => ['_wp_prop_int_html', '<h2>'],
   '/h2' => ['_wp_prop_int_html', '</h2>'],
   'h3' => ['_wp_prop_int_html', '<h3>'],
   '/h3' => ['_wp_prop_int_html', '</h3>'],
   'h4' => ['_wp_prop_int_html', '<h4>'],
   '/h4' => ['_wp_prop_int_html', '</h4>'],
   /* }}} */

   /* {{{ images */
/* FIX: check the MIME-TYPE of the link prior to display of it so we're not vulnerable to
   FIX: xss or goodness-knows-what */
/*   'image'   => ['_wp_prop_int_printf', '<img src="%s">'], */
   /* }}} */

   /* {{{ text alignment */
   'left'     => ['_wp_prop_int_html',
                       '<div style="text-align: left">'],
   '/left'    => ['_wp_prop_int_html', '</div>'],
   'right'    => ['_wp_prop_int_html',
                       '<div style="text-align: right">'],
   '/right'   => ['_wp_prop_int_html', '</div>'],
   'center'   => ['_wp_prop_int_html',
                       '<div style="text-align: center">'],
   '/center'  => ['_wp_prop_int_html', '</div>'],
   'justify'  => ['_wp_prop_int_html',
                       '<div style="text-align: justify">'],
   '/justify' => ['_wp_prop_int_html', '</div>'],
   /* }}} */

   /* {{{ character entities */
   'mdash'    => ['_wp_prop_int_html', '&mdash;'],
   'ndash'    => ['_wp_prop_int_html', '&ndash;'],
   'copy'     => ['_wp_prop_int_html', '&copy;'],
   'reg'      => ['_wp_prop_int_html', '&reg;'],
   'trade'    => ['_wp_prop_int_html', '&trade;'],
   'cent'     => ['_wp_prop_int_html', '&cent;'],
   'pound'    => ['_wp_prop_int_html', '&pound;'],
   'yen'      => ['_wp_prop_int_html', '&yen;'],
   'clubs'    => ['_wp_prop_int_html', '&clubs;'],
   'hearts'   => ['_wp_prop_int_html', '&hearts;'],
   'diamonds' => ['_wp_prop_int_html', '&diams;'],
   'spades'   => ['_wp_prop_int_html', '&spades;'],
   'deg'      => ['_wp_prop_int_html', '&deg;'],
   'apos'     => ['_wp_prop_int_html', '&apos;'],
   'eacute'   => ['_wp_prop_int_html', '&eacute;'],
   /* }}} */

   "aolbonics" => ["_wp_prop_int_aolbonics", '<a href="/aolbonics.php?mode=lookup&amp;word=%s" title="lookup %s in glossary">%s</a>'],
   "glossary" => ["_wp_prop_int_aolbonics", '<a href="/aolbonics.php?mode=lookup&amp;word=%s" title="lookup %s in glossary">%s</a>'],

   'acronym' => ['_wp_prop_int_printf', '<acronym title="%s">'],
   '/acronym' => ['_wp_prop_int_html', '</acronym>'],

   'p' => ['_wp_prop_int_html', '<p>'],
   '/p' => ['_wp_prop_int_html', '</p>'],

//   "youtube" => ["_wp_prop_int_youtube", '<object width="425" height="355"><param name="movie" value="http://www.youtube.com/v/%s&amp;rel=1"></param><param name="wmode" value="transparent"></param><embed src="http://www.youtube.com/v/%s&amp;rel=1" type="application/x-shockwave-flash" wmode="transparent" width="425" height="355"></embed></object>')
   "youtube" => ["_wp_prop_int_youtube", '']
  

);
/* }}} */

//   global $_wp_prop_interpretation_table;

//  $table = $_GLOBALS["_wp_prop_interpretation_table"];
//  var_dump($table);
   $leading_ws  = $matches[1];
   $prop_name   = $matches[2];
   $prop_param  = $matches[3];
   $trailing_ws = $matches[4];

//   logentry("wpprop: name: [" . $prop_name . "]");
   
   if (($pos = strrpos($leading_ws, "\r\n")) !== false)
     $leading_ws = substr_replace($leading_ws, '', $pos, 2);

   if (($pos = strpos($trailing_ws, "\r\n")) !== false)
     $trailing_ws = substr_replace($trailing_ws, '', $pos, 2);

//  logentry("wpprop: length of jumptable: " . count($table));
   if (isset($table[$prop_name]))
     {
//       logentry("wpprop: got one!");
        return $leading_ws . $table[$prop_name][0]($matches, $table[$prop_name][1]) .$trailing_ws;
     }
   else
     return $matches[0];
}
/* }}} */

/* {{{ function wp_prop_eval
 * returns a string with special characters converted to their HTML entities.
*/
function wp_prop_eval($str)
{
    $pattern = '/' .
        "([[:space:]]*)" .
        '\[' .
              '(\/?[a-zA-Z][a-zA-Z0-9_]*)' .
              ':?([^\]]+)?' .
              '\]' .
              '([[:space:]]*)' .
              '/m';

   
    return preg_replace_callback($pattern, "_wp_prop_callback_func", $str);
//   return nl2br(preg_replace_callback($pattern, '_wp_prop_callback_func', htmlentities($str)));
}
/* }}} */

/**
 * Smarty wpprop modifier plugin
 *
 * Type:     modifier<br />
 * Name:     wpprop<br />
 * Date:     May 18, 2006
 * Purpose:  evaluate wpprop codes and return html
 * Input:    string to evaluate
 * Example:  {$var|wpprop}
 * @version 1.0
 * @param string
 * @return string
 */
function smarty_modifier_wpprop($str)
{
    $res = wp_prop_eval($str);
//    logentry("smarty_modifier_wpprop called");
//    var_dump($res);
    return $res;
}

?>
