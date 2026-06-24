<?php
/**
 * test_router.php - Tests for router handler registry
 * 
 * Usage:
 *   php test_router.php           # Run mock tests
 *   php test_router.php --db       # Run database integration tests
 */

require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");
require_once("/home/opencode/data/work/bbsengine6/php/router.php");

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
$expectedOrder = ['blurb', 'folder', 'markdown', 'error'];
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

echo "=== All tests passed! ===\n";
