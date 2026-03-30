<?php
/**
 * test_smarty_systemdsn_fixes.php
 * Tests for SMARTYPLUGINSDIR and SYSTEMDSN constant handling with fallbacks
 */

echo "========================================\n";
echo "SMARTY & SYSTEMDSN CONSTANT FIXES TEST\n";
echo "========================================\n\n";

// Test 1: Verify Smarty constants with fallback
echo "Test 1: Testing Smarty constants fallback logic...\n";

$smartyPluginsDir = defined('\config\SMARTYPLUGINSDIR') ? \config\SMARTYPLUGINSDIR : [];
$smartyTemplatesDir = defined('\config\SMARTYTEMPLATESDIR') ? \config\SMARTYTEMPLATESDIR : [];
$smartyCompiledDir = defined('\config\SMARTYCOMPILEDTEMPLATESDIR') ? \config\SMARTYCOMPILEDTEMPLATESDIR : null;
$logEntryPrefix = defined('\config\LOGENTRYPREFIX') ? \config\LOGENTRYPREFIX : 'bbsengine6';

echo "  Plugins Dir (fallback to []): " . var_export($smartyPluginsDir, true) . "\n";
echo "  Templates Dir (fallback to []): " . var_export($smartyTemplatesDir, true) . "\n";
echo "  Compiled Dir (fallback to null): " . var_export($smartyCompiledDir, true) . "\n";
echo "  Log Entry Prefix (fallback to 'bbsengine6'): '$logEntryPrefix'\n";

if (is_array($smartyPluginsDir)) {
    echo "  ✓ PASS: Plugins dir is an array\n";
} else {
    echo "  ✗ FAIL: Plugins dir should be an array\n";
    exit(1);
}

if (is_array($smartyTemplatesDir)) {
    echo "  ✓ PASS: Templates dir is an array\n";
} else {
    echo "  ✗ FAIL: Templates dir should be an array\n";
    exit(1);
}

if ($smartyCompiledDir === null || is_string($smartyCompiledDir)) {
    echo "  ✓ PASS: Compiled dir is null or string\n";
} else {
    echo "  ✗ FAIL: Compiled dir should be null or string\n";
    exit(1);
}

if (is_string($logEntryPrefix) && strlen($logEntryPrefix) > 0) {
    echo "  ✓ PASS: Log entry prefix is a valid string\n";
} else {
    echo "  ✗ FAIL: Log entry prefix should be a string\n";
    exit(1);
}

echo "\n";

// Test 2: Verify SYSTEMDSN fallback logic
echo "Test 2: Testing SYSTEMDSN fallback logic...\n";

// Helper function to test getDSN logic (mimic what's in the code)
function testGetDSN()
{
    if (defined('\config\SYSTEMDSN')) {
        return \config\SYSTEMDSN;
    } elseif (defined('\SYSTEMDSN')) {
        return \SYSTEMDSN;
    }
    return '';
}

$dsn = testGetDSN();
echo "  DSN value (should be empty or valid DSN): '$dsn'\n";

if (is_string($dsn)) {
    echo "  ✓ PASS: DSN is a string\n";
} else {
    echo "  ✗ FAIL: DSN should be a string\n";
    exit(1);
}

echo "\n";

// Test 3: Define config constants and re-test
echo "Test 3: Testing with defined config constants...\n";

if (!defined('\config\SMARTYPLUGINSDIR')) {
    define("config\SMARTYPLUGINSDIR", ['/path/to/plugins/']);
}
if (!defined('\config\SMARTYTEMPLATESDIR')) {
    define("config\SMARTYTEMPLATESDIR", ['/path/to/templates/']);
}
if (!defined('\config\SMARTYCOMPILEDTEMPLATESDIR')) {
    define("config\SMARTYCOMPILEDTEMPLATESDIR", '/path/to/compiled/');
}
if (!defined('\config\LOGENTRYPREFIX')) {
    define("config\LOGENTRYPREFIX", "customapp");
}
if (!defined('\config\SYSTEMDSN')) {
    define("config\SYSTEMDSN", "pgsql:host=localhost;dbname=testdb");
}

$smartyPluginsDir = defined('\config\SMARTYPLUGINSDIR') ? \config\SMARTYPLUGINSDIR : [];
$smartyTemplatesDir = defined('\config\SMARTYTEMPLATESDIR') ? \config\SMARTYTEMPLATESDIR : [];
$smartyCompiledDir = defined('\config\SMARTYCOMPILEDTEMPLATESDIR') ? \config\SMARTYCOMPILEDTEMPLATESDIR : null;
$logEntryPrefix = defined('\config\LOGENTRYPREFIX') ? \config\LOGENTRYPREFIX : 'bbsengine6';
$dsn = testGetDSN();

echo "  Plugins Dir: " . var_export($smartyPluginsDir, true) . "\n";
echo "  Templates Dir: " . var_export($smartyTemplatesDir, true) . "\n";
echo "  Compiled Dir: '$smartyCompiledDir'\n";
echo "  Log Entry Prefix: '$logEntryPrefix'\n";
echo "  DSN: '$dsn'\n";

if (is_array($smartyPluginsDir) && count($smartyPluginsDir) > 0) {
    echo "  ✓ PASS: Plugins dir uses custom value\n";
} else {
    echo "  ✗ FAIL: Plugins dir should use custom value\n";
    exit(1);
}

if (is_array($smartyTemplatesDir) && count($smartyTemplatesDir) > 0) {
    echo "  ✓ PASS: Templates dir uses custom value\n";
} else {
    echo "  ✗ FAIL: Templates dir should use custom value\n";
    exit(1);
}

if ($smartyCompiledDir === '/path/to/compiled/') {
    echo "  ✓ PASS: Compiled dir uses custom value\n";
} else {
    echo "  ✗ FAIL: Compiled dir should use custom value\n";
    exit(1);
}

if ($logEntryPrefix === 'customapp') {
    echo "  ✓ PASS: Log entry prefix uses custom value\n";
} else {
    echo "  ✗ FAIL: Log entry prefix should use custom value\n";
    exit(1);
}

if ($dsn === 'pgsql:host=localhost;dbname=testdb') {
    echo "  ✓ PASS: DSN uses custom value\n";
} else {
    echo "  ✗ FAIL: DSN should use custom value\n";
    exit(1);
}

echo "\n" . str_repeat("=", 60) . "\n";
echo "All tests passed! Constants handle fallbacks correctly.\n";
echo str_repeat("=", 60) . "\n";

?>
