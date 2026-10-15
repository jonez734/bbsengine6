<?php
/**
 * test_util_datestamp.php — Verifies \bbsengine6\util\datestamp()
 * (the canonical PHP date/time formatter) matches the Python
 * `bbsengine6.util.datestamp()` contract documented at
 * bbsengine6/handbook/specs/datestamp.md.
 *
 * The Smarty `|datestamp` modifier (bbsengine6/smarty/
 * modifier.datestamp.php and zoid6/smarty/modifier.datestamp.php)
 * is a thin wrapper that calls this function; this test exercises
 * the function directly.
 *
 * Usage:
 *   php test_util_datestamp.php
 */

declare(strict_types=1);

// Load util.php in the global namespace context (where require_once
// is allowed) so the namespaced functions in bbsengine6\util are
// declared before we enter the namespaced test body. util.php
// itself declares `namespace bbsengine6\util;`, so the functions
// land in that namespace regardless of the caller's namespace.
namespace { // global
require_once(__DIR__ . "/util.php");
}

namespace bbsengine6\util {

use function bbsengine6\util\datestamp;

$passed = 0;
$failed = 0;

function test_pass(string $name, string $detail = ''): void {
    global $passed;
    $passed++;
    $suffix = $detail !== '' ? ": $detail" : '';
    echo "  PASS: $name$suffix\n";
}

function test_fail(string $name, string $detail = ''): never {
    global $failed;
    $failed++;
    $suffix = $detail !== '' ? " -- $detail" : '';
    echo "  FAIL: $name$suffix\n";
    exit(1);
}

function check(string $name, string $expected, string $actual): void {
    if ($expected === $actual) {
        test_pass($name, $actual);
    } else {
        test_fail($name, "expected [$expected] got [$actual]");
    }
}

// Server TZ is whatever PHP defaults to (UTC in CI). We assert
// against date()-rendered values for tokens that depend on server
// TZ (%H, %I, %l, %Z, %z, %:z) so the test is sandbox-portable.
$ts = strtotime('2026-10-13 14:30:00 UTC');

echo "=== \\bbsengine6\\util\\datestamp() Tests ===\n\n";

// =============================================================================
// 1. Type-coercion of $t: int, float, null, string, DateTimeInterface.
// =============================================================================

echo "--- 1. type coercion of the first arg ---\n\n";

// null → current time. Just verify it returns a non-empty string
// matching the default format shape.
$out = datestamp();
if (!is_string($out) || $out === '') {
    test_fail("null \$t returns non-empty string", "got [$out]");
}
test_pass("null \$t returns non-empty string", "[$out]");

// int $t
check('int $t',
      '2026',
      substr(datestamp($ts, '%Y'), 0, 4));

// float $t (e.g. 1760400000.5 — fractional seconds are ignored by
// PHP's date() but accepted by the signature).
$tsFloat = (float)$ts + 0.5;
check('float $t',
      datestamp($ts, '%Y-%m-%d %H:%M'),
      datestamp($tsFloat, '%Y-%m-%d %H:%M'));

// numeric-string $t (matches the Smarty modifier's contract — the
// modifier accepts "string" input but only when is_numeric).
check('numeric-string $t (integer)',
      datestamp($ts, '%Y-%m-%d'),
      datestamp((string)$ts, '%Y-%m-%d'));

// non-numeric string $t → "" (graceful failure, matches Smarty
// modifier's `is_numeric` guard).
check('non-numeric string $t returns ""',
      '',
      datestamp('not a number', '%Y-%m-%d'));

// DateTimeInterface
$dt = new \DateTimeImmutable('@' . $ts);
check('DateTimeInterface $t',
      datestamp($ts, '%Y-%m-%d %H:%M'),
      datestamp($dt, '%Y-%m-%d %H:%M'));

// =============================================================================
// 2. Format resolution: explicit arg, null/empty fallback, \config\
//    namespaced DATEFORMAT, bare DATEFORMAT.
// =============================================================================

echo "\n--- 2. format resolution ---\n\n";

// Explicit format
check('explicit format %Y', '2026', datestamp($ts, '%Y'));
check('explicit format %Y-%m-%d', '2026-10-13', datestamp($ts, '%Y-%m-%d'));

// Empty/null format → falls back to DATEFORMAT. The test does NOT
// define DATEFORMAT; util.php's fallback chain produces
// "%Y-%m-%d %H:%M".
check('null format falls back to default',
      '2026-10-13 14:30',
      datestamp($ts, null));
check('empty format falls back to default',
      '2026-10-13 14:30',
      datestamp($ts, ''));

// Bare DATEFORMAT in the global namespace (define before testing).
if (!defined('DATEFORMAT')) {
    define('DATEFORMAT', '%Y/%m/%d');
}
check('bare DATEFORMAT fallback',
      '2026/10/13',
      datestamp($ts));

// \config\DATEFORMAT in the config namespace (defined AFTER the
// bare form so it wins the walker lookup). The walker checks
// \config\ first, then bare.
if (!defined('config\\DATEFORMAT')) {
    define('config\\DATEFORMAT', '%d-%b-%Y');
}
check('\\config\\DATEFORMAT wins over bare DATEFORMAT',
      '13-Oct-2026',
      datestamp($ts));

// =============================================================================
// 3. Strftime vocabulary — the token-aware walker. Same per-token
//    coverage as bbsengine6/php/test_datestamp_modifier.php, but
//    exercised through the canonical helper.
// =============================================================================

echo "\n--- 3. strftime vocabulary ---\n\n";

check('%Y', '2026', datestamp($ts, '%Y'));
check('%y', '26',   datestamp($ts, '%y'));
check('%m', '10',   datestamp($ts, '%m'));
check('%b', 'Oct',  datestamp($ts, '%b'));
check('%B', 'October', datestamp($ts, '%B'));
check('%d', '13',   datestamp($ts, '%d'));
check('%j', '286',  datestamp($ts, '%j'));
check('%H', '14',   datestamp($ts, '%H'));
check('%I', '02',   datestamp($ts, '%I'));
// %l: PHP date('g') returns unpadded ('2'); Python strftime %l
// returns space-padded (' 2'). The walker now space-pads to match
// Python byte-exactly. See bbsengine6/handbook/specs/datestamp.md
// "Byte-exact parity" section.
check('%l (strftime-padded, byte-exact with Python)', ' 2', datestamp($ts, '%l'));
check('%M', '30',   datestamp($ts, '%M'));
check('%S', '00',   datestamp($ts, '%S'));
check('%p', 'PM',   datestamp($ts, '%p'));
check('%P', 'pm',   datestamp($ts, '%P'));
check('%Z', date('T', $ts), datestamp($ts, '%Z'));
check('%z', date('O', $ts), datestamp($ts, '%z'));
check('%:z', date('P', $ts), datestamp($ts, '%:z'));
check('%a', 'Tue',  datestamp($ts, '%a'));
check('%A', 'Tuesday', datestamp($ts, '%A'));
check('%%', '%',    datestamp($ts, '%%'));

echo "\n--- 4. combined formats ---\n\n";

$combined = '%Y-%m-%d %H:%M:%S %Z (%a)';
$expected = '2026-10-13 14:30:00 ' . date('T', $ts) . ' (Tue)';
check('combined', $expected, datestamp($ts, $combined));

$combinedWithJ = 'day %j of %Y';
check('combined with %j', 'day 286 of 2026', datestamp($ts, $combinedWithJ));

check('literal % via %%', '100% off', datestamp($ts, '100%% off'));

echo "\n--- 5. %O opt-in (per-user TZ) ---\n\n";

// No session offset: %O renders empty
check('%O no session', '', datestamp($ts, '%O'));
check('%O no session with context', '2026-10-13 ', datestamp($ts, '%Y-%m-%d %O'));

// Simulate session offset: EDT (-240). Must use a real session
// (datestamp reads $_SESSION superglobal).
$_SESSION['localtimezoneoffset'] = -240;
check('%O EDT', '-04:00', datestamp($ts, '%O'));

$ts_edt = datestamp($ts, '%Y-%m-%d %H:%M %Z %O');
check('%O EDT with date',
      '2026-10-13 10:30 ' . date('T', $ts) . ' -04:00',
      $ts_edt);

$_SESSION['localtimezoneoffset'] = 330;
$ts_ist = datestamp($ts, '%Y-%m-%d %H:%M %Z %O');
check('%O IST',
      '2026-10-13 20:00 ' . date('T', $ts) . ' +05:30',
      $ts_ist);

$_SESSION['localtimezoneoffset'] = -330;
check('%O -330', '-05:30', datestamp($ts, '%O'));

unset($_SESSION['localtimezoneoffset']);

echo "\n--- 7. token-aware walker behavior ---\n\n";

check('bare letters preserved: "day"', 'day 286', datestamp($ts, 'day %j'));
check('bare letters with literal hyphen', 'day-of-year: 286', datestamp($ts, 'day-of-year: %j'));
check('multi-character token %:z', '+00:00', datestamp($ts, '%:z'));
check('unknown %X passes through', '%X', datestamp($ts, '%X'));

echo "\n--- 8. %j vs %d distinction ---\n\n";

$tsDayOfYear = datestamp($ts, '%j');
$tsDayOfMonth = datestamp($ts, '%d');
if ($tsDayOfYear === $tsDayOfMonth) {
    test_fail('j vs d should differ on day 13 of year', "%j=$tsDayOfYear, %d=$tsDayOfMonth");
}
test_pass('j vs d values differ when expected', "%j=$tsDayOfYear (day-of-year) %d=$tsDayOfMonth (day-of-month)");

echo "\n=== Test Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\nOK -- All \\bbsengine6\\util\\datestamp() tests passed!\n";
exit(0);

} // namespace bbsengine6\util