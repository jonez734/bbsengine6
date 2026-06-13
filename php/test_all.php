<?php
/**
 * test_all.php - Master test runner for bbsengine6 PHP tests
 * 
 * Usage:
 *   php test_all.php           # Run all tests
 *   php test_all.php --mock    # Run mock tests only
 *   php test_all.php --db      # Run with database tests
 */

$run_mock = in_array("--mock", $argv);
$run_db = in_array("--db", $argv);

// If no flags, run everything
if (!$run_mock && !$run_db) {
    $run_mock = true;
    $run_db = true;
}

echo "=== BBSEngine6 PHP Test Suite ===\n\n";

$passed = 0;
$failed = 0;

// Run blurb tests
echo "--- Blurb Tests ---\n";
if ($run_mock) {
    echo "Running mock tests...\n";
    $output = [];
    $return = 0;
    exec("php " . __DIR__ . "/test_blurb.php 2>&1", $output, $return);
    if ($return === 0) {
        echo "  ✓ test_blurb.php (mock) PASSED\n";
        $passed++;
    } else {
        echo "  ✗ test_blurb.php (mock) FAILED\n";
        echo "    " . implode("\n    ", array_slice($output, 0, 5)) . "\n";
        $failed++;
    }
}

if ($run_db) {
    echo "Running database tests...\n";
    $output = [];
    $return = 0;
    exec("php " . __DIR__ . "/test_blurb.php --db 2>&1", $output, $return);
    if ($return === 0) {
        echo "  ✓ test_blurb.php (db) PASSED\n";
        $passed++;
    } else {
        echo "  ✗ test_blurb.php (db) FAILED\n";
        echo "    " . implode("\n    ", array_slice($output, 0, 5)) . "\n";
        $failed++;
    }
}

echo "\n";

// Run router tests
echo "--- Router Tests ---\n";
if ($run_mock) {
    echo "Running mock tests...\n";
    $output = [];
    $return = 0;
    exec("php " . __DIR__ . "/test_router.php 2>&1", $output, $return);
    if ($return === 0) {
        echo "  ✓ test_router.php (mock) PASSED\n";
        $passed++;
    } else {
        echo "  ✗ test_router.php (mock) FAILED\n";
        echo "    " . implode("\n    ", array_slice($output, 0, 5)) . "\n";
        $failed++;
    }
}

if ($run_db) {
    echo "Running database tests...\n";
    $output = [];
    $return = 0;
    exec("php " . __DIR__ . "/test_router.php --db 2>&1", $output, $return);
    if ($return === 0) {
        echo "  ✓ test_router.php (db) PASSED\n";
        $passed++;
    } else {
        echo "  ✗ test_router.php (db) FAILED\n";
        echo "    " . implode("\n    ", array_slice($output, 0, 5)) . "\n";
        $failed++;
    }
}

echo "\n";

// Run folder tests
echo "--- Folder Tests ---\n";
if ($run_mock) {
    echo "Running mock tests...\n";
    $output = [];
    $return = 0;
    exec("php " . __DIR__ . "/test_folder.php 2>&1", $output, $return);
    if ($return === 0) {
        echo "  ✓ test_folder.php (mock) PASSED\n";
        $passed++;
    } else {
        echo "  ✗ test_folder.php (mock) FAILED\n";
        echo "    " . implode("\n    ", array_slice($output, 0, 5)) . "\n";
        $failed++;
    }
}

if ($run_db) {
    echo "Running integration tests...\n";
    $output = [];
    $return = 0;
    exec("php " . __DIR__ . "/test_folder.php --db 2>&1", $output, $return);
    if ($return === 0) {
        echo "  ✓ test_folder.php (db) PASSED\n";
        $passed++;
    } else {
        echo "  ✗ test_folder.php (db) FAILED\n";
        echo "    " . implode("\n    ", array_slice($output, 0, 5)) . "\n";
        $failed++;
    }
}

echo "\n";

// Run sync script tests
echo "--- Sync Script Tests ---\n";
if ($run_mock) {
    echo "Running mock tests...\n";
    $output = [];
    $return = 0;
    exec("php " . __DIR__ . "/test_sync.php 2>&1", $output, $return);
    if ($return === 0) {
        echo "  ✓ test_sync.php (mock) PASSED\n";
        $passed++;
    } else {
        echo "  ✗ test_sync.php (mock) FAILED\n";
        echo "    " . implode("\n    ", array_slice($output, 0, 5)) . "\n";
        $failed++;
    }
}

if ($run_db) {
    echo "Running database tests...\n";
    $output = [];
    $return = 0;
    exec("php " . __DIR__ . "/test_sync.php --db 2>&1", $output, $return);
    if ($return === 0) {
        echo "  ✓ test_sync.php (db) PASSED\n";
        $passed++;
    } else {
        echo "  ✗ test_sync.php (db) FAILED\n";
        echo "    " . implode("\n    ", array_slice($output, 0, 5)) . "\n";
        $failed++;
    }
}

echo "\n";
echo "=== Test Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\n✓ All tests passed!\n";
exit(0);
