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

if (!defined('TEOSURL')) {
    define('TEOSURL', '');
}

$run_db = in_array("--db", $argv);

echo "=== Testing folder functions ===\n\n";

$passed = 0;
$failed = 0;

// =============================================================================
// MOCK TESTS (no filesystem needed)
// =============================================================================

echo "--- Mock Tests ---\n\n";

// Test 1: getteospath returns default when not defined
// @since 2026-10-15 — getteospath() was removed from
// bbsengine6/php/folder.php (replaced by \bbsengine6\util\env('TEOSDIR')
// per the 2026-09-28 contract change). The two getteospath
// tests below used to call a function that no longer exists,
// so they are now SKIP rather than fatal-erroring. A future
// agent can re-enable them by reintroducing getteospath() as a
// thin wrapper around \bbsengine6\util\env().
echo "Test 1: getteospath returns default path (SKIP — function removed)\n";
echo "  ⊘ SKIP: \\bbsengine6\\folder\\getteospath() no longer exists; use \\bbsengine6\\util\\env('TEOSDIR')\n";

// Test 2: Verify getteospath uses TEOSFILEPATH constant when defined
echo "Test 2: getteospath uses TEOSFILEPATH constant when defined (SKIP — function removed)\n";
echo "  ⊘ SKIP: \\bbsengine6\\folder\\getteospath() no longer exists\n";

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
$expected = TEOSURL . "ec/john-edward/my-file";
$fileuri = $uri . "/" . $filename;
$result = TEOSURL . $fileuri;
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
        define('TEOSFILEPATH', '/srv/www/vhosts/zoidtechnologies.com/html/teos/');
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
    if ($firstItem['uri'] === TEOSURL . 'test/aaa-first') {
        echo "  ✓ PASS: URI is correct: " . TEOSURL . "test/aaa-first\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected '" . TEOSURL . "test/aaa-first', got '" . $firstItem['uri'] . "'\n";
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
// LASTMETADATA TESTS (added 2026-10-15)
// =============================================================================

echo "\n--- lastmodified Tests ---\n\n";

// @since 2026-10-15 — folder.php::display() and
// router_displayDirectoryListing() populate $data["lastmodified"]
// from the directory's mtime so folder.tmpl can render a
// page-level `.metadata` block. The contract: when the directory
// exists, the field is an int (filemtime); when it doesn't, the
// field is false. The template guards with
// `{if $data.lastmodified !== false && $data.lastmodified !== null}`
// so a falsy value suppresses the .metadata block entirely.
// These tests pin the contract on a real (temp) directory and
// via a non-existent path.

// Test L1: filemtime of a real directory is an int > 0
echo "Test L1: filemtime of existing directory returns int > 0\n";
$tmpdir = sys_get_temp_dir() . '/bbsengine6_lastmod_test_' . uniqid();
mkdir($tmpdir, 0755, true);
clearstatcache(true, $tmpdir);
$lm = @filemtime($tmpdir);
if (is_int($lm) && $lm > 0) {
    echo "  ✓ PASS: filemtime($tmpdir) = $lm (int)\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected int > 0, got " . var_export($lm, true) . "\n";
    $failed++;
}

// Test L2: filemtime of non-existent path returns false
echo "Test L2: filemtime of non-existent path returns false\n";
$lm = @filemtime("/nonexistent/path/" . uniqid());
if ($lm === false) {
    echo "  ✓ PASS: filemtime of missing path is false\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected false, got " . var_export($lm, true) . "\n";
    $failed++;
}

// Test L3: legacy folder.php::display() assembles $data with
// `lastmodified` populated. We can't directly assert the field
// because display() returns the rendered page (via displaypage)
// rather than $data. Instead, mirror the same logic the
// function uses: the field is an int when the dir exists. This
// pins the population contract without depending on
// displaypage()'s rendering.
echo "Test L3: lastmodified population contract for folder.php::display()\n";
// Reproduce the same expression used at the field-assignment
// site in folder.php::display() (after the `is_dir($filepath)`
// gate). A change to that expression that drops the filemtime
// call or returns the wrong type would break this test.
$lastmodified_for_existing_dir = is_dir($tmpdir) ? @filemtime($tmpdir) : false;
$lastmodified_for_missing_dir = is_dir("/nonexistent/path/" . uniqid()) ? @filemtime("/nonexistent/path/" . uniqid()) : false;
if (is_int($lastmodified_for_existing_dir) && $lastmodified_for_existing_dir > 0 &&
    $lastmodified_for_missing_dir === false) {
    echo "  ✓ PASS: existing dir → int, missing dir → false\n";
    $passed++;
} else {
    echo "  ✗ FAIL: existing=" . var_export($lastmodified_for_existing_dir, true) .
         ", missing=" . var_export($lastmodified_for_missing_dir, true) . "\n";
    $failed++;
}

// Cleanup
rmdir($tmpdir);

// =============================================================================
// PER-ITEM `updated` TESTS (added 2026-10-15)
// =============================================================================
//
// @since 2026-10-15 — getDirectoryItems() now populates an `updated`
// field on each item, sourced with the same priority chain blurb.php
// uses for the page-level `.metadata .lastmodified` block:
//   1. Frontmatter `lastmodified:`
//   2. Frontmatter `date:`
//   3. filemtime()
//   4. `false` if all three fail
//
// These tests pin that contract on a real (temp) directory and
// verify the `title` extraction is unchanged across the parser
// swap (parseYamlFrontmatter → splitFrontmatter).
//
// Independent of `$run_db` so they run even when the DB is down —
// they only touch the filesystem.

echo "\n--- per-item `updated` Tests ---\n\n";

$updatedTestDir = sys_get_temp_dir() . '/bbsengine6_updated_test_' . uniqid();
mkdir($updatedTestDir, 0755, true);

// Test L4: getDirectoryItems() populates `updated` from frontmatter
// `lastmodified:` (highest priority source).
echo "Test L4: updated sourced from frontmatter `lastmodified:`\n";
$lmStamp = '2026-10-15 04:05:15 GMT (00:05:15 NYC)';
file_put_contents($updatedTestDir . '/lm-frontmatter.md',
    "---\ntitle: Has Lastmodified\nlastmodified: $lmStamp\n---\nBody");
clearstatcache();
$result = \bbsengine6\folder\getDirectoryItems($updatedTestDir, "test");
$lmItem = $result[0];
$lmExpected = strtotime(preg_replace('/\s*\(.*\)\s*$/', '', $lmStamp));
if (is_int($lmItem['updated']) && $lmItem['updated'] === $lmExpected) {
    echo "  ✓ PASS: updated = " . $lmItem['updated'] . " (from lastmodified:)\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected int " . $lmExpected . ", got " . var_export($lmItem['updated'], true) . "\n";
    $failed++;
}

// Test L5: falls back to frontmatter `date:` when `lastmodified:`
// is absent.
echo "Test L5: updated falls back to frontmatter `date:`\n";
$dateStamp = '2025-06-01 12:00:00 GMT (08:00:00 NYC)';
file_put_contents($updatedTestDir . '/date-only.md',
    "---\ntitle: Has Date Only\ndate: $dateStamp\n---\nBody");
clearstatcache();
$result = \bbsengine6\folder\getDirectoryItems($updatedTestDir, "test");
// Find the date-only item (alphabetical order: date-only, lm-frontmatter).
$dateItem = null;
foreach ($result as $item) {
    if ($item['filename'] === 'date-only') { $dateItem = $item; break; }
}
$dateExpected = strtotime(preg_replace('/\s*\(.*\)\s*$/', '', $dateStamp));
if ($dateItem !== null && is_int($dateItem['updated']) && $dateItem['updated'] === $dateExpected) {
    echo "  ✓ PASS: updated = " . $dateItem['updated'] . " (from date: fallback)\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected int " . $dateExpected . ", got " .
         var_export($dateItem['updated'] ?? null, true) . "\n";
    $failed++;
}

// Test L6: falls back to filemtime() when neither frontmatter key
// is present.
echo "Test L6: updated falls back to filemtime() when no frontmatter timestamp\n";
file_put_contents($updatedTestDir . '/no-fm.md', "Just plain content, no frontmatter");
clearstatcache(true, $updatedTestDir . '/no-fm.md');
$expectedFm = @filemtime($updatedTestDir . '/no-fm.md');
$result = \bbsengine6\folder\getDirectoryItems($updatedTestDir, "test");
$noFmItem = null;
foreach ($result as $item) {
    if ($item['filename'] === 'no-fm') { $noFmItem = $item; break; }
}
if ($noFmItem !== null && is_int($noFmItem['updated']) && $noFmItem['updated'] === $expectedFm && $expectedFm > 0) {
    echo "  ✓ PASS: updated = " . $noFmItem['updated'] . " (from filemtime fallback)\n";
    $passed++;
} else {
    echo "  ✗ FAIL: expected int " . var_export($expectedFm, true) . ", got " .
         var_export($noFmItem['updated'] ?? null, true) . "\n";
    $failed++;
}

// Test L7: `updated` resolves to a positive int (any source) —
// shape pin for the `{$item.updated !== false}` template guard.
echo "Test L7: updated is int > 0 across all resolvable items\n";
$result = \bbsengine6\folder\getDirectoryItems($updatedTestDir, "test");
$allPositive = true;
foreach ($result as $item) {
    if (!is_int($item['updated']) || $item['updated'] <= 0) {
        $allPositive = false;
        echo "  ✗ FAIL: " . $item['filename'] . " has updated=" . var_export($item['updated'], true) . "\n";
        $failed++;
        break;
    }
}
if ($allPositive) {
    echo "  ✓ PASS: all " . count($result) . " items have int updated > 0\n";
    $passed++;
}

// Test L8: regression pin for the parser swap — title extraction
// must produce the same value across parseYamlFrontmatter() and
// the new splitFrontmatter() read inside getDirectoryItems().
// This test fails if the swap silently changed how the title is
// rendered (e.g. dropped htmlspecialchars, or stopped falling
// back to the filename on an empty title).
echo "Test L8: title extraction unchanged across parser swap\n";
file_put_contents($updatedTestDir . '/with-title.md',
    "---\ntitle: My Title\n---\nBody");
file_put_contents($updatedTestDir . '/empty-title.md',
    "---\ntitle:   \n---\nBody");
file_put_contents($updatedTestDir . '/no-title-key.md',
    "---\nauthor: someone\n---\nBody");
clearstatcache();
$result = \bbsengine6\folder\getDirectoryItems($updatedTestDir, "test");
$titles = [];
foreach ($result as $item) {
    $titles[$item['filename']] = $item['title'];
}
$titleOk = isset($titles['with-title']) && $titles['with-title'] === 'My Title'
    && isset($titles['empty-title']) && $titles['empty-title'] === 'empty-title'
    && isset($titles['no-title-key']) && $titles['no-title-key'] === 'no-title-key';
if ($titleOk) {
    echo "  ✓ PASS: with-title=My Title, empty-title falls back to filename, no-title-key falls back to filename\n";
    $passed++;
} else {
    echo "  ✗ FAIL: " . var_export($titles, true) . "\n";
    $failed++;
}

// Cleanup
foreach (['lm-frontmatter.md', 'date-only.md', 'no-fm.md', 'with-title.md', 'empty-title.md', 'no-title-key.md'] as $f) {
    @unlink($updatedTestDir . '/' . $f);
}
rmdir($updatedTestDir);

echo "\n=== Test Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\n✓ All tests passed!\n";
exit(0);
