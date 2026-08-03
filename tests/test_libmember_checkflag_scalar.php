<?php
/**
 * test_libmember_checkflag_scalar.php
 *
 * Regression test for Phase 3 libmember.php checkflag() hardening.
 *
 * Pre-Phase-3 the function called:
 *
 *     $value = $stmt->fetchColumn()["checkflag"];
 *
 * PDOStatement::fetchColumn() returns a scalar (the value of the first
 * column in the first row), not an associative array. Subscripting it
 * with ["checkflag"] raised a PHP warning ("Trying to access array
 * offset on value of type bool") and returned null, so checkflag()
 * always returned null and every flag check was effectively false.
 *
 * Phase 3 fixed this to:
 *
 *     $value = $stmt->fetchColumn();
 *
 * This test pins down the corrected behaviour by reading the source
 * file and asserting:
 *   1. The buggy `fetchColumn()["checkflag"]` pattern does NOT appear
 *      in non-comment code.
 *   2. The production function uses `fetchColumn()` with no subscript.
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);

$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

function run_test_cf($name, $callable) {
    global $tests_passed, $tests_failed, $test_results;
    try {
        $callable();
        $tests_passed++;
        $test_results[] = "PASS: $name";
        echo "  PASS: $name\n";
    } catch (\Exception $e) {
        $tests_failed++;
        $test_results[] = "FAIL: $name - " . $e->getMessage();
        echo "  FAIL: $name\n";
        echo "    Error: " . $e->getMessage() . "\n";
    }
}

$source_path = __DIR__ . "/../php/libmember.php";
$source = file_get_contents($source_path);

/**
 * Strip /* ... * / block comments so that commented-out legacy code
 * does not produce false positives.
 */
function strip_block_comments(string $src): string {
    return preg_replace('#/\*.*?\*/#s', '', $src);
}

echo "================================================================================\n";
echo "libmember.checkflag() scalar fetchColumn() Test Suite\n";
echo "================================================================================\n\n";

run_test_cf("source file exists", function() use ($source_path) {
    if (!file_exists($source_path)) {
        throw new \Exception("libmember.php not found at $source_path");
    }
});

run_test_cf("buggy fetchColumn()['checkflag'] is REMOVED (non-comment context)", function() use ($source) {
    $clean = strip_block_comments($source);
    $buggy = 'fetchColumn()["checkflag"]';
    if (strpos($clean, $buggy) !== false) {
        throw new \Exception(
            "Source still contains buggy '$buggy' outside comments — " .
            "should be fetchColumn() with no subscript"
        );
    }
});

run_test_cf("buggy fetch()['checkflag'] is also REMOVED from production code", function() use ($source) {
    $clean = strip_block_comments($source);
    $buggy = 'fetch()["checkflag"]';
    if (strpos($clean, $buggy) !== false) {
        throw new \Exception(
            "Source still contains '$buggy' in production code — " .
            "fetch() returns an array but the scalar-returning fetchColumn() is preferred"
        );
    }
});

run_test_cf("production checkflag() function exists and uses fetchColumn()", function() use ($source) {
    $clean = strip_block_comments($source);
    // Extract the checkflag function body using brace counting.
    if (preg_match('/function checkflag\s*\([^)]*\)\s*\{/', $clean, $m, PREG_OFFSET_CAPTURE) !== 1) {
        throw new \Exception("Could not find function checkflag()");
    }
    $start = $m[0][1] + strlen($m[0][0]);
    // Walk braces from $start to find the matching closing brace.
    $depth = 1;
    $i = $start;
    $len = strlen($clean);
    while ($i < $len && $depth > 0) {
        $ch = $clean[$i];
        if ($ch === '{') $depth++;
        elseif ($ch === '}') $depth--;
        $i++;
    }
    if ($depth !== 0) {
        throw new \Exception("Could not balance braces in checkflag() body");
    }
    $body = substr($clean, $start, $i - $start - 1);

    if (strpos($body, 'fetchColumn(') === false) {
        throw new \Exception(
            "checkflag() body does not call fetchColumn()\n---BODY---\n$body\n---END---"
        );
    }
    if (preg_match('/fetchColumn\s*\(\s*\)\s*\[[^\]]*\]/', $body)) {
        throw new \Exception(
            "checkflag() body subscripts fetchColumn() result — " .
            "fetchColumn returns a scalar, not an array"
        );
    }
});

run_test_cf("production checkflag() returns the scalar value directly", function() use ($source) {
    $clean = strip_block_comments($source);
    if (preg_match('/function checkflag\s*\([^)]*\)\s*\{/', $clean, $m, PREG_OFFSET_CAPTURE) !== 1) {
        throw new \Exception("Could not find function checkflag()");
    }
    $start = $m[0][1] + strlen($m[0][0]);
    $depth = 1;
    $i = $start;
    $len = strlen($clean);
    while ($i < $len && $depth > 0) {
        $ch = $clean[$i];
        if ($ch === '{') $depth++;
        elseif ($ch === '}') $depth--;
        $i++;
    }
    $body = substr($clean, $start, $i - $start - 1);

    if (!preg_match('/=\s*\$stmt->fetchColumn\(\)/', $body) &&
        !preg_match('/return\s+\$stmt->fetchColumn\(\)/', $body)) {
        throw new \Exception(
            "checkflag() body does not assign or return " .
            "\$stmt->fetchColumn() directly"
        );
    }
});

echo "\n";
echo "================================================================================\n";
echo "Test Results: " . ($tests_passed + $tests_failed) .
     " total, $tests_passed passed, $tests_failed failed\n";
echo "================================================================================\n";

if ($tests_failed > 0) {
    foreach ($test_results as $r) {
        if (strpos($r, "FAIL") !== false) echo "  $r\n";
    }
    exit(1);
}
exit(0);
