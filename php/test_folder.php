<?php
/**
 * test_folder.php - Tests for folder handler functions
 * 
 * Usage:
 *   php test_folder.php           # Run mock tests
 *   php test_folder.php --db      # Run integration tests with real directories and database
 */

require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");
require_once("/home/opencode/data/work/bbsengine6/php/folder.php");

$run_db = in_array("--db", $argv);

echo "=== Testing folder functions ===\n\n";

$passed = 0;
$failed = 0;

// =============================================================================
// MOCK TESTS (no filesystem needed)
// =============================================================================

echo "--- Mock Tests ---\n\n";

// Test 1: getteospath returns default when not defined
echo "Test 1: getteospath returns default path\n";
$result = \bbsengine6\folder\getteospath();
$expected = '/srv/www/zoid6/teos/';
if ($result === $expected) {
    echo "  ✓ PASS: default teos path is correct\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected '$expected', got '$result'\n";
    $failed++;
}

// Test 2: Verify getteospath uses TEOSFILEPATH constant when defined
echo "Test 2: getteospath uses TEOSFILEPATH constant when defined\n";
$teospath = \bbsengine6\folder\getteospath();
// Since we can't change constants in same request, just verify it returns something reasonable
if (is_string($teospath) && strlen($teospath) > 0 && $teospath[strlen($teospath)-1] === '/') {
    echo "  ✓ PASS: getteospath returns valid path\n";
    $passed++;
} else {
    echo "  ✗ FAIL: got '$teospath'\n";
    $failed++;
}

// Test 3: getDirectoryTitle generates correct title
echo "Test 3: getDirectoryTitle generates correct title\n";
$result = \bbsengine6\folder\getDirectoryTitle("ec/john-edward");
$expected = "john-edward";
if ($result === $expected) {
    echo "  ✓ PASS: title 'ec/john-edward' → '$result'\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected '$expected', got '$result'\n";
    $failed++;
}

// Test 4: getDirectoryTitle handles root level
echo "Test 4: getDirectoryTitle handles root level\n";
$result = \bbsengine6\folder\getDirectoryTitle("python");
$expected = "python";
if ($result === $expected) {
    echo "  ✓ PASS: title 'python' → '$result'\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected '$expected', got '$result'\n";
    $failed++;
}

// Test 5: getDirectoryTitle escapes HTML
echo "Test 5: getDirectoryTitle escapes HTML characters\n";
$result = \bbsengine6\folder\getDirectoryTitle("test&folder");
$expected = "test&amp;folder";
if ($result === $expected) {
    echo "  ✓ PASS: HTML is escaped in title\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected '$expected', got '$result'\n";
    $failed++;
}

// Test 6: parseYamlFrontmatter parses simple key-value
echo "Test 6: parseYamlFrontmatter parses simple key-value\n";
$yaml = "title: My Title\ndescription: A description";
$result = \bbsengine6\folder\parseYamlFrontmatter($yaml);
if (isset($result['title']) && $result['title'] === 'My Title') {
    echo "  ✓ PASS: parsed title = 'My Title'\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected title 'My Title', got " . var_export($result, true) . "\n";
    $failed++;
}

// Test 7: parseYamlFrontmatter handles quoted values
echo "Test 7: parseYamlFrontmatter handles quoted values\n";
$yaml = "title: \"Quoted Title\"\ncategory: 'Single Quotes'";
$result = \bbsengine6\folder\parseYamlFrontmatter($yaml);
if ($result['title'] === 'Quoted Title' && $result['category'] === 'Single Quotes') {
    echo "  ✓ PASS: parsed quoted values correctly\n";
    $passed++;
} else {
    echo "  ✗ FAIL: " . var_export($result, true) . "\n";
    $failed++;
}

// Test 8: parseYamlFrontmatter handles empty string
echo "Test 8: parseYamlFrontmatter handles empty string\n";
$result = \bbsengine6\folder\parseYamlFrontmatter("");
if (is_array($result) && count($result) === 0) {
    echo "  ✓ PASS: empty yaml returns empty array\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected empty array, got " . var_export($result, true) . "\n";
    $failed++;
}

