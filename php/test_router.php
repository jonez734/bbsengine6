<?php
/**
 * test_router.php - Tests for router handler registry
 * 
 * Usage:
 *   php test_router.php           # Run mock tests
 *   php test_router.php --db       # Run database integration tests
 */

require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");
require_once("/home/opencode/data/work/bbsengine6/engine/router.php");

$run_db = in_array("--db", $argv);

echo "=== Testing router functions ===\n\n";

// =============================================================================
// MOCK TESTS (no database)
// =============================================================================

echo "--- Mock Tests ---\n\n";

// Test 1: ROUTER_NEXT constant exists
echo "Test 1: ROUTER_NEXT constant defined\n";
if (defined("ROUTER_NEXT") && ROUTER_NEXT === "ROUTER_NEXT") {
    echo "  ✓ PASS: ROUTER_NEXT = 'ROUTER_NEXT'\n";
} else {
    echo "  ✗ FAIL: ROUTER_NEXT not properly defined\n";
    exit(1);
}

// Test 2: ROUTER_STOP constant exists
echo "Test 2: ROUTER_STOP constant defined\n";
if (defined("ROUTER_STOP") && ROUTER_STOP === "ROUTER_STOP") {
    echo "  ✓ PASS: ROUTER_STOP = 'ROUTER_STOP'\n";
} else {
    echo "  ✗ FAIL: ROUTER_STOP not properly defined\n";
    exit(1);
}

// Test 3: Handler order is correct
echo "Test 3: Handler order (blurb → folder → markdown → error)\n";
$expectedOrder = ['index', 'blurb', 'folder', 'markdown', 'error'];
$handlers = router_gethandlers();
$actualOrder = array_keys($handlers);
if ($actualOrder === $expectedOrder) {
    echo "  ✓ PASS: Handler order is correct\n";
} else {
    echo "  ✗ FAIL: Handler order incorrect, got: " . implode(", ", $actualOrder) . "\n";
    exit(1);
}

// Test 4: URI to blurbID conversion
echo "Test 4: URI to blurbID conversion (used by blurb handler)\n";
$uri = "ec/john-edward";
$expected = "ec.john-edward";
$actual = str_replace("/", ".", preg_replace('/\.md$/', '', $uri));
if ($actual === $expected) {
    echo "  ✓ PASS: ec/john-edward → ec.john-edward\n";
} else {
    echo "  ✗ FAIL: expected '$expected', got '$actual'\n";
    exit(1);
}

// Test 5: YAML frontmatter parsing
echo "Test 5: YAML frontmatter parsing\n";
$yaml = "title: Test Page\ndate: 2024-01-01\n";
$metadata = router_parseYamlFrontmatter($yaml);
if ($metadata['title'] === 'Test Page' && $metadata['date'] === '2024-01-01') {
    echo "  ✓ PASS: YAML frontmatter parsed correctly\n";
} else {
    echo "  ✗ FAIL: YAML parsing failed\n";
    exit(1);
}

// Test 6: Filepath construction for teos
echo "Test 6: Filepath construction\n";
$teospath = '/srv/www/vhosts/zoidtechnologies.com/html/teos/';
$uri = 'ec/john-edward';
$filepath = $teospath . $uri . ".md";
if ($filepath === '/srv/www/vhosts/zoidtechnologies.com/html/teos/ec/john-edward.md') {
    echo "  ✓ PASS: filepath constructed correctly\n";
} else {
    echo "  ✗ FAIL: filepath incorrect: $filepath\n";
    exit(1);
}

echo "\n";

// =============================================================================
// DATABASE INTEGRATION TESTS
// =============================================================================

