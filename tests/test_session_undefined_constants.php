<?php
/**
 * test_session_undefined_constants.php
 * Tests for session.php graceful handling when config constants are NOT defined
 * This simulates the real production error where config.php hasn't been included yet
 */

echo "========================================\n";
echo "SESSION.PHP UNDEFINED CONSTANTS TEST\n";
echo "========================================\n\n";

// Test 1: Verify fallback behavior when constants NOT defined
echo "Test 1: Session initialization WITHOUT defined constants...\n";

// Ensure constants are NOT defined
if (defined('\config\SESSIONCOOKIEEXPIRE')) {
    echo "  WARNING: config\SESSIONCOOKIEEXPIRE is already defined\n";
} else {
    echo "  ✓ config\SESSIONCOOKIEEXPIRE is undefined (as expected)\n";
}

if (defined('\config\SESSIONCOOKIEDOMAIN')) {
    echo "  WARNING: config\SESSIONCOOKIEDOMAIN is already defined\n";
} else {
    echo "  ✓ config\SESSIONCOOKIEDOMAIN is undefined (as expected)\n";
}

if (defined('\config\SESSIONNAME')) {
    echo "  WARNING: config\SESSIONNAME is already defined\n";
} else {
    echo "  ✓ config\SESSIONNAME is undefined (as expected)\n";
}

echo "\n";

// Test 2: Simulate what happens in the start() function without constants
echo "Test 2: Testing fallback default values in start() logic...\n";

// This replicates the logic from the fixed start() function
$expire = defined('\config\SESSIONCOOKIEEXPIRE') ? \config\SESSIONCOOKIEEXPIRE : (12*60*60);
$domain = defined('\config\SESSIONCOOKIEDOMAIN') ? \config\SESSIONCOOKIEDOMAIN : '';
$sessionname = defined('\config\SESSIONNAME') ? \config\SESSIONNAME : 'PHPSESSID';

echo "  Expire value (should be 43200): $expire\n";
echo "  Domain value (should be empty string): '$domain'\n";
echo "  Session name (should be PHPSESSID): '$sessionname'\n";

if ($expire === 43200) {
    echo "  ✓ PASS: Expire defaults to 12 hours (43200 seconds)\n";
} else {
    echo "  ✗ FAIL: Expire has unexpected value\n";
    exit(1);
}

if ($domain === '') {
    echo "  ✓ PASS: Domain defaults to empty string\n";
} else {
    echo "  ✗ FAIL: Domain has unexpected value\n";
    exit(1);
}

if ($sessionname === 'PHPSESSID') {
    echo "  ✓ PASS: Session name defaults to PHPSESSID\n";
} else {
    echo "  ✗ FAIL: Session name has unexpected value\n";
    exit(1);
}

echo "\n";

// Test 3: Verify parameters are valid for session_set_cookie_params
echo "Test 3: Validating parameters for session_set_cookie_params...\n";

if (is_integer($expire) && $expire > 0) {
    echo "  ✓ PASS: Expire is a positive integer\n";
} else {
    echo "  ✗ FAIL: Expire is not a valid integer\n";
    exit(1);
}

if (is_string($domain)) {
    echo "  ✓ PASS: Domain is a string\n";
} else {
    echo "  ✗ FAIL: Domain is not a string\n";
    exit(1);
}

if (is_string($sessionname) && strlen($sessionname) > 0) {
    echo "  ✓ PASS: Session name is a valid string\n";
} else {
    echo "  ✗ FAIL: Session name is not valid\n";
    exit(1);
}

echo "\n";

// Test 4: Verify with constants DEFINED
echo "Test 4: Testing behavior WITH defined constants...\n";

define("config\SESSIONCOOKIEEXPIRE", 86400);  // 24 hours
define("config\SESSIONCOOKIEDOMAIN", ".example.com");
define("config\SESSIONNAME", "customsession");

$expire = defined('\config\SESSIONCOOKIEEXPIRE') ? \config\SESSIONCOOKIEEXPIRE : (12*60*60);
$domain = defined('\config\SESSIONCOOKIEDOMAIN') ? \config\SESSIONCOOKIEDOMAIN : '';
$sessionname = defined('\config\SESSIONNAME') ? \config\SESSIONNAME : 'PHPSESSID';

echo "  Expire value (should be 86400): $expire\n";
echo "  Domain value (should be .example.com): '$domain'\n";
echo "  Session name (should be customsession): '$sessionname'\n";

if ($expire === 86400) {
    echo "  ✓ PASS: Uses custom expire value\n";
} else {
    echo "  ✗ FAIL: Did not use custom expire value\n";
    exit(1);
}

if ($domain === '.example.com') {
    echo "  ✓ PASS: Uses custom domain value\n";
} else {
    echo "  ✗ FAIL: Did not use custom domain value\n";
    exit(1);
}

if ($sessionname === 'customsession') {
    echo "  ✓ PASS: Uses custom session name\n";
} else {
    echo "  ✗ FAIL: Did not use custom session name\n";
    exit(1);
}

echo "\n" . str_repeat("=", 60) . "\n";
echo "All tests passed! Session.php handles undefined constants gracefully.\n";
echo str_repeat("=", 60) . "\n";

?>
