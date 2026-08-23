<?php
/**
 * test_libpassword.php
 *
 * Unit tests for bbsengine6\password — the PHP-side replacement for
 * the PG crypt()/gen_salt('bf') round-trip in libmember.php.
 *
 * Pins:
 *   - hash_password() emits $2y$06$... length 60 (matches Python
 *     bbsengine6.util._BCRYPT_ROUNDS=6 and PG gen_salt('bf') default).
 *   - verify_password() round-trips against its own hash (true) and
 *     rejects wrong plaintext (false). Constant-time via
 *     password_verify().
 *   - is_healthy_hash() / needs_rehash() agree with the Python
 *     PasswordHashAudit structural flags.
 *   - classify_hash() recognises bcrypt vs MD5-crypt vs other.
 *
 * No database required.
 */

error_reporting(E_ALL);
ini_set("display_errors", 1);

require_once __DIR__ . "/../../php/libpassword.php";

$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

function run_test_pw($name, $callable) {
    global $tests_passed, $tests_failed, $test_results;
    try {
        $callable();
        $tests_passed++;
        $test_results[] = "PASS: $name";
        echo "  PASS: $name\n";
    } catch (\Throwable $e) {
        $tests_failed++;
        $test_results[] = "FAIL: $name - " . $e->getMessage();
        echo "  FAIL: $name\n";
        echo "    Error: " . $e->getMessage() . "\n";
    }
}

function assert_pw($expected, $actual, $label) {
    if ($expected !== $actual) {
        throw new \Exception(
            "$label: expected " . var_export($expected, true) .
            " got " . var_export($actual, true)
        );
    }
}

echo "================================================================================\n";
echo "bbsengine6\\password unit tests\n";
echo "================================================================================\n\n";

run_test_pw("hash_password produces $2y$06$... length 60", function() {
    $h = \bbsengine6\password\hash_password("hunter2");
    if (strlen($h) !== 60) {
        throw new \Exception("length=" . strlen($h) . " (want 60)");
    }
    if (strncmp($h, "\$2y\$06\$", 7) !== 0) {
        throw new \Exception("prefix mismatch: $h");
    }
});

run_test_pw("hash_password produces unique salts across calls", function() {
    $a = \bbsengine6\password\hash_password("same-plaintext");
    $b = \bbsengine6\password\hash_password("same-plaintext");
    if ($a === $b) {
        throw new \Exception("two hashes of same plaintext were identical");
    }
});

run_test_pw("hash_password rejects empty plaintext", function() {
    $threw = false;
    try {
        \bbsengine6\password\hash_password("");
    } catch (\InvalidArgumentException $e) {
        $threw = true;
    }
    if (!$threw) {
        throw new \Exception("empty plaintext did not throw");
    }
});

run_test_pw("verify_password round-trips matching plaintext", function() {
    $h = \bbsengine6\password\hash_password("correct-horse-battery-staple");
    if (!\bbsengine6\password\verify_password("correct-horse-battery-staple", $h)) {
        throw new \Exception("verify_password returned false for matching plaintext");
    }
});

run_test_pw("verify_password rejects mismatched plaintext", function() {
    $h = \bbsengine6\password\hash_password("correct-horse-battery-staple");
    if (\bbsengine6\password\verify_password("wrong-plaintext", $h)) {
        throw new \Exception("verify_password returned true for wrong plaintext");
    }
});

run_test_pw("verify_password returns false (not throws) on empty input", function() {
    $h = \bbsengine6\password\hash_password("anything");
    $r1 = \bbsengine6\password\verify_password("", $h);
    $r2 = \bbsengine6\password\verify_password("anything", "");
    if ($r1 !== false || $r2 !== false) {
        throw new \Exception("expected false on empty input");
    }
});

run_test_pw("is_healthy_hash accepts $2a$/$2b$/$2x$/$2y$ at length 60", function() {
    $valid = [
        '$2a$06$' . str_repeat("a", 53),
        '$2b$06$' . str_repeat("b", 53),
        '$2x$06$' . str_repeat("c", 53),
        '$2y$06$' . str_repeat("d", 53),
    ];
    foreach ($valid as $h) {
        if (!\bbsengine6\password\is_healthy_hash($h)) {
            throw new \Exception("rejected healthy hash: $h");
        }
    }
});

run_test_pw("is_healthy_hash rejects MD5-crypt, empty, null, wrong length", function() {
    $bad = [
        '$1$abc$' . str_repeat("x", 30),   // MD5-crypt
        '',                                  // empty
        null,                                // null
        '$2y$06$short',                      // wrong length
        '$5$xxxxxxxxxxxxxxxxxxxxxx',         // sha256-crypt prefix
        'plaintext-password',                // not a hash at all
    ];
    foreach ($bad as $h) {
        if (\bbsengine6\password\is_healthy_hash($h)) {
            throw new \Exception("accepted unhealthy value: " . var_export($h, true));
        }
    }
});

run_test_pw("needs_rehash inverts is_healthy_hash", function() {
    $cases = [
        ['$2y$06$' . str_repeat("a", 53), false],
        ['$1$abc$' . str_repeat("x", 30), true],
        ['',                              true],
        [null,                            true],
        ['$2y$06$short',                  true],
        ['plaintext',                     true],
    ];
    foreach ($cases as [$stored, $want]) {
        $got = \bbsengine6\password\needs_rehash($stored);
        if ($got !== $want) {
            throw new \Exception(
                "needs_rehash(" . var_export($stored, true) .
                ") = " . var_export($got, true) .
                " want " . var_export($want, true)
            );
        }
    }
});

run_test_pw("classify_hash recognises bcrypt, md5crypt, other, empty, null", function() {
    $cases = [
        [null,                                                "null"],
        ['',                                                  "empty"],
        ['$2y$06$' . str_repeat("a", 53),                     "bcrypt"],
        ['$2b$06$' . str_repeat("b", 53),                     "bcrypt"],
        ['$1$abc$' . str_repeat("x", 30),                     "md5crypt"],
        ['plaintext',                                         "other"],
        ['$5$short',                                          "other"],
    ];
    foreach ($cases as [$stored, $want]) {
        $got = \bbsengine6\password\classify_hash($stored);
        if ($got !== $want) {
            throw new \Exception(
                "classify_hash(" . var_export($stored, true) .
                ") = $got want $want"
            );
        }
    }
});

run_test_pw("BBSENGINE_BCRYPT_COST is 6 (matches Python and PG)", function() {
    if (\BBSENGINE_BCRYPT_COST !== 6) {
        throw new \Exception(
            "BBSENGINE_BCRYPT_COST=" . \BBSENGINE_BCRYPT_COST .
            " want 6 (matches Python _BCRYPT_ROUNDS=6 and PG gen_salt('bf') default)"
        );
    }
});

run_test_pw("BCRYPT_HASH_LENGTH is 60", function() {
    if (\bbsengine6\password\BCRYPT_HASH_LENGTH !== 60) {
        throw new \Exception("BCRYPT_HASH_LENGTH=" . \bbsengine6\password\BCRYPT_HASH_LENGTH . " want 60");
    }
});

run_test_pw("verify_password handles long-byte UTF-8 plaintext", function() {
    $pw = "pâsswörd-\xF0\x9F\x98\x80-12345";
    $h = \bbsengine6\password\hash_password($pw);
    if (!\bbsengine6\password\verify_password($pw, $h)) {
        throw new \Exception("UTF-8 plaintext did not round-trip");
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
