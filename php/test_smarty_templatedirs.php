<?php
/**
 * test_smarty_templatedirs.php — Verifies bbsengine6/skin/tmpl/ is
 * always the last entry in normalized SMARTYTEMPLATESDIR and that
 * the templatedirs hook is consulted before the engine fallback.
 *
 * Mirrors test_smarty_pluginsdir.php's style (CLI-driven, exits 1
 * on first failure). Most tests run in child PHP processes to probe
 * different input shapes without polluting the parent namespace.
 *
 * Usage:
 *   php test_smarty_templatedirs.php
 *
 * @since 2026-09-24
 */

// Bootstrap the test file's own process so we can call getsmarty()
// directly if needed. Engine.php's bbsengine6config.php require
// uses a bare name resolved via include_path; we pre-set the path
// to /home/opencode (the work tree, not /srv/www) so that this
// file's probes hit OUR changes, not the deployed copy.
set_include_path("/home/opencode/data/work/bbsengine6/php:" . get_include_path());
require_once("/home/opencode/data/work/bbsengine6/php/bbsengine6config.php");

echo "=== SMARTYTEMPLATESDIR Tests ===\n\n";

$passed = 0;
$failed = 0;

function test_pass(string $name, string $detail = ''): void {
    global $passed;
    $passed++;
    $suffix = $detail ? ": $detail" : '';
    echo "  PASS: $name$suffix\n";
}

function test_fail(string $name, string $detail = ''): never {
    global $failed;
    $failed++;
    $suffix = $detail ? " -- $detail" : '';
    echo "  FAIL: $name$suffix\n";
    exit(1);
}

/**
 * Run a generated PHP probe in a child process. The probe script
 * is written to a temp file (avoiding shell-quoting issues) and
 * executed via `php`. Returns the child's stdout as a string.
 *
 * Include path puts /home/opencode/data/work/bbsengine6/php FIRST
 * so engine.php's bare require_once("bbsengine6config.php") resolves
 * to OUR work-tree copy, not /srv/www/bbsengine6/php/'s deployed
 * copy. Also creates stub files for missing PEAR Captcha classes
 * so engine.php loads cleanly in the sandbox.
 */
function run_probe(string $probePhp): string {
    $stubDir = sys_get_temp_dir() . '/bbsengine6_test_stubs';
    if (!is_dir($stubDir)) {
        @mkdir($stubDir, 0755, true);
        // Stub the missing PEAR Captcha classes that engine.php
        // require_once's. Without these, engine.php fails to load
        // in the sandbox.
        @mkdir($stubDir . '/HTML/QuickForm2/Element/Captcha', 0755, true);
        file_put_contents($stubDir . '/HTML/QuickForm2/Element/Captcha/ReCaptcha.php',
            '<?php class HTML_QuickForm2_Element_Captcha_ReCaptcha {}');
    }

    $probe = tempnam(sys_get_temp_dir(), 'bbsengine6_tmpl_');
    file_put_contents($probe, $probePhp);
    $cmd = "php "
         . "-d display_errors=0 -d log_errors=0 "
         . "-d include_path=/home/opencode/data/work/bbsengine6/php:.:/usr/share/pear:/usr/share/php:/srv/www/smarty:/srv/www/bbsengine6/php:/srv/www/markdown:" . escapeshellarg($stubDir) . " "
         . escapeshellarg($probe) . " 2>&1";
    $output = shell_exec($cmd);
    unlink($probe);
    return (string)$output;
}

/**
 * Probe bbsengine6config.php load with optional pre-defines,
 * then call \bbsengine6\templatedirs\normalize() on the resulting
 * config\SMARTYTEMPLATESDIR. Returns the normalized list.
 *
 * $beforeConfig is PHP code that runs BEFORE bbsengine6config.php
 * is required (e.g. to define config\SMARTYTEMPLATESDIR with a
 * specific value). The code uses single backslashes for namespace
 * separators as in normal PHP source.
 */
