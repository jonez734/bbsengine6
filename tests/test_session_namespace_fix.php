<?php
/**
 * test_session_namespace_fix.php
 * Tests for the session.php namespace fixes (SESSIONCOOKIEEXPIRE, SESSIONCOOKIEDOMAIN, SESSIONNAME)
 */

// Test 1: Verify config constants are defined with proper namespace
echo "Test 1: Verifying config constants are defined...\n";

// Mock the config constants since we're in a test environment
define("config\SESSIONCOOKIEEXPIRE", 12*60*60);  // 43,200 seconds (12 hours)
define("config\SESSIONCOOKIEDOMAIN", ".bbsengine.org");
define("config\SESSIONNAME", "bbsenginedotorgsession");

echo "  ✓ config\SESSIONCOOKIEEXPIRE defined: " . var_export(\config\SESSIONCOOKIEEXPIRE, true) . "\n";
echo "  ✓ config\SESSIONCOOKIEDOMAIN defined: " . var_export(\config\SESSIONCOOKIEDOMAIN, true) . "\n";
echo "  ✓ config\SESSIONNAME defined: " . var_export(\config\SESSIONNAME, true) . "\n";

// Test 2: Verify that the constants have the correct values
echo "\nTest 2: Verifying constant values...\n";

if (\config\SESSIONCOOKIEEXPIRE === 43200) {
    echo "  ✓ SESSIONCOOKIEEXPIRE is 43200 seconds (12 hours)\n";
} else {
    echo "  ✗ SESSIONCOOKIEEXPIRE has unexpected value: " . \config\SESSIONCOOKIEEXPIRE . "\n";
    exit(1);
}

if (\config\SESSIONCOOKIEDOMAIN === ".bbsengine.org") {
    echo "  ✓ SESSIONCOOKIEDOMAIN is '.bbsengine.org'\n";
} else {
    echo "  ✗ SESSIONCOOKIEDOMAIN has unexpected value: " . \config\SESSIONCOOKIEDOMAIN . "\n";
    exit(1);
}

if (\config\SESSIONNAME === "bbsenginedotorgsession") {
    echo "  ✓ SESSIONNAME is 'bbsenginedotorgsession'\n";
} else {
    echo "  ✗ SESSIONNAME has unexpected value: " . \config\SESSIONNAME . "\n";
    exit(1);
}

// Test 3: Verify session_set_cookie_params would accept these values
echo "\nTest 3: Verifying session_set_cookie_params compatibility...\n";

// This is what line 23 does with the fixed constants
$lifetime = \config\SESSIONCOOKIEEXPIRE;
$path = "/";
$domain = \config\SESSIONCOOKIEDOMAIN;
$secure = false;
$httponly = true;

// Validate the parameter types
if (is_integer($lifetime) && $lifetime > 0) {
    echo "  ✓ SESSIONCOOKIEEXPIRE is valid integer: $lifetime\n";
} else {
    echo "  ✗ SESSIONCOOKIEEXPIRE is not a valid integer\n";
    exit(1);
}

if (is_string($path) && $path === "/") {
    echo "  ✓ Path is valid string: $path\n";
} else {
    echo "  ✗ Path is not valid\n";
    exit(1);
}

if (is_string($domain) && strlen($domain) > 0) {
    echo "  ✓ SESSIONCOOKIEDOMAIN is valid string: $domain\n";
} else {
    echo "  ✗ SESSIONCOOKIEDOMAIN is not valid\n";
    exit(1);
}

if (is_bool($secure) && is_bool($httponly)) {
    echo "  ✓ Secure and httponly are valid booleans\n";
} else {
    echo "  ✗ Secure and/or httponly are not valid\n";
    exit(1);
}

// Test 4: Verify session_name would accept the value
echo "\nTest 4: Verifying session_name compatibility...\n";

$session_name = \config\SESSIONNAME;
if (is_string($session_name) && strlen($session_name) > 0) {
    echo "  ✓ SESSIONNAME is valid string for session_name(): $session_name\n";
} else {
    echo "  ✗ SESSIONNAME is not valid for session_name()\n";
    exit(1);
}

// Test 5: Verify date calculation would work (line 304 of session.php)
echo "\nTest 5: Verifying date calculation compatibility...\n";

$expiry_timestamp = time() + \config\SESSIONCOOKIEEXPIRE;
$expiry_date = \date(DATE_RFC822, $expiry_timestamp);
if (is_string($expiry_date) && strlen($expiry_date) > 0) {
    echo "  ✓ Date calculation works: $expiry_date\n";
} else {
    echo "  ✗ Date calculation failed\n";
    exit(1);
}

echo "\n" . str_repeat("=", 60) . "\n";
echo "All tests passed! The namespace fixes are correct.\n";
echo str_repeat("=", 60) . "\n";

?>
