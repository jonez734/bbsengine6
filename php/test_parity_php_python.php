<?php
/**
 * test_parity_php_python.php — Cross-language byte-exact parity test.
 *
 * Reads the shared JSON fixture at
 * `bbsengine6/test_parity_php_python.json` and asserts that
 * `\bbsengine6\util\datestamp($epoch, $format)` produces the
 * expected output for every (epoch, format) case.
 *
 * The Python counterpart (`py/tests/test_parity_php_python.py`)
 * reads the same fixture and asserts the same expected output
 * from Python's `bbsengine6.util.datestamp()`. If the two
 * surfaces ever drift, one of the two test runners will fail.
 *
 * The fixture pins the test epoch to a specific UTC timestamp
 * (1760365800 = 2025-10-13 14:30:00 UTC) and uses only
 * TZ-independent format tokens (no `%Z`). The test pins
 * `date_default_timezone_set('UTC')` so PHP's `date()` reads
 * UTC offsets consistently regardless of the server's
 * configured timezone.
 *
 * @since 2026-10-15
 *
 * Usage:
 *   php bbsengine6/php/test_parity_php_python.php
 */

date_default_timezone_set('UTC');

require_once(__DIR__ . "/util.php");

$fixturePath = dirname(__DIR__) . "/test_parity_php_python.json";
if (!is_readable($fixturePath)) {
    fwrite(STDERR, "FATAL: fixture not readable at $fixturePath\n");
    exit(2);
}
$fixture = json_decode(file_get_contents($fixturePath), true);
if (!is_array($fixture) || empty($fixture[0]['cases'])) {
    fwrite(STDERR, "FATAL: fixture is malformed (expected array with at least one group)\n");
    exit(2);
}

$passed = 0;
$failed = 0;
$groupCount = count($fixture);

echo "=== datestamp() PHP/Python byte-exact parity test ===\n";
echo "Fixture: $fixturePath\n";
echo "Groups: $groupCount\n\n";

foreach ($fixture as $groupIdx => $group) {
    $epoch = $group['epoch'];
    $tz = $group['tz'] ?? 'UTC';
    echo "Group $groupIdx: epoch=$epoch ($tz), " . count($group['cases']) . " cases\n";
    foreach ($group['cases'] as $case) {
        $name = $case['name'] ?? '(no name)';
        $fmt = $case['format'];
        $expected = $case['expected'];
        $actual = \bbsengine6\util\datestamp($epoch, $fmt);
        if ($actual === $expected) {
            $passed++;
            printf("  \033[32m✓\033[0m PASS: %-30s [%s] -> [%s]\n", $name, $fmt, $actual);
        } else {
            $failed++;
            printf("  \033[31m✗\033[0m FAIL: %-30s [%s] expected [%s] got [%s]\n",
                $name, $fmt, $expected, $actual);
        }
    }
    echo "\n";
}

echo "=== Test Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    echo "\nFAIL: parity drift detected. Compare against Python:\n";
    echo "  cd bbsengine6/py && python3 -m pytest tests/test_parity_php_python.py -v\n";
    exit(1);
}

echo "\n✓ All PHP datestamp parity cases match the shared fixture.\n";
echo "  Python counterpart: bbsengine6/py/tests/test_parity_php_python.py\n";
exit(0);
