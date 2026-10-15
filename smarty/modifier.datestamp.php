<?php

//
// $Id: modifier.datestamp.php 1487 2011-04-12 21:00:40Z jam $
//
// @since 2026-10-15 — Byte-identical with zoid6/smarty/modifier.datestamp.php.
// This file and the zoid6 sibling are intentionally byte-identical
// so any divergence is impossible. The VHOSTDOCROOT bootstrap that
// used to live inline here has been moved to
// \bbsengine6\util\smarty_plugin_bootstrap() in bbsengine6/php/util.php
// so both modifiers can share it. The bootstrap is idempotent:
//   - bbsengine6 standalone case: primes include_path for
//     bbsengine6config.php when the plugin loads outside a fully-
//     bootstrapped vhost.
//   - zoid6-using vhost case: no-op (zoid6config.php already set
//     include_path before the plugin is loaded).
// Both modifiers delegate to \bbsengine6\util\datestamp() so the
// output is byte-identical by construction. See
// bbsengine6/handbook/specs/datestamp.md.

\bbsengine6\util\smarty_plugin_bootstrap();
require_once("config.php");

/**
 * Smarty plugin to take a timestamp expressed in UNIX epoch and return a string that formats it in a consistent way.
 * @package bbsengine6
 */


/**
 * Smarty datestamp modifier plugin
 *
 * Type:     modifier<br />
 * Name:     datestamp<br />
 * Date:     Aug 24, 2006<br />
 * Purpose:  convert UNIX-epoch timestamp into a human readable string.<br />
 * Input:    integer to evaluate<br />
 * Example:  {$var|datestamp}<br />
 * Example:  {$var|datestamp:"%Y-%m-%d"}<br />
 * @author   Jeff MacDonald <jam [at] zoid technologies dot com>
 * @version 2.1
 * @param string         $timestamp Unix epoch (integer or numeric string).
 *                                 Non-numeric input renders as empty string.
 * @param string|null    $format    Optional strftime format string.
 *                                 See \bbsengine6\util\datestamp() for the
 *                                 resolution chain (format arg → DATEFORMAT
 *                                 → default).
 * @return string
 */
function smarty_modifier_datestamp($string, $format = null)
{
    if (!is_numeric($string)) {
        return '';
    }
    return \bbsengine6\util\datestamp((int)$string, $format);
}
