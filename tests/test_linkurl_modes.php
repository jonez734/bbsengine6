<?php
/**
 * test_linkurl_modes.php
 *
 * Regression tests for Phase 3 smarty modifier.linkurl.php hardening.
 *
 * Pre-Phase-3 the plugin used preg_replace with /e modifier, which was
 * removed in PHP 7 and breaks on PHP 8.4+. Phase 3 rewrote it to use
 * preg_replace_callback. Additionally the original regex flag list
 * "smei" contained a trailing "e" which produced an "Unknown modifier"
 * warning even after the rewrite — Phase 3 also dropped the e from
 * the flag list (now "smi").
 *
 * These tests cover the SIMPLE / NONE / GET / POST modes against the
 * production function defined in smarty/modifier.linkurl.php.
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once __DIR__ . "/../smarty/modifier.linkurl.php";

$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

function run_test_linkurl($name, $callable) {
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

function assert_contains_linkurl($needle, $haystack, $message = "") {
    if (strpos($haystack, $needle) === false) {
        throw new \Exception(
            "Expected to find " . var_export($needle, true) .
            " in " . var_export($haystack, true) .
            ". $message"
        );
    }
}

function assert_not_contains_linkurl($needle, $haystack, $message = "") {
    if (strpos($haystack, $needle) !== false) {
        throw new \Exception(
            "Expected NOT to find " . var_export($needle, true) .
            " in " . var_export($haystack, true) .
            ". $message"
        );
    }
}

echo "================================================================================\n";
echo "smarty_modifier_linkurl() Test Suite\n";
echo "================================================================================\n\n";

// Capture any preg_replace warnings that would indicate the /e modifier bug.
set_error_handler(function($errno, $errstr) {
    if (strpos($errstr, "Unknown modifier") !== false ||
        strpos($errstr, "preg_replace") !== false) {
        throw new \Exception("Preg warning leaked: $errstr");
    }
    return false;
});

run_test_linkurl("non-string input returns empty string", function() {
    assert_equals_linkurl("", smarty_modifier_linkurl(null));
    assert_equals_linkurl("", smarty_modifier_linkurl(12345));
    assert_equals_linkurl("", smarty_modifier_linkurl([]));
});

run_test_linkurl("plain text without URLs is returned unchanged", function() {
    $input = "hello world no urls here";
    assert_equals_linkurl($input, smarty_modifier_linkurl($input));
});

run_test_linkurl("SIMPLE mode wraps https URL in <a href>", function() {
    $out = smarty_modifier_linkurl("visit https://example.com today");
    assert_contains_linkurl('href="https://example.com"', $out);
    assert_contains_linkurl("<a ", $out);
    assert_contains_linkurl('rel="nofollow"', $out);
});

run_test_linkurl("SIMPLE mode upgrades bare www. to http://", function() {
    $out = smarty_modifier_linkurl("visit www.example.com today");
    assert_contains_linkurl('href="http://www.example.com"', $out);
});

run_test_linkurl("NONE mode shows shortened URL without <a href>", function() {
    $out = smarty_modifier_linkurl(
        "long url https://example.com/some/very/long/path/that/exceeds/limit",
        25,
        "NONE"
    );
    assert_not_contains_linkurl("<a ", $out);
    assert_contains_linkurl("example.com", $out);
});

run_test_linkurl("GET mode redirects via redir URL", function() {
    $out = smarty_modifier_linkurl(
        "click https://example.com here",
        50,
        "GET",
        "redir.php?u="
    );
    assert_contains_linkurl('href="redir.php?u=https://example.com"', $out);
});

run_test_linkurl("GET mode upgrades bare www. in redir URL", function() {
    $out = smarty_modifier_linkurl(
        "click www.example.com here",
        50,
        "GET",
        "redir.php?u="
    );
    assert_contains_linkurl('href="redir.php?u=http://www.example.com"', $out);
});

run_test_linkurl("POST mode wraps URL in <form> with hidden input", function() {
    $out = smarty_modifier_linkurl(
        "click https://example.com here",
        50,
        "POST",
        "redir.php"
    );
    assert_contains_linkurl("<form", $out);
    assert_contains_linkurl('method="post"', $out);
    assert_contains_linkurl('name="up"', $out);
    assert_contains_linkurl('value="https://example.com"', $out);
    assert_contains_linkurl('action="redir.php"', $out);
});

run_test_linkurl("URL in URL-encoded form is htmlspecialchars-escaped", function() {
    $out = smarty_modifier_linkurl(
        'click https://example.com/?a=1&b="x" here',
        100,
        "SIMPLE"
    );
    // The double-quote " should be escaped to &quot; in the href attr.
    assert_contains_linkurl("&quot;", $out);
});

run_test_linkurl("multiple URLs in same string are all linked", function() {
    $out = smarty_modifier_linkurl(
        "see https://a.example.com and https://b.example.com",
        50,
        "SIMPLE"
    );
    assert_contains_linkurl('href="https://a.example.com"', $out);
    assert_contains_linkurl('href="https://b.example.com"', $out);
});

run_test_linkurl("URL inside parentheses is properly delimited", function() {
    $out = smarty_modifier_linkurl("(see https://example.com)", 50, "SIMPLE");
    assert_contains_linkurl('href="https://example.com"', $out);
});

restore_error_handler();

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

function assert_equals_linkurl($expected, $actual, $message = "") {
    if ($expected !== $actual) {
        throw new \Exception(
            "Expected " . var_export($expected, true) .
            ", got " . var_export($actual, true) .
            ". $message"
        );
    }
}
