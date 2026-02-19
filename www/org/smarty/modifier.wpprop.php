<?php

// require_once("wp_prop.php");

/**
 * Smarty plugin to evaluate wpprop codes
 * @package bbsengine4
 */


/**
 * wp_prop.inc - code to work with props: formatting tags that are converted
 * into HTML.
 *
 * began Sat Jun 29 13:17:30 CDT 2002 by Chad Hendry.
 *
 * @package bbsengine4
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
//    logentry("wpprop: link");

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
   'red'     => array('_wp_prop_int_html',
                      '<span style="color: #FF0000">'),
   '/red'    => array('_wp_prop_int_html', '</span>'),
   'orange'  => array('_wp_prop_int_html',
                      '<span style="color: #FF8000">'),
   '/orange' => array('_wp_prop_int_html', '</span>'),
   'yellow'  => array('_wp_prop_int_html',
                      '<span style="color: #FFFF00">'),
   '/yellow' => array('_wp_prop_int_html', '</span>'),
   'green'   => array('_wp_prop_int_html',
                      '<span style="color: #00FF00">'),
   '/green'  => array('_wp_prop_int_html', '</span>'),
   'blue'    => array('_wp_prop_int_html',
                      '<span style="color: #0000FF">'),
   '/blue'   => array('_wp_prop_int_html', '</span>'),
   'purple'  => array('_wp_prop_int_html',
                      '<span style="color: #FF00FF">'),
   '/purple' => array('_wp_prop_int_html', '</span>'),
   'black'   => array('_wp_prop_int_html',
                      '<span style="color: #000000">'),
   '/black'  => array('_wp_prop_int_html', '</span>'),
   'white'   => array('_wp_prop_int_html',
                      '<span style="color: #FFFFFF">'),
   '/white'  => array('_wp_prop_int_html', '</span>'),
   /* }}} */

   /* {{{ fonts
    */
   'f'  => array('_wp_prop_int_printf',
                 '<span style="font-family: %s">'),
   '/f' => array('_wp_prop_int_html', '</span>'),
   /* }}} */

   /* {{{ font attributes
    */
   'b'  => array('_wp_prop_int_html',
                 '<span style="font-weight: bold">'),

   'bold' => array('_wp_prop_int_html',
   				 '<span style="font-weight: bold">'),

   '/b' => array('_wp_prop_int_html', '</span>'),

   '/bold' => array('_wp_prop_int_html', '</span>'),
   
   'br' => array('_wp_prop_int_html','<br />'),

   'i'  => array('_wp_prop_int_html',
                 '<span style="font-style: italic">'),
   '/i' => array('_wp_prop_int_html', '</span>'),

   'italics' => array('_wp_prop_int_html',
                 '<span style="font-style: italic">'),
   '/italics' => array('_wp_prop_int_html', '</span>'),

   'u'  => array('_wp_prop_int_html',
                 '<span style="text-decoration: underline">'),
   '/u' => array('_wp_prop_int_html', '</span>'),

   'underline'  => array('_wp_prop_int_html',
                 '<span style="text-decoration: underline">'),
   '/underline' => array('_wp_prop_int_html', '</span>'),

   's'  => array('_wp_prop_int_html',
                 '<span style="text-decoration: line-through">'),
   '/s' => array('_wp_prop_int_html', '</span>'),

   'strike'  => array('_wp_prop_int_html',
                 '<span style="text-decoration: line-through">'),
   '/strike' => array('_wp_prop_int_html', '</span>'),

   /* }}} */

   /* {{{ lists
    */
   'ol' => array('_wp_prop_int_html', '<ol>'),
   'ul' => array('_wp_prop_int_html', '<ul>'),
   'list'  => array('_wp_prop_int_html', '<ul>'),
   'item'  => array('_wp_prop_int_html', '<li>'),
   '/item' => array('_wp_prop_int_html', '</li>'),
   'li' => array('_wp_prop_int_html', '<li>'),
   '/li'  => array('_wp_prop_int_html', '</li>'),
   '/list' => array('_wp_prop_int_html', '</ul>'),
   '/ul' => array('_wp_prop_int_html', '</ul>'),
   '/ol' => array('_wp_prop_int_html', '</ol>'),
   /* }}} */

   /* {{{ quotes
    */
   'blockquote' => array('_wp_prop_int_html', '<blockquote>'),
   '/blockquote' => array('_wp_prop_int_html', '</blockquote>'),
   /* }}} */

   /* {{{ formatting
    */
   'pre' => array('_wp_prop_int_html', '<pre>'),
   '/pre' => array('_wp_prop_int_html', '</pre>'),
   /* }}} */

   /* {{{ links */
   'link'  => array('_wp_prop_int_link', '<a href="%s" title="%s">'),
   '/link' => array('_wp_prop_int_html', '</a>'),
   /* }}} */

    /* {{{ anchors */
    'anchor' => array('_wp_prop_int_printf', '<a name="%s"></a>'),

   /* {{{ indentation */
   'indent'  => array('_wp_prop_int_printf_with_default',
                      array('<div style="margin-left: %s">', '1em')),
   '/indent' => array('_wp_prop_int_html', '</div>'),
   /* }}} */

   /* {{{ font size */
   'small'   => array('_wp_prop_int_html',
                      '<span style="font-size: small">'),
   '/small'  => array('_wp_prop_int_html', '</span>'),

   'large'   => array('_wp_prop_int_html',
                      '<span style="font-size: large">'),
   '/large'  => array('_wp_prop_int_html', '</span>'),
   'h1' => array('_wp_prop_int_html', '<h1>'),
   '/h1' => array('_wp_prop_int_html', '</h1>'),
   'h2' => array('_wp_prop_int_html', '<h2>'),
   '/h2' => array('_wp_prop_int_html', '</h2>'),
   'h3' => array('_wp_prop_int_html', '<h3>'),
   '/h3' => array('_wp_prop_int_html', '</h3>'),
   'h4' => array('_wp_prop_int_html', '<h4>'),
   '/h4' => array('_wp_prop_int_html', '</h4>'),
   /* }}} */

   /* {{{ images */
