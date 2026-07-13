<?php
/**
 * test_breadcrumbs.php - Regression tests for {teos} breadcrumb rendering
 *
 * Verifies that function.teos.php derives title/URI from path segments
 * without requiring a database lookup.
 *
 * Usage:
 *   php test_breadcrumbs.php
 */

require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");
require_once("/home/opencode/data/work/bbsengine6/engine/router.php");

echo "=== Breadcrumb Regression Tests ===\n\n";

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
    'rgs/www/smarty/function.teos.php',
];

// zoid6/smarty/function.teos.php should NOT exist — bbsengine6 version is
// the single source of truth, found via SMARTYPLUGINSDIR fallback.
$teos_files_absent = [
    'zoid6/smarty/function.teos.php',
];

foreach ($teos_files_absent as $teos_file) {
    $path = "/home/opencode/data/work/$teos_file";
    echo "Test: $teos_file should NOT exist\n";
    if (file_exists($path)) {
        test_fail("$teos_file should not exist (use bbsengine6 version via SMARTYPLUGINSDIR)");
    }
    test_pass("$teos_file correctly absent");
}

foreach ($teos_files as $idx => $teos_file) {
    $src = load_teos_source($teos_file);

    // Test: must not contain the PATHNOTFOUND error string
    echo "Test " . ($idx * 2 + 1) . ": $teos_file has no PATHNOTFOUND string\n";
    if (strpos($src, 'PATHNOTFOUND') !== false) {
        test_fail("$teos_file still contains PATHNOTFOUND");
    }
    test_pass("no PATHNOTFOUND in $teos_file");

    // Test: must derive title from path (not from DB)
    echo "Test " . ($idx * 2 + 2) . ": $teos_file derives title from path\n";
    if (strpos($src, 'str_replace') === false) {
        test_fail("$teos_file missing title derivation from path");
    }
    test_pass("title derivation present");
}

echo "\n";

// =============================================================================
// TEMPLATE TESTS
// =============================================================================

echo "--- Template Tests ---\n\n";

// Test: function.teos.tmpl exists and has no debug output
echo "Test 5: bbsengine6 function.teos.tmpl is clean\n";
$teos_tmpl = "/home/opencode/data/work/bbsengine6/skin/tmpl/function.teos.tmpl";
if (!file_exists($teos_tmpl)) {
    test_fail("bbsengine6 function.teos.tmpl not found");
}
$tmpl_src = file_get_contents($teos_tmpl);
$tmpl_no_comments = preg_replace('/\{\*.*?\*\}/s', '', $tmpl_src);
if (strpos($tmpl_no_comments, 'var_dump') !== false) {
    test_fail("function.teos.tmpl contains uncommented var_dump");
}
if (strpos($tmpl_no_comments, '!!') !== false) {
    test_fail("function.teos.tmpl contains debug markers !!");
}
test_pass("function.teos.tmpl is clean");

// Test: youarehere.tmpl uses teos-breadcrumbs.tmpl
echo "Test 6: youarehere.tmpl uses teos-breadcrumbs.tmpl\n";
$youarehere = "/home/opencode/data/work/bbsengine6/skin/tmpl/youarehere.tmpl";
$youarehere_src = file_get_contents($youarehere);
if (strpos($youarehere_src, 'teos-breadcrumbs.tmpl') === false) {
    test_fail("youarehere.tmpl does not include teos-breadcrumbs.tmpl");
}
test_pass("youarehere.tmpl uses teos-breadcrumbs.tmpl");

// Test: page-markdown.tmpl uses youarehere.tmpl
echo "Test 7: page-markdown.tmpl uses youarehere.tmpl\n";
$page_md = "/home/opencode/data/work/bbsengine6/skin/tmpl/page-markdown.tmpl";
$page_md_src = file_get_contents($page_md);
if (strpos($page_md_src, 'youarehere.tmpl') === false) {
    test_fail("page-markdown.tmpl does not include youarehere.tmpl");
}
test_pass("page-markdown.tmpl uses youarehere.tmpl");

echo "\n";

// =============================================================================
// PATH DERIVATION LOGIC TESTS
// =============================================================================

echo "--- Path Derivation Tests ---\n\n";

// These test the same logic that function.teos.php uses:
// 1. Split path on dots into segments
// 2. Convert underscores to hyphens for filesystem/URI
// 3. Join segments with slashes for URI
// 4. Title from last segment with hyphens/underscores replaced by spaces

function derive_teos_crumb(string $path): array {
    $segments = array_values(array_filter(explode(".", $path)));
    $uriSegments = array_map(function($s) { return str_replace("_", "-", $s); }, $segments);

    $uri = implode("/", $uriSegments) . "/";
    if (count($uriSegments) > 0) {
        $title = end($uriSegments);
    } else {
        $title = $path;
    }
    $title = str_replace(["-", "_"], " ", $title);

    return ['title' => $title, 'uri' => $uri];
}

// Test: single segment
echo "Test 10: derivation for 'teos'\n";
$f = derive_teos_crumb("teos");
if ($f['title'] !== 'teos' || $f['uri'] !== 'teos/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("teos → title='teos', uri='teos/'");

// Test: two segments
echo "Test 11: derivation for 'comp.lang'\n";
$f = derive_teos_crumb("comp.lang");
if ($f['title'] !== 'lang' || $f['uri'] !== 'comp/lang/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("comp.lang → title='lang', uri='comp/lang/'");

// Test: three segments
echo "Test 12: derivation for 'comp.lang.python'\n";
$f = derive_teos_crumb("comp.lang.python");
if ($f['title'] !== 'python' || $f['uri'] !== 'comp/lang/python/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("comp.lang.python → title='python', uri='comp/lang/python/'");

// Test: hyphens become spaces in title, preserved in URI
echo "Test 13: derivation for 'rec.arts.star-trek'\n";
$f = derive_teos_crumb("rec.arts.star-trek");
if ($f['title'] !== 'star trek' || $f['uri'] !== 'rec/arts/star-trek/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("rec.arts.star-trek → title='star trek', uri='rec/arts/star-trek/'");

// Test: underscores become spaces in title, converted to hyphens in URI
echo "Test 14: derivation for 'rec.arts.star_trek'\n";
$f = derive_teos_crumb("rec.arts.star_trek");
if ($f['title'] !== 'star trek' || $f['uri'] !== 'rec/arts/star-trek/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("rec.arts.star_trek → title='star trek', uri='rec/arts/star-trek/'");

// Test: deep path (the-a-team use case)
echo "Test 15: derivation for 'rec.arts.tv.the-a-team'\n";
$f = derive_teos_crumb("rec.arts.tv.the-a-team");
if ($f['title'] !== 'the a team' || $f['uri'] !== 'rec/arts/tv/the-a-team/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("rec.arts.tv.the-a-team → title='the a team', uri='rec/arts/tv/the-a-team/'");

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

// Test: breadcrumb titles are human-readable
echo "Test 21: breadcrumb titles are human-readable\n";
$crumbs = router_buildBreadcrumbs("rec/arts/tv/the-a-team");
$last = end($crumbs);
if ($last['title'] !== 'the a team') {
    test_fail("last crumb title is not 'the a team'", $last['title']);
}
test_pass("last crumb title is 'the a team'");

echo "\n";

echo "=== Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\n✓ All breadcrumb regression tests passed!\n";
exit(0);
