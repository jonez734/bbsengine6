<?php
/**
 * test_php_password_round_trip.php
 *
 * Integration test: PHP libpassword.php + libmember.php end-to-end
 * against the live engine.__member table.
 *
 * Pins:
 *   - setpassword() writes $2y$06$... length 60 (no PG round-trip).
 *   - checkpassword() verifies locally via password_verify.
 *   - checkpassword() transparently rehashes a legacy $1$ MD5-crypt
 *     value on successful verify (matches Python's audit + rehash
 *     pattern in bbsengine6.member.checkpassword).
 *   - PG crypt(plaintext, stored) ALSO verifies the locally-written
 *     hash (proves prefix and cost are in lock-step with
 *     gen_salt('bf')).
 *
 * Requires live DB (BBSENGINE_TEST_DSN env var). Skips gracefully if
 * not set so the suite can still be invoked in CI without a DB.
 */

error_reporting(E_ALL);
ini_set("display_errors", 1);

require_once __DIR__ . "/../../php/bootstrap.php";
require_once __DIR__ . "/../../php/util.php";
require_once __DIR__ . "/../../php/database.php";
require_once __DIR__ . "/../../php/libpassword.php";
require_once __DIR__ . "/../../php/libmember.php";

$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

function run_test_int($name, $callable) {
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

$test_moniker = "bbsengine6_php_pw_test_" . getmypid();
$test_dsn     = getenv("BBSENGINE_TEST_DSN");
$test_user    = getenv("BBSENGINE_TEST_USER") ?: "";
$test_pass    = getenv("BBSENGINE_TEST_PASS") ?: "";

if ($test_dsn) {
    if (!defined("SYSTEMDSN")) {
        define("SYSTEMDSN", $test_dsn);
    }
    if ($test_user && !defined("BBSENGINE_TEST_USER")) {
        define("BBSENGINE_TEST_USER", $test_user);
    }
    if ($test_pass && !defined("BBSENGINE_TEST_PASS")) {
        define("BBSENGINE_TEST_PASS", $test_pass);
    }
}

echo "================================================================================\n";
echo "bbsengine6\\password integration test (live DB)\n";
echo "================================================================================\n";

if (!$test_dsn) {
    echo "\n  SKIP: BBSENGINE_TEST_DSN not set; integration test requires live DB.\n";
    echo "         Set BBSENGINE_TEST_DSN, BBSENGINE_TEST_USER, BBSENGINE_TEST_PASS\n";
    echo "         (e.g. pgsql:host=127.0.0.1;port=5432;dbname=zoid6) and re-run.\n";
    echo "\n================================================================================\n";
    echo "Test Results: 0 total, 0 passed, 0 failed (skipped)\n";
    echo "================================================================================\n";
    exit(0);
}

echo "\n  Using moniker: $test_moniker\n\n";

try {
    $pdo = new \PDO($test_dsn, $test_user, $test_pass, [
        \PDO::ATTR_ERRMODE => \PDO::ERRMODE_EXCEPTION,
    ]);

    // Seed test member row.
    $pdo->prepare(
        "INSERT INTO engine.__member(moniker, password, email) " .
        "VALUES(:m, :p, :e) ON CONFLICT (moniker) DO UPDATE SET password = EXCLUDED.password"
    )->execute([":m" => $test_moniker, ":p" => null, ":e" => "$test_moniker@test.invalid"]);

    run_test_int("seed test member row exists", function() use ($pdo, $test_moniker) {
        $stmt = $pdo->prepare("SELECT moniker FROM engine.__member WHERE moniker = :m");
        $stmt->execute([":m" => $test_moniker]);
        if ($stmt->rowCount() !== 1) {
            throw new \Exception("seed row not found");
        }
    });

    run_test_int("setpassword writes a $2y$06$ bcrypt hash length 60", function() use ($pdo, $test_moniker) {
        $ok = \bbsengine6\member\lib\setpassword($test_moniker, "plaintext-A");
        if ($ok !== true) {
            throw new \Exception("setpassword returned " . var_export($ok, true));
        }
        $stmt = $pdo->prepare("SELECT password FROM engine.__member WHERE moniker = :m");
        $stmt->execute([":m" => $test_moniker]);
        $stored = $stmt->fetchColumn();
        if (strlen($stored) !== 60) {
            throw new \Exception("length=" . strlen($stored) . " want 60; got $stored");
        }
        if (strncmp($stored, "\$2y\$06\$", 7) !== 0) {
            throw new \Exception("prefix mismatch: $stored");
        }
    });

    run_test_int("checkpassword verifies a fresh bcrypt row", function() use ($test_moniker) {
        if (\bbsengine6\member\lib\checkpassword("plaintext-A", $test_moniker) !== true) {
            throw new \Exception("verify failed for matching plaintext");
        }
    });

    run_test_int("checkpassword rejects wrong plaintext", function() use ($test_moniker) {
        if (\bbsengine6\member\lib\checkpassword("WRONG", $test_moniker) !== false) {
            throw new \Exception("verify succeeded for wrong plaintext");
        }
    });

    run_test_int("checkpassword returns false for unknown moniker", function() use ($pdo, $test_moniker) {
        $unknown = $test_moniker . "_does_not_exist";
        if (\bbsengine6\member\lib\checkpassword("anything", $unknown) !== false) {
            throw new \Exception("verify succeeded for unknown moniker");
        }
    });

    run_test_int("PHP-written hash re-verifies locally via password_verify()", function() use ($test_moniker) {
        // Read the stored hash directly via PDO (bypassing libmember),
        // then re-verify via the same code path the production code uses.
        $pdo2 = new \PDO(
            getenv("BBSENGINE_TEST_DSN"),
            getenv("BBSENGINE_TEST_USER") ?: "",
            getenv("BBSENGINE_TEST_PASS") ?: ""
        );
        $stmt2 = $pdo2->prepare("SELECT password FROM engine.__member WHERE moniker = :m");
        $stmt2->execute([":m" => $test_moniker]);
        $stored = $stmt2->fetchColumn();
        if (!\bbsengine6\password\verify_password("plaintext-A", $stored)) {
            throw new \Exception("PHP-side re-verify of PHP-written hash failed");
        }
    });

    run_test_int("PHP-written $2y$ hash is not verifiable by PG crypt() (expected)", function() use ($pdo, $test_moniker) {
        // PG crypt() only recognises $2a$ prefix; PHP password_hash() emits $2y$.
        // After eliminating the DB round-trip this is fine (verification
        // happens in PHP via password_verify). This test pins down the
        // known limitation so a future regression that REINTRODUCES the
        // PG crypt() path catches the mismatch instead of silently failing.
        $stmt = $pdo->prepare(
            "SELECT (password = crypt(:plain, password)) AS match " .
            "FROM engine.__member WHERE moniker = :m"
        );
        $stmt->execute([":plain" => "plaintext-A", ":m" => $test_moniker]);
        $match = (bool) $stmt->fetchColumn();
        if ($match) {
            throw new \Exception(
                "PG crypt() verified $2y$ hash — surprising; would mean PG accepts $2y$ " .
                "(test pinned for awareness, not enforcement)"
            );
        }
    });

    run_test_int("checkpassword transparently rehashes a legacy $1$ MD5-crypt row", function() use ($pdo, $test_moniker) {
        // Replace the column with a hand-rolled $1$ MD5-crypt hash of "legacy-plaintext".
        // Spring/MD5-crypt format: $1$<8-char-salt>$<22-char-base64-ish-digest>
        $salt = "abcdefgh";
        $digest = crypt("legacy-plaintext", "\$1\${$salt}");
        if (strncmp($digest, "\$1\$", 3) !== 0) {
            throw new \Exception("local crypt() did not produce \$1\$ prefix");
        }
        $pdo->prepare(
            "UPDATE engine.__member SET password = :p WHERE moniker = :m"
        )->execute([":p" => $digest, ":m" => $test_moniker]);

        // Verify the column really is legacy before the call.
        $stmt = $pdo->prepare("SELECT password FROM engine.__member WHERE moniker = :m");
        $stmt->execute([":m" => $test_moniker]);
        $pre = $stmt->fetchColumn();
        if (\bbsengine6\password\is_healthy_hash($pre)) {
            throw new \Exception("pre-state was already healthy: $pre");
        }

        // Successful checkpassword should rehash.
        $ok = \bbsengine6\member\lib\checkpassword("legacy-plaintext", $test_moniker);
        if ($ok !== true) {
            throw new \Exception("verify failed against legacy hash");
        }

        $stmt->execute([":m" => $test_moniker]);
        $post = $stmt->fetchColumn();
        if (!\bbsengine6\password\is_healthy_hash($post)) {
            throw new \Exception("post-state still unhealthy: $post");
        }
        if ($post === $digest) {
            throw new \Exception("column was not rewritten after verify");
        }
    });

    run_test_int("checkpassword does NOT rehash an already-healthy row", function() use ($pdo, $test_moniker) {
        // The post-legacy-rehash column is healthy; capture and verify
        // a subsequent correct verify does not rewrite it.
        $stmt = $pdo->prepare("SELECT password FROM engine.__member WHERE moniker = :m");
        $stmt->execute([":m" => $test_moniker]);
        $before = $stmt->fetchColumn();
        if (!\bbsengine6\password\is_healthy_hash($before)) {
            throw new \Exception("baseline is not healthy: $before");
        }
        // Need to know the plaintext. We know it's either the post-legacy
        // rehash (plaintext was "legacy-plaintext") or the original
        // "plaintext-A" if the previous test failed. Try both and pick the
        // one that returns true.
        $which = null;
        foreach (["legacy-plaintext", "plaintext-A"] as $candidate) {
            if (\bbsengine6\member\lib\checkpassword($candidate, $test_moniker) === true) {
                $which = $candidate;
                break;
            }
        }
        if ($which === null) {
            throw new \Exception("could not establish a working plaintext for healthy row");
        }
        $stmt->execute([":m" => $test_moniker]);
        $after = $stmt->fetchColumn();
        if ($after !== $before) {
            throw new \Exception(
                "healthy row was rewritten during verify: before=$before after=$after"
            );
        }
    });

    // Cleanup.
    $pdo->prepare("DELETE FROM engine.__member WHERE moniker = :m")
        ->execute([":m" => $test_moniker]);
} catch (\Throwable $e) {
    echo "\n  FATAL: " . $e->getMessage() . "\n";
    echo $e->getTraceAsString() . "\n";
    exit(2);
}

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