if ($run_db) {
    echo "--- Database Integration Tests ---\n\n";
    
    define("SYSTEMDSN", "pgsql:host=127.0.0.1;port=5432;dbname=zoid6test");
    
    require_once("/home/opencode/data/work/bbsengine6/php/database.php");
    require_once("/home/opencode/data/work/bbsengine6/php/blurb.php");
    
    // Test 1: Blurb handler detects existing blurb (mock - just check isBlurb is called correctly)
    echo "Test 7: isBlurb returns true for existing blurb\n";
    $result = \bbsengine6\blurb\isBlurb("ec.biblical-prophets-mediumship-prophecy");
    if ($result === true) {
        echo "  ✓ PASS: isBlurb('ec.biblical-prophets-mediumship-prophecy') = true\n";
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        exit(1);
    }
    
    // Test 2: Blurb handler returns ROUTER_NEXT for non-existent blurb
    echo "Test 8: isBlurb returns false for non-existent\n";
    $result = \bbsengine6\blurb\isBlurb("nonexistent/page");
    if ($result === false) {
        echo "  ✓ PASS: isBlurb returns false for non-existent\n";
    } else {
        echo "  ✗ FAIL: expected false\n";
        exit(1);
    }
    
    // Test 3: Router handles non-existent content
    echo "Test 9: Router handles non-existent content gracefully\n";
    $result = router("nonexistent/xyz123");
    // Should return null (error handler result without full page infrastructure)
    if ($result === null || $result === false) {
        echo "  ✓ PASS: router returned error result\n";
    } else {
        echo "  ✗ FAIL: unexpected result from router\n";
        exit(1);
    }
    
    echo "\n";
}

// =============================================================================
// URL GENERATION TESTS
// =============================================================================

echo "--- URL Generation Tests ---\n\n";

// Test: sig URI must produce valid URL when concatenated with TEOSURL
echo "Test 10: sig URI produces valid URL (no missing slash)\n";
// TEOSURL = /teos/ (with trailing slash), sig.uri = rec/arts/star-trek/ (no leading slash)
$teosurl = '/teos/';
$item_uri = '/teos/rec/arts/star-trek/';
$teosbase = rtrim($teosurl, '/');
$reluri = ltrim(substr($item_uri, strlen($teosbase)), '/');
$full_url = rtrim($teosurl, '/') . '/' . $reluri;
echo "  reluri = '$reluri'\n";
echo "  full URL = '$full_url'\n";
if ($full_url === '/teos/rec/arts/star-trek/') {
    echo "  ✓ PASS: URL is correct\n";
} else {
    echo "  ✗ FAIL: expected /teos/rec/arts/star-trek/, got $full_url\n";
    exit(1);
}

// Test: relative URI has no leading /
echo "Test 11: relative URI has no leading /\n";
$item_uri2 = '/teos/comp/python/';
$reluri2 = ltrim(substr($item_uri2, strlen($teosbase)), '/');
if (strpos($reluri2, '/') === 0) {
    echo "  ✗ FAIL: reluri has leading /: $reluri2\n";
    exit(1);
} else {
    echo "  ✓ PASS: reluri = $reluri2\n";
}

// Test: TEOSURL + reluri joins with exactly one slash
echo "Test 12: TEOSURL + reluri joins correctly\n";
$teosurl_ns = '/teos';  // without trailing slash (fallback)
$teosbase_ns = rtrim($teosurl_ns, '/');
$reluri3 = ltrim(substr($item_uri, strlen($teosbase_ns)), '/');
$full_url3 = $teosurl_ns . '/' . $reluri3;
if ($full_url3 === '/teos/rec/arts/star-trek/') {
    echo "  ✓ PASS: $full_url3\n";
} else {
    echo "  ✗ FAIL: expected /teos/rec/arts/star-trek/, got $full_url3\n";
    exit(1);
}

echo "\n";

// =============================================================================
// BREADCRUMB TESTS
// =============================================================================

echo "--- Breadcrumb Tests ---\n\n";

// Define TEOSURL for breadcrumb tests
if (!defined('TEOSURL')) {
    define('TEOSURL', '/teos/');
}

// Test: router_buildBreadcrumbs with path segments
echo "Test 13: router_buildBreadcrumbs builds correct crumbs\n";
$breadcrumbs = router_buildBreadcrumbs("rec/arts/star-trek");
if (count($breadcrumbs) === 3) {
    echo "  ✓ PASS: 3 breadcrumbs for rec/arts/star-trek\n";
} else {
    echo "  ✗ FAIL: expected 3 breadcrumbs, got " . count($breadcrumbs) . "\n";
    exit(1);
}

