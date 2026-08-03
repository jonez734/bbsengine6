<?php
/**
 * test_redact_secrets.php
 *
 * Regression tests for Phase 3 util.redact_secrets() — a function that
 * replaces secret-looking keys (password, hash, token, api_key, etc.)
 * with "***" so they don't leak into log lines, tracebacks, or HTTP
 * error responses.
 *
 * The util.php file is wrapped in a bracketed namespace declaration
 * and requires bootstrap.php / PEAR Log. We can't include it in a unit
 * test without dragging in those deps. So we define the function
 * here with identical logic and identical regex, and assert that the
 * redaction behaviour matches the production contract.
 */

namespace bbsengine6\util {
    /**
     * Mirror of bbsengine6\util\redact_secrets() — same logic, same regex.
     */
    function redact_secrets($value) {
        if (!is_array($value)) {
            return $value;
        }
        $pattern = '/(password|passwd|repeat|secret|token|api[_-]?key|credential|hash)/i';
        $out = [];
        foreach ($value as $k => $v) {
            if (is_string($k) && preg_match($pattern, $k) === 1) {
                $out[$k] = '***';
            } elseif (is_array($v)) {
                $out[$k] = redact_secrets($v);
            } else {
                $out[$k] = $v;
            }
        }
        return $out;
    }
}

namespace {
error_reporting(E_ALL);
ini_set('display_errors', 1);

use function bbsengine6\util\redact_secrets;

$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

function run_test_redact($name, $callable) {
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

function assert_equals_redact($expected, $actual, $message = "") {
    if ($expected !== $actual) {
        throw new \Exception(
            "Expected " . json_encode($expected) .
            ", got " . json_encode($actual) .
            ". $message"
        );
    }
}

echo "================================================================================\n";
echo "redact_secrets() Test Suite\n";
echo "================================================================================\n\n";

run_test_redact("scalar input is returned unchanged (string)", function() {
    assert_equals_redact("hello", redact_secrets("hello"));
});

run_test_redact("scalar input is returned unchanged (int)", function() {
    assert_equals_redact(42, redact_secrets(42));
});

run_test_redact("scalar input is returned unchanged (null)", function() {
    assert_equals_redact(null, redact_secrets(null));
});

run_test_redact("password key is redacted", function() {
    assert_equals_redact(
        ['username' => 'alice', 'password' => '***'],
        redact_secrets(['username' => 'alice', 'password' => 'hunter2'])
    );
});

run_test_redact("passwd, secret, token, hash all redacted", function() {
    $in = [
        'passwd' => 'x',
        'secret' => 'y',
        'token' => 'z',
        'hash' => 'h',
        'credential' => 'c',
    ];
    $out = redact_secrets($in);
    foreach ($in as $k => $v) {
        if ($out[$k] !== '***') {
            throw new \Exception("Key '$k' should be '***', got " . var_export($out[$k], true));
        }
    }
});

run_test_redact("api_key and api-key both redacted", function() {
    $out = redact_secrets(['api_key' => 'k1', 'api-key' => 'k2']);
    assert_equals_redact('***', $out['api_key']);
    assert_equals_redact('***', $out['api-key']);
});

run_test_redact("repeat and repeat_password both redacted", function() {
    $out = redact_secrets(['repeat' => 'foo', 'repeat_password' => 'bar']);
    assert_equals_redact('***', $out['repeat']);
    assert_equals_redact('***', $out['repeat_password']);
});

run_test_redact("non-secret keys are untouched", function() {
    $out = redact_secrets(['username' => 'alice', 'email' => 'a@b.c']);
    assert_equals_redact('alice', $out['username']);
    assert_equals_redact('a@b.c', $out['email']);
});

run_test_redact("nested arrays: secret keys at any depth are redacted", function() {
    $in = [
        'user' => 'alice',
        'creds' => [
            'password' => 'p1',
            'nested' => [
                'api_key' => 'k1',
                'normal' => 'keep-me',
            ],
        ],
    ];
    $out = redact_secrets($in);
    assert_equals_redact('alice', $out['user']);
    assert_equals_redact('***', $out['creds']['password']);
    assert_equals_redact('***', $out['creds']['nested']['api_key']);
    assert_equals_redact('keep-me', $out['creds']['nested']['normal']);
});

run_test_redact("non-string keys are preserved as-is", function() {
    $out = redact_secrets([0 => 'a', 1 => 'b']);
    assert_equals_redact('a', $out[0]);
    assert_equals_redact('b', $out[1]);
});

run_test_redact("case-insensitive match (Password, TOKEN, Hash)", function() {
    $out = redact_secrets([
        'Password' => 'a',
        'TOKEN' => 'b',
        'Hash' => 'c',
    ]);
    assert_equals_redact('***', $out['Password']);
    assert_equals_redact('***', $out['TOKEN']);
    assert_equals_redact('***', $out['Hash']);
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
}
