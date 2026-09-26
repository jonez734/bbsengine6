<?php
/**
 * test_smarty_pluginsdir.php — Verifies the bbsengine6/smarty/
 * plugin-dir fallback is wired through the
 * \bbsengine6\template\plugin registry.
 *
 * The {teos} Smarty plugin (function.teos.php) lives in
 * bbsengine6/smarty/. All sites must be able to find it via
 * SMARTYPLUGINSDIR. The engine's canonical plugin-dir
 * contribution is exposed by \bbsengine6\template\plugin\extra()
 * (in php/bbsengine6config.php) and auto-registered at
 * PRIORITY_ENGINE. engine.php::getsmarty() delegates to
 * \bbsengine6\template\plugin\normalize() to materialize the
 * final path.
 *
 * Usage:
 *   php test_smarty_pluginsdir.php
 */

require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");

echo "=== SMARTYPLUGINSDIR Tests ===\n\n";

$passed = 0;
$failed = 0;

function test_pass(string $name, string $detail = '') {
    global $passed;
    $passed++;
    $suffix = $detail ? ": $detail" : '';
    echo "  ✓ PASS: $name$suffix\n";
}

function test_fail(string $name, string $detail = ''): never {
    global $failed;
    $failed++;
    $suffix = $detail ? " — $detail" : '';
    echo "  ✗ FAIL: $name$suffix\n";
    exit(1);
}

$BBSENGINE6_SMARTY = "/srv/www/bbsengine6/smarty/";

// =============================================================================
// zoid6config.php CENTRAL ENFORCEMENT
// =============================================================================

echo "--- zoid6config.php Tests ---\n\n";

// Test: zoid6config.php exists and is readable
echo "Test 1: zoid6config.php exists\n";
$zoid6config = "/home/opencode/data/work/zoid6/php/zoid6config.php";
if (!file_exists($zoid6config)) {
    test_fail("zoid6config.php not found", $zoid6config);
}
test_pass("zoid6config.php found");

// Test: zoid6config.php ensures bbsengine6/smarty/ in SMARTYPLUGINSDIR
echo "Test 2: zoid6config.php adds bbsengine6/smarty/ to SMARTYPLUGINSDIR\n";
$src = file_get_contents($zoid6config);
if (strpos($src, 'bbsengine6/smarty/') === false) {
    test_fail("zoid6config.php does not reference bbsengine6/smarty/");
}
test_pass("zoid6config.php references bbsengine6/smarty/");

// Test: zoid6config.php does it via in_array check (not hardcoded append)
echo "Test 3: zoid6config.php uses in_array dedup check\n";
if (strpos($src, 'in_array') === false) {
    test_fail("zoid6config.php does not use in_array for dedup");
}
test_pass("in_array dedup check present");

echo "\n";

// =============================================================================
// ENGINE.PHP CENTRAL ENFORCEMENT
// =============================================================================

echo "--- engine.php Tests ---\n\n";

// Test: bbsengine6config.php exposes bbsengine6/smarty/ as the
// engine plugin-dir fallback (formerly inlined in engine.php's
// getsmarty(); moved into \bbsengine6\template\plugin\extra()
// as part of the registry refactor).
echo "Test 4: bbsengine6config.php exposes bbsengine6/smarty/ as engine plugin fallback\n";
$config_src = file_get_contents("/home/opencode/data/work/bbsengine6/php/bbsengine6config.php");
if (strpos($config_src, 'bbsengine6/smarty/') === false) {
    test_fail("bbsengine6config.php does not reference bbsengine6/smarty/");
}
test_pass("bbsengine6config.php references bbsengine6/smarty/ as plugin fallback");

// Test: engine.php delegates plugin-dir resolution to the registry
echo "Test 5: engine.php delegates plugin-dir resolution to registry\n";
$engine_src = file_get_contents("/home/opencode/data/work/bbsengine6/php/engine.php");
if (strpos($engine_src, 'bbsengine6\\template\\plugin\\normalize') === false) {
    test_fail("engine.php does not delegate to \\bbsengine6\\template\\plugin\\normalize");
}
test_pass("engine.php delegates to \\bbsengine6\\template\\plugin\\normalize");

echo "\n";

// =============================================================================
// TEOS CONFIG TEST
// =============================================================================

echo "--- teos config-prod.php Tests ---\n\n";

// Test: teos config-prod.php exists
echo "Test 6: teos config-prod.php exists\n";
$teos_config = "/home/opencode/data/work/teos/www/config-prod.php";
if (!file_exists($teos_config)) {
    test_fail("teos config-prod.php not found", $teos_config);
}
test_pass("teos config-prod.php found");

// Test: teos config-prod.php defines config\SMARTYPLUGINSDIR
echo "Test 7: teos config-prod.php defines config\\SMARTYPLUGINSDIR\n";
$teos_src = file_get_contents($teos_config);
if (strpos($teos_src, 'config\\SMARTYPLUGINSDIR') === false) {
    test_fail("teos config-prod.php does not define config\\SMARTYPLUGINSDIR");
}
test_pass("config\\SMARTYPLUGINSDIR defined in teos config");

// Test: teos config-prod.php includes zoid6config.php
echo "Test 8: teos config-prod.php includes zoid6config.php\n";
if (strpos($teos_src, 'zoid6config.php') === false) {
    test_fail("teos config-prod.php does not include zoid6config.php");
}
test_pass("zoid6config.php included in teos config");

echo "\n";

echo "=== Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\n✓ All SMARTYPLUGINSDIR tests passed!\n";
exit(0);
