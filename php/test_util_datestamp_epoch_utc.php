<?php
/**
 * test_util_datestamp_epoch_utc.php — an epoch is a UTC instant (POSIX.1-2017 §4.16). The PHP counterpart of
 * py/tests/test_util_datestamp_epoch_utc.py: datestamp(epoch) gives the same UTC clock in every server zone.
 *
 * Usage:
 *   php test_util_datestamp_epoch_utc.php
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

const FMT = '%Y-%m-%d %H:%M:%S %Z';
const SERVER_ZONES = ['UTC', 'Europe/London', 'America/Chicago', 'America/New_York', 'Asia/Kolkata'];

foreach (SERVER_ZONES as $zone) {
    date_default_timezone_set($zone);
    check("epoch 0 in server zone $zone", datestamp(0, FMT), '1970-01-01 00:00:00 UTC');
}

date_default_timezone_set('America/Chicago');
check("int epoch 2026-03-08 08:00 UTC, server Chicago",
      datestamp(gmmktime(8, 0, 0, 3, 8, 2026), FMT), '2026-03-08 08:00:00 UTC');
check("float epoch keeps whole seconds", datestamp(59.9, FMT), '1970-01-01 00:00:59 UTC');
check("numeric string epoch is UTC", datestamp('0', FMT), '1970-01-01 00:00:00 UTC');
check("the server zone is restored after the call", date_default_timezone_get(), 'America/Chicago');

// A DateTimeInterface keeps its own zone (Python parity): 07:49 CST is printed as 07:49 CST, not converted to UTC.
// The server zone is UTC here, so a Chicago DateTime formatted in UTC would fail this check.
date_default_timezone_set('UTC');
$chicago = new \DateTime('2026-11-21 07:49:07', new \DateTimeZone('America/Chicago'));
check("an aware DateTime keeps its own zone under a UTC server zone", datestamp($chicago, FMT), '2026-11-21 07:49:07 CST');
check("the server zone is UTC after a DateTime call", date_default_timezone_get(), 'UTC');

echo "\n$pass passed, $fail failed\n";
exit($fail === 0 ? 0 : 1);
}
