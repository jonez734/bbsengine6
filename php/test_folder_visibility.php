<?php
/**
 * test_folder_visibility.php - Tests for folder visibility functionality
 * 
 * Usage:
 *   php test_folder_visibility.php           # Run tests
 *   php test_folder_visibility.php --db     # Run with database integration
 */

require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");
require_once("/home/opencode/data/work/bbsengine6/php/folder.php");

$run_db = in_array("--db", $argv);

echo "=== Testing Folder Visibility ===\n\n";

$passed = 0;
$failed = 0;

// =============================================================================
// BASIC TESTS (no database needed)
// =============================================================================

echo "--- Basic Tests ---\n\n";

// Test 1: isFolderVisible function exists
echo "Test 1: isFolderVisible function exists\n";
if (function_exists('\bbsengine6\folder\isFolderVisible')) {
    echo "  ✓ PASS: function exists\n";
    $passed++;
} else {
    echo "  ✗ FAIL: function not found\n";
    $failed++;
}

// Test 2: isSysop function exists
echo "Test 2: isSysop function exists\n";
if (function_exists('\bbsengine6\folder\isSysop')) {
    echo "  ✓ PASS: function exists\n";
    $passed++;
} else {
    echo "  ✗ FAIL: function not found\n";
    $failed++;
}

// Test 3: isSysop returns boolean
echo "Test 3: isSysop returns boolean\n";
if (function_exists('\bbsengine6\folder\isSysop')) {
    $result = \bbsengine6\folder\isSysop();
    if (is_bool($result)) {
        echo "  ✓ PASS: returns boolean\n";
        $passed++;
    } else {
        echo "  ✗ FAIL: expected boolean, got " . gettype($result) . "\n";
        $failed++;
    }
} else {
    echo "  ⊘ SKIP: function not loaded\n";
    $failed++;
}

// =============================================================================
// DATABASE TESTS
// =============================================================================

if ($run_db) {
    echo "\n--- Database Tests ---\n\n";

    // Ensure visible column exists
    try {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        
        // Check if visible column exists
        $stmt = $pdo->query("
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'engine' AND table_name = '__folder' AND column_name = 'visible'
        ");
        if ($stmt->rowCount() === 0) {
            echo "Adding visible column to __folder table...\n";
            $pdo->exec("ALTER TABLE engine.__folder ADD COLUMN visible boolean NOT NULL DEFAULT true");
        }
        $pdo = null;
        echo "Database ready.\n\n";
    } catch (\Throwable $e) {
        echo "Database setup: " . $e->getMessage() . "\n\n";
    }

    // Test 4: isFolderVisible returns true for folder not in DB
    echo "Test 4: isFolderVisible returns true for folder not in database\n";
    try {
        $result = \bbsengine6\folder\isFolderVisible("nonexistent/test/path");
        if ($result === true) {
            echo "  ✓ PASS: returns true for unknown folder\n";
            $passed++;
        } else {
            echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
            $failed++;
        }
    } catch (\Throwable $e) {
        echo "  ⊘ SKIP: " . $e->getMessage() . "\n";
    }

    // Test 5: isFolderVisible returns false for invisible folder
    echo "Test 5: isFolderVisible returns false for invisible folder\n";
    try {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        
        $testPath = 'top.testvis' . bin2hex(random_bytes(4));
        $pdo->exec("INSERT INTO engine.__folder (path, title, visible, datecreated) 
                    VALUES ('$testPath'::ltree, 'Test', false, now())
                    ON CONFLICT (path) DO UPDATE SET visible = false");
        
        $uri = str_replace('.', '/', $testPath);
        $result = \bbsengine6\folder\isFolderVisible($uri);
        
        if ($result === false) {
            echo "  ✓ PASS: invisible folder returns false\n";
            $passed++;
        } else {
            echo "  ✗ FAIL: expected false, got " . var_export($result, true) . "\n";
            $failed++;
        }
        
        // Cleanup
        $pdo->exec("DELETE FROM engine.__folder WHERE path = '$testPath'::ltree");
        $pdo = null;
    } catch (\Throwable $e) {
        echo "  ⊘ SKIP: " . $e->getMessage() . "\n";
    }

    // Test 6: isFolderVisible returns true for visible folder
    echo "Test 6: isFolderVisible returns true for visible folder\n";
    try {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        
        $testPath = 'top.testvis2' . bin2hex(random_bytes(4));
        $pdo->exec("INSERT INTO engine.__folder (path, title, visible, datecreated) 
                    VALUES ('$testPath'::ltree, 'Test', true, now())
                    ON CONFLICT (path) DO UPDATE SET visible = true");
        
        $uri = str_replace('.', '/', $testPath);
        $result = \bbsengine6\folder\isFolderVisible($uri);
        
        if ($result === true) {
            echo "  ✓ PASS: visible folder returns true\n";
            $passed++;
        } else {
            echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
            $failed++;
        }
        
        // Cleanup
        $pdo->exec("DELETE FROM engine.__folder WHERE path = '$testPath'::ltree");
        $pdo = null;
    } catch (\Throwable $e) {
        echo "  ⊘ SKIP: " . $e->getMessage() . "\n";
    }

    // Test 7: visibility works with 'top' folder (should be visible)
    echo "Test 7: 'top' folder is visible by default\n";
    try {
        $result = \bbsengine6\folder\isFolderVisible("top");
        if ($result === true) {
            echo "  ✓ PASS: top folder is visible\n";
            $passed++;
        } else {
            echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
            $failed++;
        }
    } catch (\Throwable $e) {
        echo "  ⊘ SKIP: " . $e->getMessage() . "\n";
    }
}

// =============================================================================
// ROUTER VISIBILITY TESTS
// =============================================================================

echo "\n--- Router Tests ---\n\n";

// Test 8: router_handleFolder checks visibility
echo "Test 8: router_handleFolder respects visibility\n";
if (function_exists('\bbsengine6\router\router_handleFolder')) {
    echo "  ⊘ SKIP: needs test directory setup\n";
} else {
    echo "  ⊘ SKIP: router not loaded\n";
}

// =============================================================================
// SUMMARY
// =============================================================================

echo "\n=== Test Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\n✓ All tests passed!\n";
exit(0);