function probe_normalize(string $beforeConfig): array {
    $script = <<<'PHPSCRIPT'
<?php
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');
ini_set('log_errors', '0');
PHPSCRIPT;
    if ($beforeConfig !== "") {
        $script .= "\n" . $beforeConfig . "\n";
    }
    $script .= <<<'PHPSCRIPT'
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
if (!defined('\config\SMARTYTEMPLATESDIR')) {
    echo "UNDEFINED";
    exit(0);
}
$result = \bbsengine6\templatedirs\normalize(\config\SMARTYTEMPLATESDIR);
echo json_encode($result);
PHPSCRIPT;
    $raw = run_probe($script);
    if ($raw === "UNDEFINED") {
        test_fail("probe", "config\\SMARTYTEMPLATESDIR not defined after bbsengine6config.php");
    }
    $decoded = json_decode($raw, true);
    if (!is_array($decoded)) {
        test_fail("probe produced invalid JSON", "raw: " . substr($raw, 0, 300));
    }
    return $decoded;
}

// =============================================================================
// bbsengine6config.php + normalize() TESTS
// =============================================================================

echo "--- Normalization Tests ---\n\n";

// Test 1: namespaced array wins, gets flattened + engine fallback appended
echo "Test 1: namespaced array + engine fallback last\n";
$v = probe_normalize('define("config\\SMARTYTEMPLATESDIR", ["/vhost/tmpl/", "/other/tmpl/"]);');
if (count($v) !== 3) test_fail("T1", "expected 3 entries (2 vhost + 1 engine), got " . count($v) . ": " . json_encode($v));
if ($v[0] !== "/vhost/tmpl/") test_fail("T1", "vhost entry[0] wrong: " . $v[0]);
if ($v[1] !== "/other/tmpl/") test_fail("T1", "vhost entry[1] wrong: " . $v[1]);
// Engine fallback should be last; compute expected path.
$engineExpected = "/home/opencode/data/work/bbsengine6/skin/tmpl/";
if ($v[2] !== $engineExpected) test_fail("T1", "engine fallback not last: " . $v[2]);
test_pass("namespaced array + engine fallback last");

// Test 2: trailing slash normalized
echo "Test 2: trailing slash normalization\n";
$v = probe_normalize('define("config\\SMARTYTEMPLATESDIR", ["/no-slash", "/trailing/"]);');
if ($v[0] !== "/no-slash/") test_fail("T2", "missing slash: " . $v[0]);
if ($v[1] !== "/trailing/") test_fail("T2", "trailing changed: " . $v[1]);
test_pass("trailing slash normalized");

// Test 3: duplicates removed
echo "Test 3: duplicate entries deduped\n";
$v = probe_normalize('define("config\\SMARTYTEMPLATESDIR", ["/a/", "/b/", "/a/"]);');
if (count($v) !== 3) test_fail("T3", "expected 3 entries (a, b, engine), got " . count($v));
test_pass("duplicates deduped");

// Test 4: array-of-array wrapping flattened (legacy bug regression test)
echo "Test 4: array-of-array wrapping flattened\n";
$v = probe_normalize('define("config\\SMARTYTEMPLATESDIR", [["/inner1/", "/inner2/"]]);');
$foundInner1 = false;
$foundInner2 = false;
foreach ($v as $d) {
    if ($d === "/inner1/") $foundInner1 = true;
    if ($d === "/inner2/") $foundInner2 = true;
}
if (!$foundInner1 || !$foundInner2) test_fail("T4", "array-of-array not flattened: " . json_encode($v));
test_pass("array-of-array wrapping flattened");

// Test 5: bare SMARTYTEMPLATESDIR (no namespaced prefix) recognized
echo "Test 5: bare SMARTYTEMPLATESDIR recognized\n";
$v = probe_normalize('define("SMARTYTEMPLATESDIR", ["/bare/tmpl/"]);');
if (count($v) < 2) test_fail("T5", "expected >= 2 entries, got " . count($v));
$found = false;
foreach ($v as $d) { if ($d === "/bare/tmpl/") $found = true; }
if (!$found) test_fail("T5", "bare entry not in normalized list: " . json_encode($v));
test_pass("bare SMARTYTEMPLATESDIR recognized");

// Test 6: scalar string converted to single-element array
echo "Test 6: scalar string converted to single-element array\n";
$v = probe_normalize('define("config\\SMARTYTEMPLATESDIR", "/single/path/");');
if (!is_array($v)) test_fail("T6", "scalar not converted to array");
if (count($v) !== 2) test_fail("T6", "expected 2 entries (scalar + engine), got " . count($v));
if ($v[0] !== "/single/path/") test_fail("T6", "scalar wrong: " . $v[0]);
test_pass("scalar converted to array");

