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
//
// @since 2026-10-13 — Extended to support the full Python strftime
// vocabulary via a token-aware walker. Translates only %X-prefixed
// strftime tokens to PHP date() tokens; bare letters and other
// non-% characters pass through unchanged. Adds eight previously-
// unmapped tokens (%a, %b, %B, %l, %P, %z, %:z, %j) and the
// achilles-specific %O opt-in (per-user timezone offset).
// See bbsengine6/handbook/specs/datestamp.md for the full spec.

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
 * @version 2.0
 * @param string   $timestamp  Unix epoch (integer or numeric string)
 * @param string|null $format  Optional strftime format string.
 *                              If null, reads the vhost's DATEFORMAT
 *                              constant (defined in config.php).
 * @return string
 */
function smarty_modifier_datestamp($string, $format = null)
{
    if (!is_numeric($string)) {
        return '';
    }
    $timestamp = (int)$string;

    if ($format === null || $format === '') {
        $format = defined('DATEFORMAT') ? DATEFORMAT : '%Y-%m-%d %H:%M';
    }

    $offsetMinutes = isset($_SESSION['localtimezoneoffset'])
        ? (int)$_SESSION['localtimezoneoffset']
        : 0;
    $localTs = $timestamp + ($offsetMinutes * 60);

    // Per-user timezone offset string for %O. Pre-computed so the
    // token walker can reference it inline.
    $userOffsetValue = '';
    if ($offsetMinutes !== 0) {
        $sign = $offsetMinutes >= 0 ? '+' : '-';
        $abs = abs($offsetMinutes);
        $oh = str_pad((string)intdiv($abs, 60), 2, '0', STR_PAD_LEFT);
        $om = str_pad((string)($abs % 60), 2, '0', STR_PAD_LEFT);
        $userOffsetValue = sprintf('%s%02d:%02d', $sign, $oh, $om);
    }

    // strftime-token → PHP date() format. Tokens not in this map
    // fall back to a default translation where reasonable (e.g. %Y
    // → Y) or pass through strftime if no PHP equivalent exists.
    // See bbsengine6/handbook/specs/datestamp.md for the full table.
    $strftimeToDate = [
        // Year
        '%Y' => 'Y', '%y' => 'y',
        // Month
        '%m' => 'm', '%b' => 'M', '%B' => 'F',
        // Day
        '%d' => 'd',
        // %j is handled inline (PHP date('z') is 0-indexed,
        // strftime %j is 1-indexed).
        // Hour
        '%H' => 'H', '%I' => 'h', '%l' => 'g',
        // Minute/second
        '%M' => 'i', '%S' => 's',
        // AM/PM
        '%p' => 'A', '%P' => 'a',
        // Timezone (server-local; matches Python strftime semantics
        // since both languages use the server's local TZ for strftime).
        '%Z' => 'T',
        '%z' => 'O',
        '%:z' => 'P',
        // Day name
        '%a' => 'D', '%A' => 'l',
        // Literal %: strftime "%%" → "%"
        '%%' => '%',
    ];

    // Walk the format string character-by-character. Only sequences
    // beginning with '%' are tokens; bare letters and other chars
    // pass through literally. This matches Python's strftime behavior
    // and avoids PHP date()'s over-eager letter-tokenization.
    //
    // Some strftime tokens are multi-character (e.g. %:z for
    // "+HH:MM" offset). We try the longest known prefix first, then
    // fall back to the single-letter form.
    $knownTokens = array_keys($strftimeToDate);
    // Tokens we handle inline (not in the map).
    $inlineTokens = ['%%', '%j', '%O'];

    // Sort tokens by length descending so longer ones match first.
    $allTokens = array_merge($inlineTokens, $knownTokens);
    usort($allTokens, function ($a, $b) { return strlen($b) - strlen($a); });

    $result = '';
    $len = strlen($format);
    for ($i = 0; $i < $len; $i++) {
        $ch = $format[$i];
        if ($ch === '%' && $i + 1 < $len) {
            // Find the longest matching token at this position.
            $matched = null;
            foreach ($allTokens as $tok) {
                if (substr($format, $i, strlen($tok)) === $tok) {
                    $matched = $tok;
                    break;
                }
            }
            if ($matched !== null) {
                $i += strlen($matched) - 1;
                if ($matched === '%%') {
                    $result .= '%';
                } elseif ($matched === '%j') {
                    $result .= (string)((int)date('z', $localTs) + 1);
                } elseif ($matched === '%O') {
                    $result .= $userOffsetValue;
                } else {
                    $result .= date($strftimeToDate[$matched], $localTs);
                }
                continue;
            }
            // Unknown %X token: pass through verbatim (try single
            // char, fall back to %).
            if ($i + 1 < $len && ctype_alpha($format[$i + 1])) {
                $result .= '%' . $format[$i + 1];
                $i++;
            } else {
                $result .= '%';
            }
            continue;
        }
        $result .= $ch;
    }

    return $result;
}