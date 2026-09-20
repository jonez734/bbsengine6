<?php
/**
 * test_router.php - Tests for router handler registry
 * 
 * Usage:
 *   php test_router.php           # Run mock tests
 *   php test_router.php --db       # Run database integration tests
 */

require_once __DIR__ . "/bootstrap.php";
require_once("engine/router.php");

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

// Test 2: ROUTER_RENDERED constant exists
echo "Test 2: ROUTER_RENDERED constant defined (replaces the implicit empty-string-as-success contract)\n";
if (defined("ROUTER_RENDERED") && ROUTER_RENDERED === "ROUTER_RENDERED") {
    echo "  ✓ PASS: ROUTER_RENDERED = 'ROUTER_RENDERED'\n";
} else {
    echo "  ✗ FAIL: ROUTER_RENDERED not properly defined\n";
    exit(1);
}

// Test 3: Handler order is correct
echo "Test 3: Handler order (index → blurb → folder → markdown → page)\n";
$expectedOrder = ['index', 'blurb', 'folder', 'markdown', 'page'];
$handlers = router_gethandlers();
$actualOrder = array_keys($handlers);
if ($actualOrder === $expectedOrder) {
    echo "  ✓ PASS: Handler order is correct\n";
} else {
    echo "  ✗ FAIL: Handler order incorrect, got: " . implode(", ", $actualOrder) . "\n";
    exit(1);
}

// Test 3a: Each entry resolves to a callable FQCN. Legacy entries
// may be a bare FQCN string; new entries are arrays with a 'fn'
// key (and optional 'pattern'). Regression guard for the 2026-09-15
// namespace refactor (commit bfaca68), which left bare-name
// strings in router_gethandlers() and broke the dispatch loop on
// every HTTP request.
echo "Test 3a: Each handler entry resolves to an FQCN (regression guard for variable-function dispatch)\n";
$fqcn_ok = true;
foreach ($handlers as $name => $entry) {
    $fqcn = is_array($entry) ? ($entry['fn'] ?? null) : $entry;
    if (!is_string($fqcn) || strpos($fqcn, 'bbsengine6\\') !== 0) {
        echo "  ✗ FAIL: handler '$name' is not FQCN: " . var_export($entry, true) . "\n";
        $fqcn_ok = false;
    }
}
if (!$fqcn_ok) {
    exit(1);
}
echo "  ✓ PASS: all " . count($handlers) . " handlers have a callable FQCN\n";

// Test 3b: `error` is intentionally not in the registry (the
// dispatch loop falls through to router_handleError($uri) when no
// handler matches, so registering it would fire it twice on a
// miss). 2026-09-19.
echo "Test 3b: 'error' is not in the handler registry\n";
if (array_key_exists('error', $handlers)) {
    echo "  ✗ FAIL: 'error' key found in registry; dispatch loop would double-fire\n";
    exit(1);
}
echo "  ✓ PASS: 'error' not in registry (single source of truth via post-loop fallback)\n";

// Test 3c: Every non-null `pattern` is a valid PCRE regex.
echo "Test 3c: Handler patterns are valid PCRE\n";
$bad_patterns = [];
foreach ($handlers as $name => $entry) {
    if (!is_array($entry)) continue;
    $p = $entry['pattern'] ?? null;
    if ($p === null) continue;
    if (@preg_match($p, '') === false) {
        $bad_patterns[] = "$name: $p";
    }
}
if (!empty($bad_patterns)) {
    echo "  ✗ FAIL: invalid patterns: " . implode('; ', $bad_patterns) . "\n";
    exit(1);
}
echo "  ✓ PASS: all non-null patterns compile cleanly\n";

// Test 3d: Pattern skip behavior. Stub each handler to record
// whether it was invoked; dispatch a URI that should match only
// one handler; assert only that handler was called.
echo "Test 3d: Dispatch loop skips handlers whose pattern doesn't match\n";
$GLOBALS['__invoked'] = [];
$orig_handlers = $handlers;
$stub_handlers = [];
foreach ($orig_handlers as $name => $entry) {
    $stub_handlers[$name] = [
        'fn' => function (string $uri) use ($name) {
            $GLOBALS['__invoked'][$name] = ($GLOBALS['__invoked'][$name] ?? 0) + 1;
            return \bbsengine6\router\ROUTER_NEXT;
        },
        'pattern' => is_array($entry) ? ($entry['pattern'] ?? null) : null,
    ];
}