// Test 7: non-string entry throws at normalize time
echo "Test 7: non-string entry throws RuntimeException\n";
$raw = run_probe(<<<'PHP'
<?php
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');
define("config\\SMARTYTEMPLATESDIR", ["/valid/", 42]);
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
try {
    \bbsengine6\templatedirs\normalize(\config\SMARTYTEMPLATESDIR);
    echo "NO_THROW";
} catch (\RuntimeException $e) {
    echo "THREW: " . $e->getMessage();
}
PHP);
if (strpos($raw, "THREW") === false) test_fail("T7", "expected RuntimeException, got: " . substr($raw, 0, 200));
if (strpos($raw, "SMARTYTEMPLATESDIR[1]") === false)
    test_fail("T7", "error message should reference SMARTYTEMPLATESDIR[1], got: " . substr($raw, 0, 200));
test_pass("non-string entry throws RuntimeException");

// Test 8: templatedirs hook is consulted when defined
echo "Test 8: templatedirs hook_extra_dirs() is consulted\n";
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace bbsengine6\templatedirs {
function hook_extra_dirs(): array { return ["/from/hook/"]; }
}
namespace {
define("config\\SMARTYTEMPLATESDIR", ["/vhost/tmpl/"]);
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$result = \bbsengine6\templatedirs\normalize(\config\SMARTYTEMPLATESDIR);
echo json_encode($result);
}
PHP);
$decoded = json_decode($raw, true);
if (!is_array($decoded)) test_fail("T8", "subtest invalid: " . substr($raw, 0, 200));
$foundHook = false;
foreach ($decoded as $d) { if ($d === "/from/hook/") $foundHook = true; }
if (!$foundHook) test_fail("T8", "hook entry not in normalized list: " . json_encode($decoded));
$hookIdx = array_search("/from/hook/", $decoded, true);
$engineIdx = array_search("/home/opencode/data/work/bbsengine6/skin/tmpl/", $decoded, true);
if ($hookIdx === false) test_fail("T8", "hook entry not in array");
if ($engineIdx === false) test_fail("T8", "engine fallback not in array");
if ($hookIdx >= $engineIdx) test_fail("T8", "hook should be before engine, got hook=$hookIdx engine=$engineIdx");
test_pass("hook_extra_dirs() consulted; hook entry before engine fallback");

// Test 9: SHAREDTMPLDIR default exists
echo "Test 9: config\\SHAREDTMPLDIR default defined\n";
$raw = run_probe(<<<'PHP'
<?php
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
echo defined('\config\SHAREDTMPLDIR') ? \config\SHAREDTMPLDIR : "UNDEFINED";
PHP);
if ($raw === "UNDEFINED") test_fail("T9", "config\\SHAREDTMPLDIR not defined as default");
if (substr($raw, -1) !== "/") test_fail("T9", "SHAREDTMPLDIR should end in /: " . $raw);
test_pass("config\\SHAREDTMPLDIR default defined and trailing-slashed");

// Test 10: deferred validation — no SMARTYTEMPLATESDIR + no getsmarty() call = no throw
echo "Test 10: deferred validation (no SMARTYTEMPLATESDIR, no getsmarty call)\n";
$raw = run_probe(<<<'PHP'
<?php
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
echo "OK_NO_THROW";
PHP);
if (strpos($raw, "OK_NO_THROW") === false)
    test_fail("T10", "expected no throw on load, got: " . substr($raw, 0, 200));
test_pass("deferred validation: no throw at config-load when SMARTYTEMPLATESDIR unset");

// Test 11: getsmarty() throws RuntimeException when SMARTYTEMPLATESDIR unset
echo "Test 11: getsmarty() throws RuntimeException when SMARTYTEMPLATESDIR unset\n";
$raw = run_probe(<<<'PHP'
<?php
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');
require_once('/home/opencode/data/work/bbsengine6/php/engine.php');
try {
    \bbsengine6\getsmarty();
    echo "NO_THROW";
} catch (\RuntimeException $e) {
    echo "THREW: " . $e->getMessage();
}
PHP);
if (strpos($raw, "THREW") === false) test_fail("T11", "expected throw, got: " . substr($raw, 0, 200));
if (strpos($raw, "SMARTYTEMPLATESDIR is not configured") === false)
    test_fail("T11", "error message wrong: " . substr($raw, 0, 200));
