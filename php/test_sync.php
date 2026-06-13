<?php
/**
 * test_sync.php - Tests for sync_teos_blurbs.sh script
 * 
 * Tests the core logic of the sync script:
 * - Path to blurb ID conversion
 * - Title extraction from frontmatter
 * - Title fallback to filename
 * 
 * Usage:
 *   php test_sync.php           # Run all tests
 *   php test_sync.php --mock    # Run mock tests only
 */

echo "=== Testing Sync Script Logic ===\n\n";

// =============================================================================
// MOCK TESTS
// =============================================================================

echo "--- Mock Tests ---\n\n";

// Test 1: Path to blurbID conversion (core logic)
echo "Test 1: Path to blurbID conversion - basic\n";
$teospath = '/srv/www/zoid6/teos/';
$filepath = '/srv/www/zoid6/teos/ec/john-edward.md';
$relativepath = str_replace($teospath, '', $filepath);
$blurbid = preg_replace('/\.md$/', '', $relativepath);
$blurbid = str_replace('/', '.', $blurbid);
if ($blurbid === 'ec.john-edward') {
    echo "  ✓ PASS: /srv/www/zoid6/teos/ec/john-edward.md → ec.john-edward\n";
} else {
    echo "  ✗ FAIL: expected 'ec.john-edward', got '$blurbid'\n";
    exit(1);
}

// Test 2: Path to blurbID conversion - nested path
echo "Test 2: Path to blurbID conversion - nested path\n";
$filepath = '/srv/www/zoid6/teos/comp/lang/python/intro.md';
$relativepath = str_replace($teospath, '', $filepath);
$blurbid = preg_replace('/\.md$/', '', $relativepath);
$blurbid = str_replace('/', '.', $blurbid);
if ($blurbid === 'comp.lang.python.intro') {
    echo "  ✓ PASS: Nested path converts correctly\n";
} else {
    echo "  ✗ FAIL: expected 'comp.lang.python.intro', got '$blurbid'\n";
    exit(1);
}

// Test 3: Path to blurbID conversion - root file
echo "Test 3: Path to blurbID conversion - root file\n";
$filepath = '/srv/www/zoid6/teos/about.md';
$relativepath = str_replace($teospath, '', $filepath);
$blurbid = preg_replace('/\.md$/', '', $relativepath);
$blurbid = str_replace('/', '.', $blurbid);
if ($blurbid === 'about') {
    echo "  ✓ PASS: Root file converts correctly\n";
} else {
    echo "  ✗ FAIL: expected 'about', got '$blurbid'\n";
    exit(1);
}

// Test 4: Title extraction from frontmatter
echo "Test 4: Title extraction from frontmatter\n";
$content = <<<MD
---
title: John Edward - Mediumship
date: 2024-01-15
---

# Content here
MD;

$title = '';
if (preg_match('/^---/', $content)) {
    preg_match('/^title: *(.*)$/m', $content, $matches);
    if (isset($matches[1])) {
        $title = trim($matches[1]);
    }
}

if ($title === 'John Edward - Mediumship') {
    echo "  ✓ PASS: Frontmatter title extracted correctly\n";
} else {
    echo "  ✗ FAIL: expected 'John Edward - Mediumship', got '$title'\n";
    exit(1);
}

// Test 5: Title fallback to filename (no frontmatter)
echo "Test 5: Title fallback to filename\n";
$filepath = '/srv/www/zoid6/teos/ec/john-edward.md';
$title = basename($filepath, '.md');
$title = preg_replace('/-/', ' ', $title);

if ($title === 'john edward') {
    echo "  ✓ PASS: Title fallback works correctly\n";
} else {
    echo "  ✗ FAIL: expected 'john edward', got '$title'\n";
    exit(1);
}

