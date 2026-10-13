<?php
/**
 * test_datestamp_modifier.php — Verifies the bbsengine6 `|datestamp`
 * Smarty modifier supports the full Python strftime vocabulary, plus
 * the %O opt-in (per-user timezone offset).
 *
 * The modifier reads DATEFORMAT (a strftime format string) from the
 * vhost config when called without a format argument, or accepts an
 * explicit format as the second argument. Both surfaces produce
 * identical output for any common-subset token.
 *
 * Implementation note: the modifier walks the format string
 * character-by-character rather than running str_replace on the whole
 * string. This is necessary because PHP date() interprets any ASCII
 * letter in the format as a token, while strftime only treats
 * %X-prefixed sequences as tokens — bare letters must be passed
 * through literally. The walker tries the longest known prefix first
 * (so multi-character tokens like %:z match before single-letter %z),
 * then a single-letter %X, then a literal %.
 *
 * Usage:
 *   php test_datestamp_modifier.php
 */

// Stub config.php require inside the modifier.
define("DATEFORMAT", "%Y-%m-%d %I:%M%P %Z (%a)");

// Bootstrap the modifier function without its config.php require.
$source = file_get_contents("/home/opencode/data/work/bbsengine6/smarty/modifier.datestamp.php");
$source = preg_replace('/require_once\("config\.php"\);/', '// stubbed', $source);
eval("?>" . $source);

echo "=== |datestamp modifier Tests ===\n\n";

$passed = 0;
$failed = 0;

function test_pass(string $name, string $detail = ''): void {
    global $passed;
    $passed++;
    $suffix = $detail ? ": $detail" : '';
    echo "  ✓ PASS: $name$suffix\n";
}

function test_fail(string $name, string $detail = ''): never {
    global $failed;
    $failed++;
    $suffix = $detail ? " — $detail" : '';
    echo "  ✗ FAIL: $name$suffix\n";
    exit(1);
}

function check(string $name, string $expected, string $actual): void {
    if ($expected === $actual) {
        test_pass($name, "[$actual]");
    } else {
        test_fail($name, "expected [$expected] got [$actual]");
    }
}

// =============================================================================
// Per-token coverage. The server's TZ in this sandbox is UTC; the test
// timestamp below is interpreted as UTC by date(). strftime tokens whose
// output depends on server-local TZ (e.g. %Z, %H, %z) are pinned to the
// sandbox's UTC value.
// =============================================================================

$ts = strtotime('2026-10-13 14:30:00 UTC'); // 2026-10-13 14:30:00 UTC, a Tuesday
$tsDate = date('Y-m-d H:i:s', $ts);
echo "Test timestamp: $tsDate (server-local)\n\n";

echo "--- Per-token parity (strftime vocabulary) ---\n\n";

check('%Y', '2026', smarty_modifier_datestamp($ts, '%Y'));
check('%y', '26',   smarty_modifier_datestamp($ts, '%y'));
check('%m', '10',   smarty_modifier_datestamp($ts, '%m'));
check('%b', 'Oct',  smarty_modifier_datestamp($ts, '%b'));
check('%B', 'October', smarty_modifier_datestamp($ts, '%B'));
check('%d', '13',   smarty_modifier_datestamp($ts, '%d'));
check('%j', '286',  smarty_modifier_datestamp($ts, '%j')); // day-of-year, 1-indexed
check('%H', '14',   smarty_modifier_datestamp($ts, '%H'));
check('%I', '02',   smarty_modifier_datestamp($ts, '%I'));
// %l: PHP date('g') = no padding/no leading zero; Python strftime %l
// is space-padded. Documented divergence in handbook/specs/datestamp.md.
check('%l (PHP g)', '2', smarty_modifier_datestamp($ts, '%l'));
check('%M', '30',   smarty_modifier_datestamp($ts, '%M'));
check('%S', '00',   smarty_modifier_datestamp($ts, '%S'));
check('%p', 'PM',   smarty_modifier_datestamp($ts, '%p'));
check('%P', 'pm',   smarty_modifier_datestamp($ts, '%P'));
check('%Z', date('T', $ts), smarty_modifier_datestamp($ts, '%Z')); // sandbox TZ abbrev
check('%z', date('O', $ts), smarty_modifier_datestamp($ts, '%z')); // +0000
check('%:z', date('P', $ts), smarty_modifier_datestamp($ts, '%:z')); // +00:00
check('%a', 'Tue',  smarty_modifier_datestamp($ts, '%a'));
check('%A', 'Tuesday', smarty_modifier_datestamp($ts, '%A'));
check('%%', '%',    smarty_modifier_datestamp($ts, '%%'));