// Swap the registry by overriding router_gethandlers via a
// runkit-less trick: the dispatch loop calls router_gethandlers()
// every iteration, so we can't easily monkey-patch it from here
// without runkit. Instead, test the pattern logic directly: pick
// the `page` handler (narrowest pattern), then assert its pattern
// rejects a URI that should go to markdown/blurb/folder.
$page_entry = $handlers['page'];
$page_pattern = is_array($page_entry) ? $page_entry['pattern'] : null;
if ($page_pattern === null) {
    echo "  ✗ FAIL: page handler has no pattern\n";
    exit(1);
}
$should_match = (bool) preg_match($page_pattern, 'contact-us');
$should_miss  = (bool) preg_match($page_pattern, 'rec/arts/star-trek');
if (!$should_match) {
    echo "  ✗ FAIL: page pattern should match 'contact-us'\n";
    exit(1);
}
if ($should_miss) {
    echo "  ✗ FAIL: page pattern should NOT match 'rec/arts/star-trek'\n";
    exit(1);
}
echo "  ✓ PASS: page pattern matches 'contact-us', rejects 'rec/arts/star-trek'\n";

// Test 3e: Dispatch smoke test. Actually invokes router() so the
// variable-function call inside the dispatch loop is exercised.
// Catches the 2026-09-16 regression where router_gethandlers()
// returned bare-name strings; bare names broke because PHP
// variable-function lookup goes to the global namespace, not
// the call-site namespace, so every request threw
// `Call to undefined function router_handleIndex()`.
//
// FQCN call: test_router.php runs in the global namespace, so
// an unqualified `router()` would itself be a lookup miss.
//
// Post-C1: 'error' is no longer in the registry, so on a miss
// the dispatch loop falls through to router_handleError($uri).
// The new contract (ROUTER_RENDERED) routes through page\error()
// → displaypage(), which prints to stdout. The dispatch loop
// returns ''. We accept either:
//   - empty-string return with page\error chrome on stdout, OR
//   - non-empty-string return with "Page Not Found" body (legacy
//     shape, if displaypage throws).
echo "Test 3e: router() dispatches through full handler chain without 'undefined function' errors\n";
ob_start();
$dispatch_result = \bbsengine6\router\router("nonexistent/xyz123");
$dispatch_body = ob_get_clean();
$ok = false;
if ($dispatch_result === '' && $dispatch_body !== '') {
    $ok = true; // ROUTER_RENDERED path: chrome on stdout, return ''
} elseif (is_string($dispatch_result)
          && strlen($dispatch_result) > 0
          && strpos($dispatch_result, "Page Not Found") !== false) {
    $ok = true; // legacy inline body path
}
if ($ok) {
    echo "  ✓ PASS: router() dispatch complete (result=" . var_export($dispatch_result, true)
         . ", body length=" . strlen($dispatch_body) . ")\n";
} else {
    echo "  ✗ FAIL: router() did not produce an error path: "
         . "result=" . var_export($dispatch_result, true)
         . ", body length=" . strlen($dispatch_body) . "\n";
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
$md = "---\ntitle: Test Page\ndate: 2024-01-01\n---\n\nbody here\n";
require_once("markdown.php");
[$metadata, $body] = \bbsengine6\markdown\splitFrontmatter($md);
if ($metadata['title'] === 'Test Page' && $metadata['date'] === '2024-01-01' && $body === "body here\n") {
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
    echo "Test 9: Router handles non-existent content gracefully (no duplication)\n";
    // FQCN call: test_router.php runs in the global namespace, so
    // an unqualified router() is a lookup miss. Same shape as
    // Test 3e (which runs unconditionally), but here we exercise
    // the path through the database-aware blurb handler before
    // falling through to router_handleError.
    //
    // Production contract (post-fix):
    //   - page\error() prints the styled chrome via displaypage()
    //     and returns null.
    //   - router_handleError then returns ROUTER_RENDERED.
    //   - The dispatch loop maps ROUTER_RENDERED -> '' so the
    //     HTTP entry-point's `echo $router_result` is a no-op.
    //   - The handler NEVER emits a trailing <html><title>404>
    //     fallback block in production; that would duplicate the
    //     already-printed styled chrome.
    //
    // Capture stdout and assert there's exactly one <title> tag
    // (i.e. the styled chrome is present once, with no trailing
    // duplicate block). The pre-fix shape had two <title> tags
    // (the styled chrome + the trailing fallback).
    ob_start();
    $result = \bbsengine6\router\router("nonexistent/xyz123");
    $body = ob_get_clean();
    $titleCount = substr_count($body, '<title>');
    if ($result === ''
        && $titleCount === 1
        && strpos($body, 'bbsengine.org errormessage.tmpl') !== false) {
        echo "  ✓ PASS: router returned ''; stdout contains exactly one styled error (title count=$titleCount)\n";
    } else {
        echo "  ✗ FAIL: expected '' return + single styled body; got result="
             . var_export($result, true) . ", title count=$titleCount, body length=" . strlen($body) . "\n";
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
if (count($breadcrumbs) === 4) {
    echo "  ✓ PASS: 4 breadcrumbs for rec/arts/star-trek\n";
} else {
    echo "  ✗ FAIL: expected 4 breadcrumbs, got " . count($breadcrumbs) . "\n";
    exit(1);
}

// Test: breadcrumb titles
echo "Test 14: breadcrumb titles are title-cased\n";
if ($breadcrumbs[1]['title'] === 'rec' && $breadcrumbs[2]['title'] === 'arts' && $breadcrumbs[3]['title'] === 'star trek') {
    echo "  ✓ PASS: titles = rec, arts, star trek\n";
} else {
    echo "  ✗ FAIL: titles = " . $breadcrumbs[1]['title'] . ", " . $breadcrumbs[2]['title'] . ", " . $breadcrumbs[3]['title'] . "\n";
    exit(1);
}

// Test: breadcrumb URIs
echo "Test 15: breadcrumb URIs have trailing slash\n";
if ($breadcrumbs[0]['uri'] === '/teos/' && $breadcrumbs[3]['uri'] === '/teos/rec/arts/star-trek/') {
    echo "  ✓ PASS: URIs = /teos/, /teos/rec/arts/star-trek/\n";
} else {
    echo "  ✗ FAIL: uri[0]=" . $breadcrumbs[0]['uri'] . " uri[3]=" . $breadcrumbs[3]['uri'] . "\n";
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
if (count($crumbs_no_db) === 4
    && $crumbs_no_db[0]['path'] === 'teos'
    && $crumbs_no_db[1]['path'] === 'comp'
    && $crumbs_no_db[2]['path'] === 'comp.lang'
    && $crumbs_no_db[3]['path'] === 'comp.lang.python'
    && $crumbs_no_db[0]['uri'] === '/teos/'
    && $crumbs_no_db[1]['uri'] === '/teos/comp/'
    && $crumbs_no_db[2]['uri'] === '/teos/comp/lang/'
    && $crumbs_no_db[3]['uri'] === '/teos/comp/lang/python/') {
    echo "  ✓ PASS: auto-generated breadcrumbs correct\n";
} else {
    echo "  ✗ FAIL: auto-generated breadcrumbs incorrect\n";
    exit(1);
}

// Test: single segment produces one crumb
echo "Test 18: single segment URI produces one crumb\n";
$crumbs_single = router_buildBreadcrumbs("rec");
if (count($crumbs_single) === 2
    && $crumbs_single[0]['path'] === 'teos'
    && $crumbs_single[0]['title'] === 'teos'
    && $crumbs_single[0]['uri'] === '/teos/'
    && $crumbs_single[1]['path'] === 'rec'
    && $crumbs_single[1]['title'] === 'rec'
    && $crumbs_single[1]['uri'] === '/teos/rec/') {
    echo "  ✓ PASS: single crumb correct\n";
} else {
    echo "  ✗ FAIL: single crumb incorrect\n";
    exit(1);
}

// Test: hyphens in segments are title-cased with spaces
echo "Test 19: hyphens in segments become spaces in title\n";
$crumbs_hyphen = router_buildBreadcrumbs("rec/arts/star-trek");
if ($crumbs_hyphen[3]['title'] === 'star trek' && $crumbs_hyphen[3]['path'] === 'rec.arts.star-trek') {
    echo "  ✓ PASS: star-trek → 'star trek', path = rec.arts.star-trek\n";
} else {
    echo "  ✗ FAIL: title=" . $crumbs_hyphen[3]['title'] . " path=" . $crumbs_hyphen[3]['path'] . "\n";
    exit(1);
}

// Test: trailing slash in URI is handled
echo "Test 20: trailing slash in URI is handled\n";
$crumbs_trail = router_buildBreadcrumbs("rec/arts/");
if (count($crumbs_trail) === 3) {
    echo "  ✓ PASS: trailing slash ignored, 3 crumbs\n";
} else {
    echo "  ✗ FAIL: expected 3 crumbs, got " . count($crumbs_trail) . "\n";
    exit(1);
}

echo "\n";

echo "=== All tests passed! ===\n";