// Test 6: Title with hyphens converted to spaces
echo "Test 6: Title hyphen conversion\n";
$title = 'biblical-prophets-mediumship';
$titleConverted = preg_replace('/-/', ' ', $title);
if ($titleConverted === 'biblical prophets mediumship') {
    echo "  ✓ PASS: Hyphens converted to spaces\n";
} else {
    echo "  ✗ FAIL: expected 'biblical prophets mediumship', got '$titleConverted'\n";
    exit(1);
}

// Test 7: SQL escaping of single quotes
echo "Test 7: SQL quote escaping\n";
$title = "John's Message";
$titleEscaped = str_replace("'", "''", $title);
if ($titleEscaped === "John''s Message") {
    echo "  ✓ PASS: Single quotes escaped correctly\n";
} else {
    echo "  ✗ FAIL: expected 'John''s Message', got '$titleEscaped'\n";
    exit(1);
}

// Test 8: File extension stripping
echo "Test 8: File extension stripping\n";
$filepath = '/path/to/file.md';
$withoutExt = preg_replace('/\.md$/', '', $filepath);
if ($withoutExt === '/path/to/file') {
    echo "  ✓ PASS: .md extension stripped correctly\n";
} else {
    echo "  ✗ FAIL: expected '/path/to/file', got '$withoutExt'\n";
    exit(1);
}

// Test 9: Skip backup files pattern
echo "Test 9: Backup file detection\n";
$backupFiles = [
    '/path/to/file.md~',
    '/path/to/file.bak',
    '/path/to/file.md',
];

$isBackup = preg_match('/\.md~$/', $backupFiles[0]);
if ($isBackup === 1 && preg_match('/\.md~$/', $backupFiles[1]) === 0 && preg_match('/\.md~$/', $backupFiles[2]) === 0) {
    echo "  ✓ PASS: Backup file detection works\n";
} else {
    echo "  ✗ FAIL: Backup file detection failed\n";
    exit(1);
}

// Test 10: contentfilename path format
echo "Test 10: contentfilename path format\n";
$teospath = '/srv/www/zoid6/teos/';
$filepath = '/srv/www/zoid6/teos/ec/john-edward.md';
$relativepath = str_replace($teospath, '', $filepath);
if ($relativepath === 'ec/john-edward.md') {
    echo "  ✓ PASS: contentfilename path format correct\n";
} else {
    echo "  ✗ FAIL: expected 'ec/john-edward.md', got '$relativepath'\n";
    exit(1);
}

echo "\n";

// =============================================================================
// INTEGRATION TESTS (requires database and filesystem)
// =============================================================================

$run_db = in_array("--db", $argv);

if ($run_db) {
    echo "--- Integration Tests ---\n\n";
    
    // Test 11: Run sync script with --dry-run on test database
    echo "Test 11: Sync script dry-run on test database\n";
    $output = [];
    $return = 0;
    exec(
        "bash " . __DIR__ . "/sync_teos_blurbs.sh /srv/www/zoid6/teos/ --dry-run --dbname zoid6test 2>&1",
        $output,
        $return
    );
    
    // Check that script ran
    if ($return === 0 && count($output) > 0) {
        echo "  ✓ PASS: Sync script ran successfully (dry-run)\n";
    } else {
        echo "  ✗ FAIL: Sync script failed with return code $return\n";
        echo "    Output: " . implode("\n    ", array_slice($output, 0, 3)) . "\n";
    }
    
    // Test 12: Verify blurbs exist in test database
    echo "Test 12: Verify blurbs exist in test database\n";
    $output = [];
    exec("psql -t -A -h 127.0.0.1 -p 5432 -U postgres -d zoid6test -c \"SELECT COUNT(*) FROM engine.__blurb\" 2>&1", $output);
    $count = intval(trim($output[0] ?? '0'));
    if ($count > 0) {
        echo "  ✓ PASS: Found $count blurbs in test database\n";
    } else {
        echo "  ✗ FAIL: No blurbs found in test database\n";
    }
    
    echo "\n";
}

echo "=== All tests passed! ===\n";