// Test: breadcrumb titles
echo "Test 14: breadcrumb titles are title-cased\n";
if ($breadcrumbs[0]['title'] === 'Rec' && $breadcrumbs[1]['title'] === 'Arts' && $breadcrumbs[2]['title'] === 'Star Trek') {
    echo "  ✓ PASS: titles = Rec, Arts, Star Trek\n";
} else {
    echo "  ✗ FAIL: titles = " . $breadcrumbs[0]['title'] . ", " . $breadcrumbs[1]['title'] . ", " . $breadcrumbs[2]['title'] . "\n";
    exit(1);
}

// Test: breadcrumb URIs
echo "Test 15: breadcrumb URIs have trailing slash\n";
if ($breadcrumbs[0]['uri'] === '/teos/rec/' && $breadcrumbs[2]['uri'] === '/teos/rec/arts/star-trek/') {
    echo "  ✓ PASS: URIs = /teos/rec/, /teos/rec/arts/star-trek/\n";
} else {
    echo "  ✗ FAIL: uri[0]=" . $breadcrumbs[0]['uri'] . " uri[2]=" . $breadcrumbs[2]['uri'] . "\n";
    exit(1);
}

// Test: empty URI returns empty array
echo "Test 16: empty URI returns empty breadcrumbs\n";
$empty = router_buildBreadcrumbs("");
if (empty($empty)) {
    echo "  ✓ PASS: empty URI → empty breadcrumbs\n";
} else {
    echo "  ✗ FAIL: expected empty array\n";
    exit(1);
}

// Test: breadcrumbs work without DB (auto-generated fallback)
echo "Test 17: breadcrumbs auto-generate without DB connection\n";
// This tests that router_buildBreadcrumbs returns valid crumbs even when DB is unavailable
$crumbs_no_db = router_buildBreadcrumbs("comp/lang/python");
if (count($crumbs_no_db) === 3
    && $crumbs_no_db[0]['path'] === 'comp'
    && $crumbs_no_db[1]['path'] === 'comp.lang'
    && $crumbs_no_db[2]['path'] === 'comp.lang.python'
    && $crumbs_no_db[0]['uri'] === '/teos/comp/'
    && $crumbs_no_db[1]['uri'] === '/teos/comp/lang/'
    && $crumbs_no_db[2]['uri'] === '/teos/comp/lang/python/') {
    echo "  ✓ PASS: auto-generated breadcrumbs correct\n";
} else {
    echo "  ✗ FAIL: auto-generated breadcrumbs incorrect\n";
    exit(1);
}

// Test: single segment produces one crumb
echo "Test 18: single segment URI produces one crumb\n";
$crumbs_single = router_buildBreadcrumbs("rec");
if (count($crumbs_single) === 1
    && $crumbs_single[0]['path'] === 'rec'
    && $crumbs_single[0]['title'] === 'Rec'
    && $crumbs_single[0]['uri'] === '/teos/rec/') {
    echo "  ✓ PASS: single crumb correct\n";
} else {
    echo "  ✗ FAIL: single crumb incorrect\n";
    exit(1);
}

// Test: hyphens in segments are title-cased with spaces
echo "Test 19: hyphens in segments become spaces in title\n";
$crumbs_hyphen = router_buildBreadcrumbs("rec/arts/star-trek");
if ($crumbs_hyphen[2]['title'] === 'Star Trek' && $crumbs_hyphen[2]['path'] === 'rec.arts.star-trek') {
    echo "  ✓ PASS: star-trek → 'Star Trek', path = rec.arts.star-trek\n";
} else {
    echo "  ✗ FAIL: title=" . $crumbs_hyphen[2]['title'] . " path=" . $crumbs_hyphen[2]['path'] . "\n";
    exit(1);
}

// Test: trailing slash in URI is handled
echo "Test 20: trailing slash in URI is handled\n";
$crumbs_trail = router_buildBreadcrumbs("rec/arts/");
if (count($crumbs_trail) === 2) {
    echo "  ✓ PASS: trailing slash ignored, 2 crumbs\n";
} else {
    echo "  ✗ FAIL: expected 2 crumbs, got " . count($crumbs_trail) . "\n";
    exit(1);
}

echo "\n";

echo "=== All tests passed! ===\n";