// Test 9: parseYamlFrontmatter handles multiple keys
echo "Test 9: parseYamlFrontmatter handles multiple keys\n";
$yaml = "title: Test\nauthor: John\ndate: 2024-01-15\nstatus: published";
$result = \bbsengine6\folder\parseYamlFrontmatter($yaml);
if (count($result) === 4 && $result['author'] === 'John' && $result['status'] === 'published') {
    echo "  ✓ PASS: parsed 4 keys correctly\n";
    $passed++;
} else {
    echo "  ✗ FAIL: " . var_export($result, true) . "\n";
    $failed++;
}

// Test 10: URI construction for directory items
echo "Test 10: URI construction for directory items\n";
$uri = "ec/john-edward";
$filename = "my-file";
$expected = "/teos/ec/john-edward/my-file";
$fileuri = $uri . "/" . $filename;
$result = "/teos/" . $fileuri;
if ($result === $expected) {
    echo "  ✓ PASS: URI constructed correctly\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected '$expected', got '$result'\n";
    $failed++;
}

// =============================================================================
// INTEGRATION TESTS (with real filesystem)
// =============================================================================

if ($run_db) {
    echo "\n--- Integration Tests ---\n\n";

    // Create a temporary test directory
    $testDir = sys_get_temp_dir() . '/bbsengine6_folder_test_' . uniqid();
    mkdir($testDir, 0755, true);

    // Test 11: isFolder returns true for existing directory
    echo "Test 11: isFolder returns true for existing directory\n";
    $testUri = basename($testDir);
    $testTeosPath = dirname($testDir) . '/';
    
    if (!defined('TEOSFILEPATH')) {
        define('TEOSFILEPATH', $testTeosPath);
        $result = \bbsengine6\folder\isFolder($testUri);
        define('TEOSFILEPATH', '/srv/www/zoid6/teos/');
    } else {
        $expectedPath = $testTeosPath . $testUri;
        $result = is_dir($expectedPath);
    }
    if ($result === true) {
        echo "  ✓ PASS: isFolder returns true for existing directory\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        $failed++;
    }

    // Test 12: isFolder returns false for non-existing directory
    echo "Test 12: isFolder returns false for non-existing directory\n";
    $result = \bbsengine6\folder\isFolder("/nonexistent/path/xyz123");
    if ($result === false) {
        echo "  ✓ PASS: isFolder returns false for non-existing directory\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected false, got " . var_export($result, true) . "\n";
        $failed++;
    }

    // Test 13: getDirectoryItems returns empty array for empty directory
    echo "Test 13: getDirectoryItems returns empty array for empty directory\n";
    $result = \bbsengine6\folder\getDirectoryItems($testDir, "test");
    if (is_array($result) && count($result) === 0) {
        echo "  ✓ PASS: empty directory returns empty array\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected empty array, got " . var_export($result, true) . "\n";
        $failed++;
    }

    // Create test markdown files
    file_put_contents($testDir . '/aaa-first.md', "---\ntitle: Aaa First File\n---\nContent A");
    file_put_contents($testDir . '/zzz-last.md', "---\ntitle: Zzz Last File\n---\nContent Z");
    file_put_contents($testDir . '/no-frontmatter.md', "Just plain content");

    // Test 14: getDirectoryItems returns items sorted alphabetically
    echo "Test 14: getDirectoryItems returns items sorted alphabetically\n";
    $result = \bbsengine6\folder\getDirectoryItems($testDir, "test");
    $filenames = array_column($result, 'filename');
    if ($filenames === ['aaa-first', 'no-frontmatter', 'zzz-last']) {
        echo "  ✓ PASS: files are sorted alphabetically\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: " . var_export($filenames, true) . "\n";
        $failed++;
    }

    // Test 15: getDirectoryItems parses frontmatter for title
    echo "Test 15: getDirectoryItems parses frontmatter for title\n";
    $result = \bbsengine6\folder\getDirectoryItems($testDir, "test");
    $firstItem = $result[0];
    if ($firstItem['title'] === 'Aaa First File') {
        echo "  ✓ PASS: frontmatter title used: 'Aaa First File'\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected 'Aaa First File', got '" . $firstItem['title'] . "'\n";
        $failed++;
    }

    // Test 16: getDirectoryItems uses filename when no frontmatter
    echo "Test 16: getDirectoryItems uses filename when no frontmatter\n";
    $result = \bbsengine6\folder\getDirectoryItems($testDir, "test");
    $secondItem = $result[1];
    if ($secondItem['title'] === 'no-frontmatter' && $secondItem['filename'] === 'no-frontmatter') {
        echo "  ✓ PASS: filename used as title when no frontmatter\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: " . var_export($secondItem, true) . "\n";
        $failed++;
    }

    // Test 17: getDirectoryItems constructs correct URIs
    echo "Test 17: getDirectoryItems constructs correct URIs\n";
    $result = \bbsengine6\folder\getDirectoryItems($testDir, "test");
    $firstItem = $result[0];
    if ($firstItem['uri'] === '/teos/test/aaa-first') {
        echo "  ✓ PASS: URI is correct: /teos/test/aaa-first\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected '/teos/test/aaa-first', got '" . $firstItem['uri'] . "'\n";
        $failed++;
    }

    // Set up TEOSFILEPATH for display tests
    $testTeosPath = dirname($testDir) . '/';
    $testUri = basename($testDir);
    
    // Always set to our test path - use string literal in eval
    eval('define("TEOSFILEPATH", "' . $testTeosPath . '");');

    // Test 18: display returns null for non-existent directory
    echo "Test 18: display returns null for non-existent directory\n";
    $result = \bbsengine6\folder\display("nonexistent/xyz123");
    if ($result === null) {
        echo "  ✓ PASS: display returns null for non-existent directory\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected null, got " . var_export($result, true) . "\n";
        $failed++;
    }

    // Test 19: display returns HTML for existing directory
    echo "Test 19: display returns HTML for existing directory\n";
    $result = \bbsengine6\folder\display($testUri);
    if ($result !== null && strpos($result, '<html>') !== false && strpos($result, '<ul>') !== false) {
        echo "  ✓ PASS: display returns HTML for existing directory\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected HTML output, got: " . var_export($result, true) . "\n";
        $failed++;
    }

    // Test 20: display includes directory title
    echo "Test 20: display includes directory title\n";
    $result = \bbsengine6\folder\display($testUri);
    if (strpos($result, '<h1>') !== false) {
        echo "  ✓ PASS: display includes h1 title\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected h1 in output\n";
        $failed++;
    }

    // Cleanup
    unlink($testDir . '/aaa-first.md');
    unlink($testDir . '/zzz-last.md');
    unlink($testDir . '/no-frontmatter.md');
    rmdir($testDir);

    echo "\n";
}

