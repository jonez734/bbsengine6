<?php

// @since 2026-09-29 — VHOSTCONFIG fallback removed. The plugin now
// relies on VHOSTDOCROOT alone for include_path setup. If VHOSTDOCROOT
// is unset on FPM, the bare require_once("config.php") below will
// fail and the rendering handler will swallow the throwable (same
// pre-2026-09-26 failure mode).
$vhostroot = getenv('VHOSTDOCROOT');
if (is_string($vhostroot) && $vhostroot !== '' && is_dir($vhostroot)) {
    if (function_exists('bbsengine6\\bootstrap')) {
        bbsengine6\bootstrap([$vhostroot]);
    }
    if (function_exists('bbsengine6\\util\\add_include_paths')) {
        bbsengine6\util\add_include_paths([
            $vhostroot,
            $vhostroot . 'teos/',
        ]);
    }
}

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
 * Date:     Aug 24, 2006<br />
 * Purpose:  convert UNIX-epoch timestamp into a human readable string.<br />
 * Input:    string to evaluate<br />
 * Example:  {$var|datestamp}<br />
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
