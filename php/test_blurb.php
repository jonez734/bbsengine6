<?php
/**
 * test_blurb.php - Tests for blurb handler functions
 * 
 * Usage:
 *   php test_blurb.php           # Run mock tests
 *   php test_blurb.php --db       # Run database integration tests
 */

require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");

$run_db = in_array("--db", $argv);

echo "=== Testing blurb functions ===\n\n";

// =============================================================================
// MOCK TESTS (no database)
// =============================================================================

echo "--- Mock Tests ---\n\n";

// Test 1: URI to blurbID conversion
echo "Test 1: URI to blurbID conversion\n";
$uri = "ec/john-edward";
$expected = "ec.john-edward";
$actual = str_replace("/", ".", preg_replace('/\.md$/', '', $uri));
if ($actual === $expected) {
    echo "  ✓ PASS: ec/john-edward → ec.john-edward\n";
} else {
    echo "  ✗ FAIL: expected '$expected', got '$actual'\n";
    exit(1);
}

// Test 2: Strips .md extension
echo "Test 2: Strip .md extension\n";
$uri = "ec/john-edward.md";
$expected = "ec/john-edward";
$actual = preg_replace('/\.md$/', '', $uri);
if ($actual === $expected) {
    echo "  ✓ PASS: ec/john-edward.md → ec/john-edward\n";
} else {
    echo "  ✗ FAIL: expected '$expected', got '$actual'\n";
    exit(1);
}

// Test 3: Full blurbID generation from filepath
echo "Test 3: Full blurbID generation from filepath\n";
$filepath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/ec/john-edward.md";
$teospath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/";
$relative = str_replace($teospath, "", $filepath);
$blurbid = preg_replace('/\.md$/', '', $relative);
$blurbid = str_replace("/", ".", $blurbid);
if ($blurbid === "ec.john-edward") {
    echo "  ✓ PASS: /srv/www/vhosts/zoidtechnologies.com/html/teos/ec/john-edward.md → ec.john-edward\n";
} else {
    echo "  ✗ FAIL: expected 'ec.john-edward', got '$blurbid'\n";
    exit(1);
}

// Test 4: Nested path conversion
echo "Test 4: Nested path conversion\n";
$filepath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/comp/lang/python/intro.md";
$teospath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/";
$relative = str_replace($teospath, "", $filepath);
$blurbid = preg_replace('/\.md$/', '', $relative);
$blurbid = str_replace("/", ".", $blurbid);
if ($blurbid === "comp.lang.python.intro") {
    echo "  ✓ PASS: Nested path converts correctly\n";
} else {
    echo "  ✗ FAIL: expected 'comp.lang.python.intro', got '$blurbid'\n";
    exit(1);
}

// Test 5: Root-level file
echo "Test 5: Root-level file\n";
$filepath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/about.md";
$teospath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/";
$relative = str_replace($teospath, "", $filepath);
$blurbid = preg_replace('/\.md$/', '', $relative);
$blurbid = str_replace("/", ".", $blurbid);
if ($blurbid === "about") {
    echo "  ✓ PASS: Root-level file converts correctly\n";
} else {
    echo "  ✗ FAIL: expected 'about', got '$blurbid'\n";
    exit(1);
}

echo "\n";

// =============================================================================
// DATABASE INTEGRATION TESTS
// =============================================================================

if ($run_db) {
    echo "--- Database Integration Tests ---\n\n";
    
    // Set up test database
    define("SYSTEMDSN", "pgsql:host=127.0.0.1;port=5432;dbname=zoid6test");
    
    require_once("/home/opencode/data/work/bbsengine6/php/database.php");
    require_once("/home/opencode/data/work/bbsengine6/php/blurb.php");
    
    // Test 1: isBlurb returns true for existing blurb
    echo "Test 6: isBlurb returns true for existing blurb\n";
    $result = \bbsengine6\blurb\isBlurb("ec.biblical-prophets-mediumship-prophecy");
    if ($result === true) {
        echo "  ✓ PASS: isBlurb('ec.biblical-prophets-mediumship-prophecy') = true\n";
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        exit(1);
    }
    
    // Test 2: isBlurb returns false for non-existing blurb
    echo "Test 7: isBlurb returns false for non-existing blurb\n";
    $result = \bbsengine6\blurb\isBlurb("nonexistent.blah");
    if ($result === false) {
        echo "  ✓ PASS: isBlurb('nonexistent.blah') = false\n";
    } else {
        echo "  ✗ FAIL: expected false, got " . var_export($result, true) . "\n";
        exit(1);
    }
    
    // Test 3: isBlurb handles .md suffix
    echo "Test 8: isBlurb handles .md suffix\n";
    $result = \bbsengine6\blurb\isBlurb("ec.biblical-prophets-mediumship-prophecy.md");
    if ($result === true) {
        echo "  ✓ PASS: isBlurb handles .md suffix\n";
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        exit(1);
    }
    
    // Test 4: isBlurb with nested path
    echo "Test 9: isBlurb with nested path\n";
    // Create a nested path blurb for testing (using existing member)
    $pdo = \bbsengine6\database\connect(SYSTEMDSN);
    $pdo->exec("INSERT INTO engine.__blurb (id, kind, attributes, contentfilename, datecreated, createdbymoniker) 
                VALUES ('comp.lang.python', 'markdown', '{\"title\": \"Python\"}', 'comp/lang/python.md', NOW(), 'jam') 
                ON CONFLICT (id) DO NOTHING");
    
    $result = \bbsengine6\blurb\isBlurb("comp.lang.python");
    if ($result === true) {
        echo "  ✓ PASS: isBlurb('comp.lang.python') = true\n";
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        exit(1);
    }
    
    echo "\n";
}

echo "=== All tests passed! ===\n";
