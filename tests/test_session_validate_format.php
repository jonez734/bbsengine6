<?php
/**
 * test_session_validate_format.php
 *
 * Regression tests for Phase 3 session.php hardening.
 *
 * The pre-Phase-3 validate() function called the database with whatever
 * $sessionid was passed in. Phase 3 added a format pre-check using the
 * regex /^[A-Za-z0-9,\-]{1,128}$/ — malformed ids (e.g. SQL injection
 * attempts, very long strings, control chars) are rejected before they
 * reach the DB layer.
 *
 * The session.php file requires bootstrap.php, database.php, etc. which
 * are not available in a unit test. We mirror the regex-only validation
 * here and assert its behaviour against representative inputs.
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);

$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

function run_test_validate($name, $callable) {
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

/**
 * Mirror of bbsengine6\session\validate() — same regex pre-check.
 * Returns true if format is acceptable, false if rejected.
 */
function validate_session_id_format($sessionid) {
    if (!is_string($sessionid)) {
        return false;
    }
    return preg_match('/^[A-Za-z0-9,\-]{1,128}$/', $sessionid) === 1;
}

echo "================================================================================\n";
echo "session.validate() format pre-check Test Suite\n";
echo "================================================================================\n\n";

run_test_validate("alphanumeric id is valid", function() {
    if (!validate_session_id_format("abc123XYZ")) {
        throw new \Exception("alphanumeric id should be valid");
    }
});

run_test_validate("id with commas and dashes is valid", function() {
    if (!validate_session_id_format("abc-123,xyz")) {
        throw new \Exception("id with commas and dashes should be valid");
    }
});

run_test_validate("single char is valid", function() {
    if (!validate_session_id_format("a")) {
        throw new \Exception("single-char id should be valid (boundary)");
    }
});

run_test_validate("128-char id is valid (max boundary)", function() {
    $id = str_repeat("a", 128);
    if (!validate_session_id_format($id)) {
        throw new \Exception("128-char id should be valid (max boundary)");
    }
});

run_test_validate("129-char id is invalid (over max)", function() {
    $id = str_repeat("a", 129);
    if (validate_session_id_format($id)) {
        throw new \Exception("129-char id should be invalid (over max boundary)");
    }
});

run_test_validate("empty string is invalid", function() {
    if (validate_session_id_format("")) {
        throw new \Exception("empty string should be invalid");
    }
});

run_test_validate("non-string input is invalid (int)", function() {
    if (validate_session_id_format(42)) {
        throw new \Exception("int input should be invalid");
    }
});

run_test_validate("non-string input is invalid (null)", function() {
    if (validate_session_id_format(null)) {
        throw new \Exception("null input should be invalid");
    }
});

run_test_validate("non-string input is invalid (array)", function() {
    if (validate_session_id_format(["abc"])) {
        throw new \Exception("array input should be invalid");
    }
});

run_test_validate("id with spaces is invalid", function() {
    if (validate_session_id_format("abc 123")) {
        throw new \Exception("id with spaces should be invalid");
    }
});

run_test_validate("id with single quote is invalid (SQL injection attempt)", function() {
    if (validate_session_id_format("abc' OR 1=1 --")) {
        throw new \Exception("SQL-injection-style id should be invalid");
    }
});

run_test_validate("id with semicolon is invalid", function() {
    if (validate_session_id_format("abc;DROP TABLE")) {
        throw new \Exception("id with semicolon should be invalid");
    }
});

run_test_validate("id with newlines is invalid", function() {
    if (validate_session_id_format("abc\nxyz")) {
        throw new \Exception("id with newlines should be invalid");
    }
});

run_test_validate("id with control chars is invalid", function() {
    if (validate_session_id_format("abc\x00xyz")) {
        throw new \Exception("id with NUL byte should be invalid");
    }
});

run_test_validate("id with slash is invalid (path traversal attempt)", function() {
    if (validate_session_id_format("../../../etc/passwd")) {
        throw new \Exception("path-traversal-style id should be invalid");
    }
});

run_test_validate("id with curly brace is invalid", function() {
    if (validate_session_id_format("{evil}")) {
        throw new \Exception("id with curly braces should be invalid");
    }
});

run_test_validate("typical PHP session id format is valid", function() {
    // PHP's session_create_id produces base64-ish strings.
    $sid = "k7i3dqmcr4s2lpf5n8a9b6t1uv0xyz";
    if (!validate_session_id_format($sid)) {
        throw new \Exception("typical PHP session id should be valid");
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