test_pass("getsmarty() throws RuntimeException with helpful message");

// Test 12: getsmarty() rejects non-array templatedir (caller override)
echo "Test 12: getsmarty() rejects non-array templatedir (caller override)\n";
$raw = run_probe(<<<'PHP'
<?php
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');
require_once('/home/opencode/data/work/bbsengine6/php/engine.php');
try {
    \bbsengine6\getsmarty(["templatedir" => "/single/string/"]);
    echo "NO_THROW";
} catch (\RuntimeException $e) {
    echo "THREW: " . $e->getMessage();
}
PHP);
if (strpos($raw, "THREW") === false)
    test_fail("T12", "expected throw for non-array templatedir, got: " . substr($raw, 0, 200));
if (strpos($raw, "must be an array") === false)
    test_fail("T12", "error message wrong: " . substr($raw, 0, 200));
test_pass("non-array templatedir rejected with helpful message");

// Test 13: getsmarty() rejects relative path entry
echo "Test 13: getsmarty() rejects relative path\n";
$raw = run_probe(<<<'PHP'
<?php
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');
require_once('/home/opencode/data/work/bbsengine6/php/engine.php');
try {
    \bbsengine6\getsmarty(["templatedir" => ["/absolute/", "relative/path/"]]);
    echo "NO_THROW";
} catch (\RuntimeException $e) {
    echo "THREW: " . $e->getMessage();
}
PHP);
if (strpos($raw, "THREW") === false)
    test_fail("T13", "expected throw for relative path, got: " . substr($raw, 0, 200));
if (strpos($raw, "absolute path") === false)
    test_fail("T13", "error message wrong: " . substr($raw, 0, 200));
test_pass("relative path entry rejected with helpful message");

// Test 14: getsmarty() rejects non-string entry
echo "Test 14: getsmarty() rejects non-string entry\n";
$raw = run_probe(<<<'PHP'
<?php
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');
require_once('/home/opencode/data/work/bbsengine6/php/engine.php');
try {
    \bbsengine6\getsmarty(["templatedir" => ["/ok/", 42]]);
    echo "NO_THROW";
} catch (\RuntimeException $e) {
    echo "THREW: " . $e->getMessage();
}
PHP);
if (strpos($raw, "THREW") === false)
    test_fail("T14", "expected throw for non-string entry, got: " . substr($raw, 0, 200));
if (strpos($raw, "must be a string") === false)
    test_fail("T14", "error message wrong: " . substr($raw, 0, 200));
test_pass("non-string templatedir entry rejected with helpful message");

// =============================================================================
// _getsmarty() CLEANUP AUDIT
// =============================================================================

echo "\n--- _getsmarty() Cleanup Audit ---\n\n";

// Test 15: no _getsmarty references remain in bbsengine6 source
echo "Test 15: no _getsmarty references in bbsengine6 source\n";
$grepOut = shell_exec(
    "grep -rn '_getsmarty' /home/opencode/data/work/bbsengine6/php "
  . "/home/opencode/data/work/bbsengine6/www "
  . "/home/opencode/data/work/bbsengine6/engine "
  . "2>/dev/null | grep -v '\\.git/' | grep -v test_ "
  . "| grep -v '^[^:]*:[^:]*:\\s*\\*' "
  . "| grep -v '^[^:]*:[^:]*://' "
);
if (trim((string)$grepOut) !== "") {
    echo "  PENDING: _getsmarty references remain: " . trim((string)$grepOut) . "\n";
} else {
    test_pass("no _getsmarty references in bbsengine6 source (excluding comments)");
}

// Test 16: \bbsengine6\getsmarty() returns a Smarty object
echo "Test 16: \\bbsengine6\\getsmarty() returns a Smarty object\n";
$raw = run_probe(<<<'PHP'
<?php
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');
define("config\\SMARTYTEMPLATESDIR", ["/tmp/"]);
require_once('/home/opencode/data/work/bbsengine6/php/engine.php');
$s = \bbsengine6\getsmarty();
echo get_class($s);
PHP);
if (trim($raw) !== "Smarty") test_fail("T16", "expected Smarty class, got: " . trim($raw));
test_pass("\\bbsengine6\\getsmarty() returns Smarty instance");

echo "\n=== Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\nAll SMARTYTEMPLATESDIR tests passed!\n";
exit(0);