/* FIX: check the MIME-TYPE of the link prior to display of it so we're not vulnerable to
   FIX: xss or goodness-knows-what */
/*   'image'   => array('_wp_prop_int_printf', '<img src="%s">'), */
   /* }}} */

   /* {{{ text alignment */
   'left'     => array('_wp_prop_int_html',
                       '<div style="text-align: left">'),
   '/left'    => array('_wp_prop_int_html', '</div>'),
   'right'    => array('_wp_prop_int_html',
                       '<div style="text-align: right">'),
   '/right'   => array('_wp_prop_int_html', '</div>'),
   'center'   => array('_wp_prop_int_html',
                       '<div style="text-align: center">'),
   '/center'  => array('_wp_prop_int_html', '</div>'),
   'justify'  => array('_wp_prop_int_html',
                       '<div style="text-align: justify">'),
   '/justify' => array('_wp_prop_int_html', '</div>'),
   /* }}} */

   /* {{{ character entities */
   'mdash'    => array('_wp_prop_int_html', '&mdash;'),
   'ndash'    => array('_wp_prop_int_html', '&ndash;'),
   'copy'     => array('_wp_prop_int_html', '&copy;'),
   'reg'      => array('_wp_prop_int_html', '&reg;'),
   'trade'    => array('_wp_prop_int_html', '&trade;'),
   'cent'     => array('_wp_prop_int_html', '&cent;'),
   'pound'    => array('_wp_prop_int_html', '&pound;'),
   'yen'      => array('_wp_prop_int_html', '&yen;'),
   'clubs'    => array('_wp_prop_int_html', '&clubs;'),
   'hearts'   => array('_wp_prop_int_html', '&hearts;'),
   'diamonds' => array('_wp_prop_int_html', '&diams;'),
   'spades'   => array('_wp_prop_int_html', '&spades;'),
   'deg'      => array('_wp_prop_int_html', '&deg;'),
   'apos'     => array('_wp_prop_int_html', '&apos;'),
   'eacute'   => array('_wp_prop_int_html', '&eacute;'),
   /* }}} */

   "aolbonics" => array("_wp_prop_int_aolbonics", '<a href="/aolbonics.php?mode=lookup&amp;word=%s" title="lookup %s in glossary">%s</a>'),
   "glossary" => array("_wp_prop_int_aolbonics", '<a href="/aolbonics.php?mode=lookup&amp;word=%s" title="lookup %s in glossary">%s</a>'),

   'acronym' => array('_wp_prop_int_printf', '<acronym title="%s">'),
   '/acronym' => array('_wp_prop_int_html', '</acronym>'),

   'p' => array('_wp_prop_int_html', '<p>'),
   '/p' => array('_wp_prop_int_html', '</p>'),

//   "youtube" => array("_wp_prop_int_youtube", '<object width="425" height="355"><param name="movie" value="http://www.youtube.com/v/%s&amp;rel=1"></param><param name="wmode" value="transparent"></param><embed src="http://www.youtube.com/v/%s&amp;rel=1" type="application/x-shockwave-flash" wmode="transparent" width="425" height="355"></embed></object>')
   "youtube" => array("_wp_prop_int_youtube", ''),
  

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
 * Smarty cat modifier plugin
 *
 * Type:     modifier<br />
 * Name:     wpprop<br />
 * Date:     May 18, 2006
 * Purpose:  evaluate wpprop codes and return html
 * Input:    string to evaluate
 * Example:  {$var|wpprop}
 * @author   Jeff MacDonald <jam@zoidtechnologies.com>
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
