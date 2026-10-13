<?php

// @since 2026-10-13 — This file and zoid6/smarty/modifier.datestamp.php
// are intentionally close cousins, not byte-identical. Both delegate
// to \bbsengine6\util\datestamp() (the canonical PHP date/time
// formatter in bbsengine6/php/util.php) — there is one walker
// implementation, three call sites (the helper itself plus the two
// Smarty modifiers). What differs:
//
//   1. This file (bbsengine6) carries a VHOSTDOCROOT bootstrap block
//      that primes include_path for bbsengine6config.php when the
//      plugin loads outside a fully-bootstrapped vhost (e.g. when
//      Smarty's plugin_dir lookup hits bbsengine6/smarty/ directly
//      without going through engine.php). zoid6's modifier does
//      NOT need this block: zoid6-using vhosts load zoid6config.php
//      first, which transitively sets up the same include_path.
//      Adding a mirror block to zoid6 would be dead code; removing
//      it from here would drop a defensive guardrail. Symmetry in
//      behavior is preserved by the shared helper — asymmetry in
//      file structure is by design.
//
//   2. Cosmetic: legacy CVS $Id tag, @package name, Input: doc
//      phrasing, and @author line. These are pre-2026 differences
//      inherited from the original smarty2/smarty3 plugins; they
//      have no runtime effect.

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
// @since 2026-10-13 — Thin wrapper around \bbsengine6\util\datestamp().
// Previously embedded a 100+ line token-aware walker here; the walker
// now lives in bbsengine6/php/util.php (the canonical PHP date/time
// formatter, mirroring bbsengine6.util.datestamp in Python). See
// bbsengine6/handbook/specs/datestamp.md for the full spec.

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