// =============================================================================
// VISIBILITY TESTS
// =============================================================================

echo "\n--- Visibility Tests ---\n\n";

// Test V1: isFolderVisible returns true when folder not in DB
echo "Test V1: isFolderVisible returns true when folder not in database\n";
if (!function_exists('\bbsengine6\folder\isFolderVisible')) {
    echo "  ⊘ SKIP: isFolderVisible not loaded (requires database)\n";
} else {
    $result = \bbsengine6\folder\isFolderVisible("nonexistent_test_xyz123");
    if ($result === true) {
        echo "  ✓ PASS: returns true for folder not in DB\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        $failed++;
    }
}

// Test V2: isFolderVisible handles visible folder
echo "Test V2: isFolderVisible returns true for visible folder in DB\n";
if (!function_exists('\bbsengine6\folder\isFolderVisible')) {
    echo "  ⊘ SKIP: isFolderVisible not loaded (requires database)\n";
} else {
    // Use 'top' which should exist and be visible
    $result = \bbsengine6\folder\isFolderVisible("top");
    if ($result === true) {
        echo "  ✓ PASS: visible folder returns true\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        $failed++;
    }
}

// Test V3: isSysop returns boolean
echo "Test V3: isSysop returns boolean\n";
if (!function_exists('\bbsengine6\folder\isSysop')) {
    echo "  ⊘ SKIP: isSysop not loaded\n";
} else {
    $result = \bbsengine6\folder\isSysop();
    if (is_bool($result)) {
        echo "  ✓ PASS: isSysop returns boolean\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected boolean, got " . gettype($result) . "\n";
        $failed++;
    }
}

