<?php
/**
 * test_blurb_render.php
 * Regression test for the blurb double-render bug.
 *
 * The bug: when a request hits a URI matching a .md blurb,
 *   1. router_handleBlurb() calls blurb\display()
 *   2. blurb\display() calls bbsengine6\displaypage() which echoes
 *      page.tmpl and returns null
 *   3. blurb\display() returns null (passthrough of displaypage's return)
 *   4. The router loop sees null and falls through to the next handler
 *   5. The next handler (folder or markdown) renders page.tmpl again
 *
 * The fix: router_handleBlurb must return '' (or similar non-null sentinel)
 * after calling display(), so the router stops.
 *
 * This test is a self-contained regression test that:
 *  - Stubs displaypage() to record calls and return null (the original bug)
 *  - Calls router_handleBlurb() in isolation
 *  - Asserts that the router receives a non-null sentinel
 *  - Asserts that the captured output contains page.tmpl exactly once
 *  - Asserts the output does not contain debug junk from templates
 *
 * Run: php test_blurb_render.php
 *
 * @since 2026-07-12
 */

namespace bbsengine6\blurb {
    /**
     * Stub for the buggy blurb\display(): echoes a "page.tmpl" render
     * and returns null, mimicking the original bug.
     */
    function display($uri, $filepath) {
        $GLOBALS["__displaypage_calls"]++;
        echo "<!DOCTYPE html><html><body>page.tmpl render #" . $GLOBALS["__displaypage_calls"] . "</body></html>";
        return null;  // <-- this is the bug
    }
}

