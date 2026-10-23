<?php
/**
 * test_datestamp_default_matches_python.php — with no format argument and no DATEFORMAT
 * constant, \bbsengine6\util\datestamp() uses the same default as Python's
 * bbsengine6.util.datestamp(): "%Y-%m-%d %I:%M%P %Z (%a)".
 *
 * Runs in its own process, so no DATEFORMAT constant is defined by an earlier test.
 *
 * Usage:
 *   php test_datestamp_default_matches_python.php
 */

declare(strict_types=1);

namespace { // global
require_once(__DIR__ . "/util.php");
}

namespace bbsengine6\util {

$failed = 0;
$expected_default = "%Y-%m-%d %I:%M%P %Z (%a)";

function check(string $name, bool $ok, string $detail = ""): void
{
    global $failed;
    if ($ok) {
        echo "PASS: $name\n";
    } else {
        echo "FAIL: $name" . ($detail !== "" ? " ($detail)" : "") . "\n";
        $failed++;
    }
}

// Pin the zone so the expected string is deterministic.
date_default_timezone_set('UTC');
$ts = 1729701530; // 2024-10-23 16:38:50 UTC

check("no DATEFORMAT constant is defined in this process", !defined('\config\DATEFORMAT') && !defined('DATEFORMAT'));

$no_format = datestamp($ts);
$explicit = datestamp($ts, $expected_default);
check("default (no format argument) equals the Python default",
      $no_format === $explicit,
      "got '$no_format', expected '$explicit'");
check("the default renders the Python layout",
      $no_format === "2024-10-23 04:38pm UTC (Wed)",
      "got '$no_format'");
check("empty format also falls back to the Python default",
      datestamp($ts, '') === $explicit);

if ($failed > 0) {
    exit(1);
}
echo "\nOK -- default format matches the Python default\n";
exit(0);

} // namespace bbsengine6\util