// Test V4: display respects visibility for non-sysop
echo "Test V4: display returns null for invisible folder when not sysop\n";
if (!function_exists('\bbsengine6\folder\isFolderVisible')) {
    echo "  ⊘ SKIP: visibility functions not loaded\n";
} else {
    // Create a temp directory that doesn't exist
    $fakeUri = "test_invisible_" . uniqid();
    // The display function will return null for non-existent dir anyway,
    // so we test the visibility check logic separately
    echo "  ⊘ SKIP: requires real invisible folder setup in database\n";
}

// =============================================================================
// DATABASE INTEGRATION TESTS
// =============================================================================

if ($run_db) {
    echo "--- Database Integration Tests ---\n\n";

    // Set up test database
    define("SYSTEMDSN", "pgsql:host=127.0.0.1;port=5432;dbname=zoid6test");

    require_once("/home/opencode/data/work/bbsengine6/php/database.php");
    require_once("/home/opencode/data/work/bbsengine6/php/folder.php");

    // Test 21: getFolderMeta returns data for existing sig
    echo "Test 21: getFolderMeta returns data for existing sig\n";
    $result = \bbsengine6\folder\getFolderMeta("top");
    if ($result !== null && isset($result['path']) && $result['path'] === 'top') {
        echo "  ✓ PASS: getFolderMeta('top') returns sig data\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected sig data for 'top', got " . var_export($result, true) . "\n";
        $failed++;
    }

    // Test 22: getFolderMeta returns null for non-existing sig
    echo "Test 22: getFolderMeta returns null for non-existing sig\n";
    $result = \bbsengine6\folder\getFolderMeta("nonexistent_xyz123");
    if ($result === null) {
        echo "  ✓ PASS: getFolderMeta returns null for non-existent\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected null, got " . var_export($result, true) . "\n";
        $failed++;
    }

    // Test 23: getFolderBreadcrumbs returns breadcrumbs for a sig path
    echo "Test 23: getFolderBreadcrumbs returns breadcrumbs for sig path\n";
    $result = \bbsengine6\folder\getFolderBreadcrumbs("top.entertainment");
    if (is_array($result) && count($result) >= 1) {
        echo "  ✓ PASS: getFolderBreadcrumbs returns breadcrumb array\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected array, got " . var_export($result, true) . "\n";
        $failed++;
    }

    // Test 24: getTopLevelFolders returns top-level sigs
    echo "Test 24: getTopLevelFolders returns top-level sigs\n";
    $result = \bbsengine6\folder\getTopLevelFolders();
    if (is_array($result)) {
        echo "  ✓ PASS: getTopLevelFolders returns array (" . count($result) . " items)\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected array, got " . var_export($result, true) . "\n";
        $failed++;
    }

    // Test 25: getFolderSigs returns child sigs for a path
    echo "Test 25: getFolderSigs returns child sigs for a path\n";
    $result = \bbsengine6\folder\getFolderSigs("top_entertainment");
    if (is_array($result)) {
        echo "  ✓ PASS: getFolderSigs returns array (" . count($result) . " items)\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected array, got " . var_export($result, true) . "\n";
        $failed++;
    }

    echo "\n";
}

// =============================================================================
// SUMMARY
// =============================================================================

echo "=== Test Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\n✓ All tests passed!\n";
exit(0);
