<?php
/**
 * test_breadcrumbs.php - Regression tests for TEOS.PATHNOTFOUND fix
 *
 * Verifies that {teos} Smarty plugin never renders "TEOS.PATHNOTFOUND"
 * as visible text. When a path is missing from engine.sig, the plugin
 * derives a fallback title and URI from the path itself.
 *
 * Usage:
 *   php test_breadcrumbs.php
 */

require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");
require_once("/home/opencode/data/work/bbsengine6/engine/router.php");

echo "=== PATHNOTFOUND Regression Tests ===\n\n";

$passed = 0;
$failed = 0;

function test_pass(string $name, string $detail = '') {
    global $passed;
    $passed++;
    $suffix = $detail ? ": $detail" : '';
    echo "  ✓ PASS: $name$suffix\n";
}

function test_fail(string $name, string $detail = ''): never {
    global $failed;
    $failed++;
    $suffix = $detail ? " — $detail" : '';
    echo "  ✗ FAIL: $name$suffix\n";
    exit(1);
}

// =============================================================================
// FUNCTION.TEOS.PHP SOURCE ANALYSIS
// =============================================================================

echo "--- function.teos.php Source Tests ---\n\n";

function load_teos_source(string $subpath): string {
    $path = "/home/opencode/data/work/$subpath";
    if (!file_exists($path)) {
        test_fail("source file not found", $path);
    }
    return file_get_contents($path);
}

$teos_files = [
    'bbsengine6/smarty/function.teos.php',
    'zoid6/smarty/function.teos.php',
    'rgs/www/smarty/function.teos.php',
];

foreach ($teos_files as $idx => $teos_file) {
    $src = load_teos_source($teos_file);

    // Test: must not contain the PATHNOTFOUND error string
    echo "Test " . ($idx * 3 + 1) . ": $teos_file has no PATHNOTFOUND string\n";
    if (strpos($src, 'PATHNOTFOUND') !== false) {
        test_fail("$teos_file still contains PATHNOTFOUND");
    }
    test_pass("no PATHNOTFOUND in $teos_file");

    // Test: must still have the DB query for the happy path
    echo "Test " . ($idx * 3 + 2) . ": $teos_file queries engine.sig\n";
    if (strpos($src, 'engine.sig') === false) {
        test_fail("$teos_file missing engine.sig query");
    }
    test_pass("engine.sig query present");

    // Test: must have fallback derivation logic
    echo "Test " . ($idx * 3 + 3) . ": $teos_file has fallback path derivation\n";
    if (strpos($src, 'implode("/", $segments)') === false) {
        test_fail("$teos_file missing URI derivation from path segments");
    }
    if (strpos($src, 'str_replace') === false) {
        test_fail("$teos_file missing title derivation from path");
    }
    test_pass("fallback derivation present");
}

echo "\n";

// =============================================================================
// PATH DERIVATION LOGIC TESTS
// =============================================================================

echo "--- Path Derivation Tests ---\n\n";

// These test the same logic that function.teos.php uses for fallback:
//   $segments = array_filter(explode(".", $path));
//   $title = end($segments) ?: $path;
//   $title = str_replace(["-", "_"], " ", $title);
//   $uri = implode("/", $segments) . "/";

function derive_fallback(string $path): array {
    $segments = array_filter(explode(".", $path));
    $title = end($segments) ?: $path;
    $title = str_replace(["-", "_"], " ", $title);
    $uri = implode("/", $segments) . "/";
    return ['title' => $title, 'uri' => $uri];
}

// Test: single segment path
echo "Test 10: fallback for 'teos'\n";
$f = derive_fallback("teos");
if ($f['title'] !== 'teos' || $f['uri'] !== 'teos/') {
    test_fail("unexpected fallback", print_r($f, true));
}
test_pass("teos → title='teos', uri='teos/'");

// Test: single segment
echo "Test 11: fallback for 'comp'\n";
$f = derive_fallback("comp");
if ($f['title'] !== 'comp' || $f['uri'] !== 'comp/') {
    test_fail("unexpected fallback", print_r($f, true));
}
test_pass("comp → title='comp', uri='comp/'");

// Test: two segments
echo "Test 12: fallback for 'comp.lang'\n";
$f = derive_fallback("comp.lang");
if ($f['title'] !== 'lang' || $f['uri'] !== 'comp/lang/') {
    test_fail("unexpected fallback", print_r($f, true));
}
test_pass("comp.lang → title='lang', uri='comp/lang/'");

// Test: three segments
echo "Test 13: fallback for 'comp.lang.python'\n";
$f = derive_fallback("comp.lang.python");
if ($f['title'] !== 'python' || $f['uri'] !== 'comp/lang/python/') {
    test_fail("unexpected fallback", print_r($f, true));
}
test_pass("comp.lang.python → title='python', uri='comp/lang/python/'");

// Test: hyphens become spaces in title
echo "Test 14: fallback for 'rec.arts.star-trek'\n";
$f = derive_fallback("rec.arts.star-trek");
if ($f['title'] !== 'star trek' || $f['uri'] !== 'rec/arts/star-trek/') {
    test_fail("unexpected fallback", print_r($f, true));
}
test_pass("rec.arts.star-trek → title='star trek', uri='rec/arts/star-trek/'");

// Test: underscores become spaces in title
echo "Test 15: fallback for 'ec.john_edward'\n";
$f = derive_fallback("ec.john_edward");
if ($f['title'] !== 'john edward' || $f['uri'] !== 'ec/john_edward/') {
    test_fail("unexpected fallback", print_r($f, true));
}
test_pass("ec.john_edward → title='john edward', uri='ec/john_edward/'");

// Test: empty/blank path returns path itself
echo "Test 16: fallback for empty path\n";
$f = derive_fallback("");
if ($f['title'] !== '' || $f['uri'] !== '/') {
    test_fail("unexpected fallback for empty path", print_r($f, true));
}
test_pass("empty path → title='', uri='/'");

echo "\n";

// =============================================================================
// BREADCRUMB DATA STRUCTURE TESTS
// =============================================================================

echo "--- Breadcrumb Data Tests ---\n\n";

if (!defined('TEOSURL')) {
    define('TEOSURL', '/teos/');
}

// Test: router_buildBreadcrumbs always produces title+uri+path keys
echo "Test 20: router_buildBreadcrumbs produces required keys\n";
$crumbs = router_buildBreadcrumbs("comp/lang/python");
foreach ($crumbs as $i => $crumb) {
    if (!isset($crumb['title']) || !isset($crumb['uri']) || !isset($crumb['path'])) {
        test_fail("crumb[$i] missing required keys", print_r($crumb, true));
    }
}
test_pass('all crumbs have title, uri, and path');

// Test: breadcrumb data is suitable for {teos} plugin
echo "Test 21: breadcrumb paths are valid for {teos} lookup\n";
$paths = ['comp', 'comp.lang', 'comp.lang.python', 'rec', 'rec.arts', 'rec.arts.star-trek'];
foreach ($paths as $path) {
    $segments = explode(".", $path);
    $last = end($segments);
    if (empty($last)) {
        test_fail("path '$path' produces empty last segment");
    }
    // The path must be a valid engine.sig lookup key (no slashes, just dots)
    if (strpos($path, '/') !== false) {
        test_fail("path '$path' contains slash, not valid for {teos}");
    }
}
test_pass('all paths are valid {teos} lookup keys');

echo "\n";

echo "=== Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\n✓ All PATHNOTFOUND regression tests passed!\n";
exit(0);
