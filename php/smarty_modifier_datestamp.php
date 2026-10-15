<?php

/**
 * \bbsengine6\smarty_modifier_datestamp — the canonical
 * |datestamp Smarty modifier function body.
 *
 * Both bbsengine6/smarty/modifier.datestamp.php and
 * zoid6/smarty/modifier.datestamp.php require this file so
 * the modifier is defined in exactly one place. The modifier
 * is a thin wrapper over \bbsengine6\util\datestamp() (the
 * canonical PHP date/time formatter) with a non-numeric-input
 * guard that returns empty string for invalid input.
 *
 * The body lives in bbsengine6/php/ (not bbsengine6/smarty/)
 * so both modifier files can use __DIR__-relative require
 * paths that resolve regardless of which Smarty plugin dir
 * the modifier loaded from:
 *
 *   bbsengine6/smarty/modifier.datestamp.php:
 *     __DIR__ . "/../php/smarty_modifier_datestamp.php"
 *
 *   zoid6/smarty/modifier.datestamp.php (assuming bbsengine6
 *   and zoid6 are sibling checkouts/Installs):
 *     __DIR__ . "/../../bbsengine6/php/smarty_modifier_datestamp.php"
 *
 * Spec: bbsengine6/handbook/specs/datestamp.md.
 *
 * @since 2026-10-15
 * @param string      $timestamp Unix epoch (integer or numeric string).
 *                                Non-numeric input renders as empty string.
 * @param string|null $format    Optional strftime format string.
 *                                See \bbsengine6\util\datestamp() for the
 *                                resolution chain (format arg → DATEFORMAT
 *                                → default).
 * @return string
 */
function smarty_modifier_datestamp($string, $format = null)
{
    if (!is_numeric($string)) {
        return '';
    }
    return \bbsengine6\util\datestamp((int)$string, $format);
}