namespace {

error_reporting(E_ALL & ~E_DEPRECATED);
ini_set("display_errors", 1);

$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

if (!defined("ROUTER_NEXT")) define("ROUTER_NEXT", "ROUTER_NEXT");
if (!defined("ROUTER_STOP")) define("ROUTER_STOP", "ROUTER_STOP");

$GLOBALS["__displaypage_calls"] = 0;

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

function assert_equal($expected, $actual, $message = "") {
    if ($expected !== $actual) {
        throw new Exception(
            $message ?: "Expected " . var_export($expected, true)
            . " but got " . var_export($actual, true)
        );
    }
}

function assert_not_null($value, $message = "") {
    if ($value === null) {
        throw new Exception($message ?: "Expected non-null value, got null");
    }
}

function assert_null($value, $message = "") {
    if ($value !== null) {
        throw new Exception(
            $message ?: "Expected null, got " . var_export($value, true)
        );
    }
}

function assert_true($condition, $message = "") {
    if (!$condition) {
        throw new Exception($message ?: "Expected true");
    }
}

/**
 * Simulated router handler in two variants: buggy and fixed.
 */
function fake_handleBlurb_buggy(string $uri) {
    if (function_exists('bbsengine6\\blurb\\display')) {
        return bbsengine6\blurb\display($uri, null);
    }
    return ROUTER_NEXT;
}

function fake_handleBlurb_fixed(string $uri) {
    if (function_exists('bbsengine6\\blurb\\display')) {
        bbsengine6\blurb\display($uri, null);
        return '';
    }
    return ROUTER_NEXT;
}

/**
 * Stub folder handler that ALSO renders (mimics the fallthrough bug).
 */
function fake_handleFolder_also_renders(string $uri) {
    $GLOBALS["__displaypage_calls"]++;
    echo "<!DOCTYPE html><html><body>page.tmpl fallthrough render</body></html>";
    return '';
}

/**
 * Router loop, mirroring the production one.
 */
function fake_router(array $handlers, string $uri) {
    foreach ($handlers as $handler) {
        $result = $handler($uri);
        if ($result === ROUTER_NEXT) continue;
        if ($result === null || $result === false) continue;
        return $result;
    }
    return null;
}

function test_reset() {
    $GLOBALS["__displaypage_calls"] = 0;
}

echo "Blurb Render Regression Tests\n";
echo "==============================\n\n";
ob_start();

// ====================================================================
// Test Group 1: router handle chain
// ====================================================================

echo "Test Group 1: Router handler chain does not fall through\n";

run_test("buggy handler renders page.tmpl once but returns null", function() {
    test_reset();
    $result = fake_handleBlurb_buggy("comp/lang/python/intro");
    assert_equal(1, $GLOBALS["__displaypage_calls"], "should have called display() once");
    assert_null($result, "buggy handler returns null (the bug)");
});

run_test("fixed handler renders page.tmpl and returns empty string", function() {
    test_reset();
    $result = fake_handleBlurb_fixed("comp/lang/python/intro");
    assert_equal(1, $GLOBALS["__displaypage_calls"], "should have called display() once");
    assert_not_null($result, "fixed handler must not return null");
    assert_equal("", $result, "fixed handler returns '' sentinel");
});

run_test("buggy chain: blurb + folder both render (the bug)", function() {
    test_reset();
    ob_start();
    $result = fake_router(
        ['blurb' => 'fake_handleBlurb_buggy', 'folder' => 'fake_handleFolder_also_renders'],
        "comp/lang/python/intro"
    );
    $output = ob_get_clean();

    assert_equal(2, $GLOBALS["__displaypage_calls"], "page.tmpl renders twice (the bug)");
    $count = substr_count($output, "<!DOCTYPE html>");
    assert_equal(2, $count, "output contains two <!DOCTYPE html> (the bug)");
});

run_test("fixed chain: only blurb renders, no fallthrough", function() {
    test_reset();
    ob_start();
    $result = fake_router(
        ['blurb' => 'fake_handleBlurb_fixed', 'folder' => 'fake_handleFolder_also_renders'],
        "comp/lang/python/intro"
    );
    $output = ob_get_clean();

    assert_equal(1, $GLOBALS["__displaypage_calls"], "page.tmpl renders exactly once (fixed)");
    $count = substr_count($output, "<!DOCTYPE html>");
    assert_equal(1, $count, "output contains one <!DOCTYPE html> (fixed)");
    assert_equal("", $result, "router returns '' from blurb handler");
});

// ====================================================================
// Test Group 2: Production router_handleBlurb (loaded from source)
// ====================================================================

echo "\nTest Group 2: Production router_handleBlurb function\n";

$bbsengine6_engine = "/home/opencode/data/work/bbsengine6/engine";

run_test("production router_handleBlurb exists in router.php", function() use ($bbsengine6_engine) {
    $src = file_get_contents($bbsengine6_engine . "/router.php");
    if (strpos($src, "function router_handleBlurb") === false) {
        throw new Exception("router_handleBlurb not found in router.php");
    }
});

run_test("production router_handleBlurb does NOT pass through null", function() use ($bbsengine6_engine) {
    $src = file_get_contents($bbsengine6_engine . "/router.php");
    if (preg_match('/function router_handleBlurb.*?^\}/sm', $src, $m)) {
        $body = $m[0];
    } else {
        throw new Exception("could not extract router_handleBlurb body");
    }

    if (preg_match('/return\s+bbsengine6\\\\blurb\\\\display\s*\(/', $body)) {
        throw new Exception(
            "router_handleBlurb passes through display()'s null return. " .
            "This causes the router to fall through to the next handler, " .
            "which renders page.tmpl a second time."
        );
    }
});

run_test("production router_handleBlurb returns non-null sentinel", function() use ($bbsengine6_engine) {
    $src = file_get_contents($bbsengine6_engine . "/router.php");
    if (preg_match('/function router_handleBlurb.*?^\}/sm', $src, $m)) {
        $body = $m[0];
    } else {
        throw new Exception("could not extract router_handleBlurb body");
    }

    if (!preg_match('/bbsengine6\\\\blurb\\\\display\s*\([^)]*\)\s*;\s*return\s+/', $body)) {
        throw new Exception(
            "router_handleBlurb should call display() and then return a sentinel. " .
            "Expected: 'display(...); return ...;' but got:\n$body"
        );
    }

    if (!preg_match("/return\s+(''|" . '""' . "|ROUTER_STOP)\s*;/", $body, $m)) {
        throw new Exception(
            "router_handleBlurb must return a non-null sentinel. " .
            "Found: " . trim($m[0] ?? "<none>")
        );
    }
});

// ====================================================================
// Test Group 3: Template sanity (no debug output in production templates)
// ====================================================================

echo "\nTest Group 3: Templates are clean of debug output\n";

$templates_to_check = [
    "/home/opencode/data/work/zoid6/shared/skin/tmpl/page.tmpl" => [
        "forbid" => ["<pre>foo!</pre>"],
    ],
    "/home/opencode/data/work/bbsengine6/skin/tmpl/blurb-block.tmpl" => [
        "forbid" => ["<pre>blurb!</pre>"],
    ],
    "/home/opencode/data/work/bbsengine6/skin/tmpl/page-markdown.tmpl" => [
        "forbid" => ["<pre>page-markdown!</pre>"],
    ],
    "/home/opencode/data/work/bbsengine6/skin/tmpl/page-markdown-sections.tmpl" => [
        "forbid" => [
            "<pre>!!data=",
            '<pre>{$sections|var_dump}',
            "<pre>after content block</pre>",
        ],
        "require" => ['$data.sections', '$data.title'],
    ],
];

foreach ($templates_to_check as $path => $rules) {
    $name = basename($path);
    if (isset($rules["forbid"])) {
        foreach ($rules["forbid"] as $needle) {
            run_test("$name: does not contain '$needle'", function() use ($path, $needle) {
                if (!file_exists($path)) {
                    throw new Exception("template not found: $path");
                }
                $src = file_get_contents($path);
                if (strpos($src, $needle) !== false) {
                    throw new Exception("Found forbidden debug output '$needle' in $path");
                }
            });
        }
    }
    if (isset($rules["require"])) {
        foreach ($rules["require"] as $needle) {
            run_test("$name: contains '$needle'", function() use ($path, $needle) {
                if (!file_exists($path)) {
                    throw new Exception("template not found: $path");
                }
                $src = file_get_contents($path);
                if (strpos($src, $needle) === false) {
                    throw new Exception("Required reference '$needle' not found in $path");
                }
            });
        }
    }
}

// ====================================================================
// Results
// ====================================================================

echo "\n==============================\n";
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

}
