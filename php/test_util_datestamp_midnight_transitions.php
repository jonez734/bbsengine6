<?php
/**
 * test_util_datestamp_midnight_transitions.php — \bbsengine6\util\datestamp() where a DST switch
 * happens at local midnight. The PHP counterpart of
 * py/tests/test_util_datestamp_midnight_transitions.py: the same instants, the same expected output.
 *
 * Skipped midnight: the clock jumps 23:59:59 -> 01:00:00, so 00:00 never occurs that day.
 * Repeated midnight: the clock goes back 00:59:59 -> 00:00:00, so 00:00 occurs twice.
 *
 * The zone is set with date_default_timezone_set() before each case, because the PHP walker
 * formats the epoch in the server zone. Instants are epochs, so the result does not depend on
 * which zone the caller was in.
 *
 * Usage:
 *   php test_util_datestamp_midnight_transitions.php
 */

declare(strict_types=1);

namespace {
require_once(__DIR__ . "/util.php");
}

namespace bbsengine6\util {

use function bbsengine6\util\datestamp;

$pass = 0;
$fail = 0;

function check(string $label, string $got, string $want): void
{
    global $pass, $fail;
    if ($got === $want) {
        $pass++;
        echo "ok   $label\n";
    } else {
        $fail++;
        echo "FAIL $label\n     got:  '$got'\n     want: '$want'\n";
    }
}

// The fixed format matches the Python tests: 24-hour clock, the zone abbreviation.
const FMT = '%Y-%m-%d %H:%M:%S %Z';

/** Epoch of a UTC wall time, so each case names its instant the same way the Python tests do. */
function utc(int $y, int $mo, int $d, int $h, int $mi, int $s = 0): int
{
    return gmmktime($h, $mi, $s, $mo, $d, $y);
}

/** Format $epoch as the local clock of $zone, with the zone set for the call and restored after. */
function at(string $zone, int $epoch): string
{
    $saved = date_default_timezone_get();
    date_default_timezone_set($zone);
    try {
        return datestamp($epoch, FMT);
    } finally {
        date_default_timezone_set($saved);
    }
}

echo "--- skipped midnight ---\n";
$t = utc(2026, 3, 8, 5, 0);
check("Havana 2026-03-08 one second before the jump", at('America/Havana', $t - 1), '2026-03-07 23:59:59 CST');
check("Havana 2026-03-08 at the jump", at('America/Havana', $t), '2026-03-08 01:00:00 CDT');

$t = utc(2026, 9, 6, 4, 0);
check("Santiago 2026-09-06 one second before the jump", at('America/Santiago', $t - 1), '2026-09-05 23:59:59 -04');
check("Santiago 2026-09-06 at the jump", at('America/Santiago', $t), '2026-09-06 01:00:00 -03');

echo "--- repeated midnight ---\n";
$t = utc(2027, 11, 7, 5, 0);
check("Havana 2027-11-07 one second before the repeat", at('America/Havana', $t - 1), '2027-11-07 00:59:59 CDT');
check("Havana 2027-11-07 at the repeat", at('America/Havana', $t), '2027-11-07 00:00:00 CST');

$t = utc(2015, 10, 22, 22, 0);
check("Gaza 2015-10-23 one second before the repeat", at('Asia/Gaza', $t - 1), '2015-10-23 00:59:59 EEST');
check("Gaza 2015-10-23 at the repeat", at('Asia/Gaza', $t), '2015-10-23 00:00:00 EET');

echo "--- repeated midnight is told apart by the zone name, not only the clock ---\n";
check("Havana 2027-11-07 first 00:30 is CDT", at('America/Havana', utc(2027, 11, 7, 4, 30)), '2027-11-07 00:30:00 CDT');
check("Havana 2027-11-07 second 00:30 is CST", at('America/Havana', utc(2027, 11, 7, 5, 30)), '2027-11-07 00:30:00 CST');

echo "--- a fold-ignoring formatter is distinguishable from the real one ---\n";
// A formatter that uses the offset at the start of the local day gives 01:30 CDT for the second 00:30; the real
// formatter gives 00:30 CST. This case fails if datestamp ever formats with the day's first offset.
$second = utc(2027, 11, 7, 5, 30);
$startOfDayOffset = (int)date('Z', strtotime(
    (function () use ($second) { date_default_timezone_set('America/Havana'); return date('Y-m-d 00:00:00', $second); })()
));
$mutant = gmdate('Y-m-d H:i:s', $second + $startOfDayOffset) . ' CDT';
check("real formatter differs from the fold-ignoring mutant at the repeated 00:30",
      at('America/Havana', $second) === $mutant ? 'same' : 'different', 'different');

echo "\n$pass passed, $fail failed\n";
exit($fail === 0 ? 0 : 1);
}