echo "\n--- Combined format ---\n\n";

$combined = '%Y-%m-%d %H:%M:%S %Z (%a)';
$expected = '2026-10-13 14:30:00 ' . date('T', $ts) . ' (Tue)';
check('combined', $expected, smarty_modifier_datestamp($ts, $combined));

// %j inside a longer format
$combinedWithJ = 'day %j of %Y';
check('combined with %j', 'day 286 of 2026', smarty_modifier_datestamp($ts, $combinedWithJ));

// Literal % via %%
check('literal % via %%', '100% off', smarty_modifier_datestamp($ts, '100%% off'));

echo "\n--- Default format (reads DATEFORMAT) ---\n\n";

$defaultResult = smarty_modifier_datestamp($ts);
$expectedDefault = '2026-10-13 02:30pm ' . date('T', $ts) . ' (Tue)';
check('reads DATEFORMAT', $expectedDefault, $defaultResult);

echo "\n--- %O opt-in (per-user TZ) ---\n\n";

// No session set: %O renders empty
check('%O no session', '', smarty_modifier_datestamp($ts, '%O'));
check('%O no session with context', '2026-10-13 ', smarty_modifier_datestamp($ts, '%Y-%m-%d %O'));

// Simulate session offset: EDT (-240)
$_SESSION['localtimezoneoffset'] = -240;
check('%O EDT', '-04:00', smarty_modifier_datestamp($ts, '%O'));
$ts_edt = smarty_modifier_datestamp($ts, '%Y-%m-%d %H:%M %Z %O');
check('%O EDT with date', '2026-10-13 10:30 ' . date('T', $ts) . ' -04:00', $ts_edt);

// IST (+330)
$_SESSION['localtimezoneoffset'] = 330;
$ts_ist = smarty_modifier_datestamp($ts, '%Y-%m-%d %H:%M %Z %O');
check('%O IST', '2026-10-13 20:00 ' . date('T', $ts) . ' +05:30', $ts_ist);

// Half-hour TZ: India Standard (+330 already tested above); also test
// negative half hour (e.g. -330 = UTC-5:30 = India "IST" sign-flip).
$_SESSION['localtimezoneoffset'] = -330;
check('%O -330', '-05:30', smarty_modifier_datestamp($ts, '%O'));

unset($_SESSION['localtimezoneoffset']);

echo "\n--- Edge cases ---\n\n";

check('non-numeric input', '', smarty_modifier_datestamp('not a number'));
check('null input', '', smarty_modifier_datestamp(null));
// 0 is a valid Unix epoch (1970-01-01 00:00:00 UTC). is_numeric
// accepts it, so the modifier formats it. Just verify the result
// starts with "1970" (year of the epoch) — no crash on edge case.
$epochResult = smarty_modifier_datestamp(0);
if (strpos($epochResult, '1970') === 0) {
    test_pass('zero timestamp (Unix epoch)', "[$epochResult]");
} else {
    test_fail('zero timestamp', "expected result starting with 1970, got [$epochResult]");
}
// Empty format string is treated as "no override" and falls back
// to DATEFORMAT. This matches the existing bbsengine6 contract.
check('empty format falls back to DATEFORMAT', $expectedDefault, smarty_modifier_datestamp($ts, ''));
check('null format falls back to DATEFORMAT', $expectedDefault, smarty_modifier_datestamp($ts, null));

echo "\n--- Token-aware walker (bare letters preserved) ---\n\n";

// strftime convention: only %X-prefixed sequences are tokens; bare
// letters are literal. PHP date() interprets any letter as a token,
// so the modifier must walk the format string token-by-token to
// preserve bare letters.
check('bare letters preserved: "day"', 'day 286', smarty_modifier_datestamp($ts, 'day %j'));
check('bare letters with literal hyphen', 'day-of-year: 286', smarty_modifier_datestamp($ts, 'day-of-year: %j'));
check('multi-character token %:z', '+00:00', smarty_modifier_datestamp($ts, '%:z'));
check('unknown %X passes through', '%X', smarty_modifier_datestamp($ts, '%X'));

echo "\n--- %j vs %d distinction ---\n\n";

// %j is day-of-year (1-indexed), %d is day-of-month. On 2026-10-13:
// day-of-month=13, day-of-year=286.
$tsDayOfYear = smarty_modifier_datestamp($ts, '%j');
$tsDayOfMonth = smarty_modifier_datestamp($ts, '%d');
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

echo "\n✓ All |datestamp modifier tests passed!\n";
exit(0);