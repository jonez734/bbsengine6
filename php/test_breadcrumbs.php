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

// @since 2026-09-10 — bootstrap order. The pre-existing test
// bootstrap only required bbsengine6/php/bootstrap.php (which
// sets the include_path) and engine/router.php, leaving the
// Tests 20-21 data-structure block unable to run with a
// "Call to undefined function bbsengine6\util\teos_url()"
// fatal. The new TEOS_LABEL plumbing tests (22-24) need
// bbsengine6\util\vhost_label(), which lives in php/util.php
// and is reached by router_buildBreadcrumbs through
// bbsengine6\util\teos_url(). Requiring php/util.php before
// engine/router.php makes both the pre-existing data tests
// and the new TEOS_LABEL tests runnable without dragging in
// the blurb.php require chain (zoid6\bootstrap, zoid6config,
// zoid6.php, ...).
require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");
require_once("/home/opencode/data/work/bbsengine6/php/util.php");
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

// Test: teos-breadcrumbs.tmpl exists on disk. Catches the half-finished
// refactor from commit ff0981a where youarehere.tmpl was updated to
// include teos-breadcrumbs.tmpl but the target template was never
// authored. Without this assertion the build looks green until
// Smarty tries to render a page that uses youarehere.tmpl.
echo "Test 6b: skin/tmpl/teos-breadcrumbs.tmpl exists\n";
$target = "/home/opencode/data/work/bbsengine6/skin/tmpl/teos-breadcrumbs.tmpl";
if (!file_exists($target)) {
    test_fail("skin/tmpl/teos-breadcrumbs.tmpl missing", $target);
}
test_pass("skin/tmpl/teos-breadcrumbs.tmpl exists");

// Test: page-markdown.tmpl uses youarehere.tmpl
echo "Test 7: page-markdown.tmpl uses youarehere.tmpl\n";
$page_md = "/home/opencode/data/work/bbsengine6/skin/tmpl/page-markdown.tmpl";
$page_md_src = file_get_contents($page_md);
if (strpos($page_md_src, 'youarehere.tmpl') === false) {
    test_fail("page-markdown.tmpl does not include youarehere.tmpl");
}
test_pass("page-markdown.tmpl uses youarehere.tmpl");

// Test: teos-breadcrumbs.tmpl and breadcrumbs.tmpl pass title=$b.title
// into {teos}. @since 2026-09-10 — regression check for the
// "double-teos" bug where the root crumb rendered as the
// literal string "teos" twice. The {teos} Smarty plugin
// (smarty/function.teos.php:25-44) defaults its rendered
// text to end($uriSegments) when no title= argument is
// supplied, so for the root crumb (path='teos', one
// segment) it printed 'teos' regardless of $b.title.
// Passing title=$b.title through to the plugin makes the
// visible text follow the breadcrumb data, which the
// handbook vhost now populates with 'bbsengine6 handbook'
// via the TEOS_LABEL plumbing (Test 23/24 above).
$title_arg_check = [
    "/home/opencode/data/work/bbsengine6/skin/tmpl/teos-breadcrumbs.tmpl",
    "/home/opencode/data/work/bbsengine6/skin/tmpl/breadcrumbs.tmpl",
];
foreach ($title_arg_check as $tpl) {
    $label = basename($tpl);
    echo "Test 8: $label passes title=\$b.title to {teos}\n";
    if (!file_exists($tpl)) {
        test_fail("$label missing", $tpl);
    }
    $src = file_get_contents($tpl);
    if (strpos($src, 'title=$b.title') === false) {
        test_fail("$label does not pass title=\$b.title to {teos} (regression: the top crumb will render its path-derived title, causing the double-'teos'-link bug on the handbook vhost)");
    }
    test_pass("$label passes title=\$b.title to {teos}");
}

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

// Test: top-crumb title defaults to 'teos' when TEOS_LABEL is unset.
// @since 2026-09-10 — regression check for the
// router_buildBreadcrumbs() -> bbsengine6\util\vhost_label()
// plumbing. Without TEOS_LABEL set (or with it empty) the
// top crumb must still be 'teos', so existing /teos/ vhost
// callers see no change.
echo "Test 22: top-crumb title defaults to 'teos' when TEOS_LABEL unset\n";
putenv('TEOS_LABEL'); // clear any pre-existing value
$crumbs = router_buildBreadcrumbs("specs/foo");
if ($crumbs[0]['title'] !== 'teos') {
    test_fail("expected top crumb title 'teos', got '" . var_export($crumbs[0]['title'], true) . "'");
}
if ($crumbs[0]['path'] !== 'teos') {
    test_fail("expected top crumb path 'teos', got '" . var_export($crumbs[0]['path'], true) . "'");
}
test_pass("default top crumb is title='teos', path='teos'");

// Test: top-crumb title honors TEOS_LABEL env var.
// @since 2026-09-10 — the handbook vhost entry point in
// engine/router.php putenv()s TEOS_LABEL="bbsengine6
// handbook" before dispatching; bbsengine6\util\vhost_label()
// in php/util.php reads it. router_buildBreadcrumbs was
// updated to call vhost_label() so the same vhost label
// reaches the filesystem-driven breadcrumb path. Catches
// a future refactor that decouples the two code paths
// (blurb.php vs router.php) or drops the env read.
echo "Test 23: top-crumb title honors TEOS_LABEL env var\n";
putenv('TEOS_LABEL=handbook test label');
$crumbs = router_buildBreadcrumbs("specs/foo");
if ($crumbs[0]['title'] !== 'handbook test label') {
    test_fail("expected top crumb title 'handbook test label', got '" . var_export($crumbs[0]['title'], true) . "'");
}
if ($crumbs[0]['path'] !== 'teos') {
    test_fail("path identifier should still be 'teos' (internal), got '" . var_export($crumbs[0]['path'], true) . "'");
}
if (!str_ends_with($crumbs[0]['uri'], '/')) {
    test_fail("top crumb uri should end with /, got '" . var_export($crumbs[0]['uri'], true) . "'");
}
test_pass("TEOS_LABEL env var → top crumb title matches; path and uri unchanged");
putenv('TEOS_LABEL'); // clean up

// Test: top-crumb uri still follows TEOSURL after the
// TEOS_LABEL change. The handbook vhost sets TEOSURL to
// '/handbook/6/' via putenv() before TEOS_LABEL; the
// teos vhost sets TEOSURL='/teos/'. The root crumb's
// uri must follow whichever TEOSURL is in effect, not
// the literal 'teos' string.
echo "Test 24: top-crumb uri follows TEOSURL when TEOS_LABEL is set\n";
putenv('TEOSURL=/handbook/6/');
putenv('TEOS_LABEL=bbsengine6 handbook');
$crumbs = router_buildBreadcrumbs("specs/foo");
if ($crumbs[0]['uri'] !== '/handbook/6/') {
    test_fail("expected top crumb uri '/handbook/6/', got '" . var_export($crumbs[0]['uri'], true) . "'");
}
test_pass("top crumb uri is /handbook/6/ when TEOSURL is /handbook/6/");
// restore defaults so subsequent test runs are unaffected
putenv('TEOSURL');
putenv('TEOS_LABEL');

echo "\n";

echo "=== Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\n✓ All breadcrumb regression tests passed!\n";
exit(0);
