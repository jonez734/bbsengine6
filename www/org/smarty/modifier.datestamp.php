<?php

require_once("/srv/www/bbsengine6/php/bootstrap.php");

// 
// $Id: modifier.datestamp.php 1821 2011-08-15 18:41:18Z jam $
//

require_once("config.php");

/**
 * Smarty plugin to take a timstamp expressed in UNIX epoch and return a string that formats it in a consistent way.
 * @package bbsengine4
 */


/**
 * Smarty datestamp modifier plugin
 *
 * Type:     modifier<br />
 * Name:     datestamp<br />
 * Date:     Aug 24, 2006
 * Purpose:  convert UNIX-epoch timestamp into a human readable string.
 * Input:    string to evaluate
 * Example:  {$var|datestamp}
 * @author   Jeff MacDonald <jam [at] zoid technologies dot com>
 * @version 1.0
 * @param string
 * @return string
 */
function smarty_modifier_datestamp($string)
{
    if (!is_numeric($string)) {
        return '';
    }
    $timestamp = (int)$string;

    $map = [
        '%Y' => 'Y', '%y' => 'y', '%m' => 'm', '%d' => 'd',
        '%H' => 'H', '%I' => 'h', '%M' => 'i', '%S' => 's',
        '%p' => 'A', '%Z' => 'T', '%A' => 'l',
    ];

    $format = DATEFORMAT;
    foreach ($map as $from => $to) {
        $format = str_replace($from, $to, $format);
    }

    return date($format, $timestamp);
}

?>
