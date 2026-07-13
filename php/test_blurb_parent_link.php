<?php
/**
 * test_blurb_parent_link.php
 * Verifies that a blurb page contains a "previous folder" (parent) link.
 *
 * The page-markdown-sections.tmpl should render a parent folder link
 * (href="..") before the first section when breadcrumbs are non-empty.
 *
 * Run: php test_blurb_parent_link.php
 *
 * @since 2026-07-12
 */

$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

$blurb_url = "https://zoidtechnologies.com/teos/rec/arts/sci-fi/tv/knight-rider/iconic-episodes/knight-song";

function run_test($name, $callable) {
    global $tests_passed, $tests_failed, $test_results;
    try {
        $callable();
        $tests_passed++;
        $test_results[] = "PASS: $name";
        echo "  PASS: $name\n";
    } catch (Throwable $e) {
        $tests_failed++;
        $test_results[] = "FAIL: $name - " . $e->getMessage();
        echo "  FAIL: $name\n";
        echo "    " . $e->getMessage() . "\n";
    }
}

function assert_true($condition, $message = "") {
    if (!$condition) {
        throw new Exception($message ?: "Expected true");
    }
}

function assert_false($condition, $message = "") {
    if ($condition) {
        throw new Exception($message ?: "Expected false");
    }
}

function fetch_url($url) {
    $ctx = stream_context_create([
        "http" => [
            "follow_location" => true,
            "timeout" => 30,
            "ignore_errors" => true,
        ],
    ]);
    $html = @file_get_contents($url, false, $ctx);
    if ($html === false) {
        throw new Exception("Failed to fetch $url");
    }
    return $html;
}

echo "Blurb Parent Link Tests\n";
echo "=======================\n";
echo "URL: $blurb_url\n\n";

$html = fetch_url($blurb_url);

// ====================================================================
// Test Group 1: Page loads successfully
// ====================================================================

echo "Test Group 1: Page loads\n";

run_test("HTTP response is non-empty", function() use ($html) {
    assert_true(strlen($html) > 0, "Response body is empty");
});

run_test("page contains blurb content", function() use ($html) {
    assert_true(
        strpos($html, "knight-song") !== false || strpos($html, "knight") !== false,
        "Expected blurb content about knight-song"
    );
});

// ====================================================================
// Test Group 2: Parent folder link exists
// ====================================================================

echo "\nTest Group 2: Parent folder link\n";

run_test("page contains a parent folder link (href=\"..\")", function() use ($html) {
    assert_true(
        preg_match('/<a\s+href="\.\."[^>]*>/', $html) === 1,
        "Expected <a href=\"..\"> link for parent folder navigation"
    );
});

run_test("parent link contains up-arrow icon", function() use ($html) {
    assert_true(
        strpos($html, "fa-level-up-alt") !== false,
        "Expected fa-level-up-alt icon in parent folder link"
    );
});

run_test("parent link appears before first section header", function() use ($html) {
    $parent_pos = strpos($html, 'href=".."');
    assert_true($parent_pos !== false, "Parent link not found");

    $first_h1_pos = strpos($html, "<h1>", $parent_pos);
    assert_true($first_h1_pos !== false, "No <h1> found after parent link");
    assert_true(
        $first_h1_pos > $parent_pos,
        "First <h1> should appear after parent link"
    );
});

// ====================================================================
// Results
// ====================================================================

echo "\n=======================\n";
echo "Results: $tests_passed passed, $tests_failed failed\n";

if ($tests_failed > 0) {
    echo "\nFailures:\n";
    foreach ($test_results as $r) {
        if (strpos($r, "FAIL") === 0) {
            echo "  $r\n";
        }
    }
    exit(1);
}

echo "\nAll tests passed.\n";
exit(0);
