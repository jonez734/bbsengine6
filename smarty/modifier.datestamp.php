<?php

// @since 2026-09-26 — defensive include_path set-up.
//
// Smarty lazy-loads plugins from its pluginsdir; when this
// file is reached, the FPM worker's include_path does not
// necessarily have VHOSTDOCROOT on it, even when the vhost's
// config.php ran add_include_paths() earlier (VHOSTDOCROOT
// may not propagate to FPM under some mod_env + mod_rewrite
// + mod_proxy_fcgi combos). The bare require_once("config.php")
// below then fails with 'Failed to open stream: No such
// file or directory' and the rendering handler swallows
// the throwable.
//
// Fix: re-establish the vhost docroot on include_path right
// now, by reading VHOSTDOCROOT (preferred) or VHOSTCONFIG
// (fallback) and appending the paths the vhost's
// config-prod.php registers. file_exists() / function_exists()
// guards keep dev/test paths from breaking.
$vhostroot = getenv('VHOSTDOCROOT');
if (!is_string($vhostroot) || $vhostroot === '' || !is_dir($vhostroot)) {
    $vhostconfig = getenv('VHOSTCONFIG');
    if (is_string($vhostconfig) && $vhostconfig !== '' && is_file($vhostconfig)) {
        $vhostroot = dirname($vhostconfig);
    }
}
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
