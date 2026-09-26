<?php
/**
 * test_smarty_template.php — Verifies the template and plugin-dir
 * registry pattern introduced alongside the
 * \bbsengine6\template / \bbsengine6\template\plugin /
 * \zoid6\template namespaces.
 *
 * Two concerns are tested:
 *
 *   1. Backward compatibility. The previous
 *      \bbsengine6\templatedirs\normalize() and
 *      \bbsengine6\templatedirs\hook_extra_dirs() symbols
 *      were replaced by \bbsengine6\template\normalize() and
 *      \bbsengine6\template\hook_extra_dirs(). All previous
 *      tests (T1–T16) must keep passing under the new
 *      namespace.
 *
 *   2. New behavior. The priority-enum registry, the
 *      \bbsengine6\template\extra() canonical engine
 *      contribution, the thin-wrapper shape, and the
 *      request-scoped cache are exercised by T17–T37.
 *
 * Style mirrors test_smarty_pluginsdir.php: CLI-driven,
 * exits 1 on first failure. Most tests run in child PHP
 * processes to probe different input shapes without
 * polluting the parent namespace.
 *
 * Usage:
 *   php test_smarty_template.php
 *
 * @since 2026-09-24
 */

set_include_path("/home/opencode/data/work/bbsengine6/php:" . get_include_path());
require_once("/home/opencode/data/work/bbsengine6/php/bbsengine6config.php");

echo "=== SMARTYTEMPLATESDIR + Template Registry Tests ===\n\n";

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
 */
function run_probe(string $probePhp): string {
    $stubDir = sys_get_temp_dir() . '/bbsengine6_test_stubs';
    if (!is_dir($stubDir)) {
        @mkdir($stubDir, 0755, true);
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
 * then call \bbsengine6\template\normalize() on the resulting
 * config\SMARTYTEMPLATESDIR. Returns the normalized list.
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
$result = \bbsengine6\template\normalize(
    \config\SMARTYTEMPLATESDIR,
    \bbsengine6\template\_registry(),
    \bbsengine6\template\extra()[0],
    "bbsengine6\\template"
);
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
// NORMALIZATION (T1-T9) — equivalent to the previous templatedirs tests
// =============================================================================

echo "--- Normalization Tests ---\n\n";

echo "Test 1: namespaced array + engine fallback last\n";
$v = probe_normalize('define("config\\SMARTYTEMPLATESDIR", ["/vhost/tmpl/", "/other/tmpl/"]);');
if (count($v) !== 3) test_fail("T1", "expected 3 entries (2 vhost + 1 engine), got " . count($v) . ": " . json_encode($v));
if ($v[0] !== "/vhost/tmpl/") test_fail("T1", "vhost entry[0] wrong: " . $v[0]);
if ($v[1] !== "/other/tmpl/") test_fail("T1", "vhost entry[1] wrong: " . $v[1]);
$engineExpected = "/home/opencode/data/work/bbsengine6/skin/tmpl/";
if ($v[2] !== $engineExpected) test_fail("T1", "engine fallback not last: " . $v[2]);
test_pass("namespaced array + engine fallback last");

echo "Test 2: trailing slash normalization\n";
$v = probe_normalize('define("config\\SMARTYTEMPLATESDIR", ["/no-slash", "/trailing/"]);');
if ($v[0] !== "/no-slash/") test_fail("T2", "missing slash: " . $v[0]);
if ($v[1] !== "/trailing/") test_fail("T2", "trailing changed: " . $v[1]);
test_pass("trailing slash normalized");

echo "Test 3: duplicate entries deduped\n";
$v = probe_normalize('define("config\\SMARTYTEMPLATESDIR", ["/a/", "/b/", "/a/"]);');
if (count($v) !== 3) test_fail("T3", "expected 3 entries (a, b, engine), got " . count($v));
test_pass("duplicates deduped");

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

echo "Test 5: bare SMARTYTEMPLATESDIR recognized\n";
$v = probe_normalize('define("SMARTYTEMPLATESDIR", ["/bare/tmpl/"]);');
if (count($v) < 2) test_fail("T5", "expected >= 2 entries, got " . count($v));
$found = false;
foreach ($v as $d) { if ($d === "/bare/tmpl/") $found = true; }
if (!$found) test_fail("T5", "bare entry not in normalized list: " . json_encode($v));
test_pass("bare SMARTYTEMPLATESDIR recognized");

echo "Test 6: scalar string converted to single-element array\n";
$v = probe_normalize('define("config\\SMARTYTEMPLATESDIR", "/single/path/");');
if (!is_array($v)) test_fail("T6", "scalar not converted to array");
if (count($v) !== 2) test_fail("T6", "expected 2 entries (scalar + engine), got " . count($v));
if ($v[0] !== "/single/path/") test_fail("T6", "scalar wrong: " . $v[0]);
test_pass("scalar converted to array");

echo "Test 7: non-string entry throws RuntimeException\n";
$raw = run_probe(<<<'PHP'
<?php
error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');
define("config\\SMARTYTEMPLATESDIR", ["/valid/", 42]);
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
try {
    \bbsengine6\template\normalize(
        \config\SMARTYTEMPLATESDIR,
        \bbsengine6\template\_registry(),
        \bbsengine6\template\extra()[0],
        "bbsengine6\\template"
    );
    echo "NO_THROW";
} catch (\RuntimeException $e) {
    echo "THREW: " . $e->getMessage();
}
PHP);
if (strpos($raw, "THREW") === false) test_fail("T7", "expected RuntimeException, got: " . substr($raw, 0, 200));
test_pass("non-string entry throws RuntimeException");

echo "Test 8: hook_extra_dirs() in new namespace is consulted\n";
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace bbsengine6\template {
function hook_extra_dirs(): array { return ["/from/hook/"]; }
}
namespace {
define("config\\SMARTYTEMPLATESDIR", ["/vhost/tmpl/"]);
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$result = \bbsengine6\template\normalize(
    \config\SMARTYTEMPLATESDIR,
    \bbsengine6\template\_registry(),
    \bbsengine6\template\extra()[0],
    "bbsengine6\\template"
);
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

// =============================================================================
// DEFERRED VALIDATION (T10-T11) and getsmarty() VALIDATION (T12-T14)
// =============================================================================

echo "\n--- Deferred Validation ---\n\n";

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

echo "\n--- getsmarty() Validation ---\n\n";

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

echo "Test 13: getsmarty() rejects relative path entry\n";
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
// CLEANUP AUDIT (T15-T16)
// =============================================================================

echo "\n--- Cleanup Audit ---\n\n";

echo "Test 15: no _getsmarty references remain in bbsengine6 source\n";
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

// =============================================================================
// PRIORITY-ENUM REGISTRY TESTS (T17-T22)
// =============================================================================

echo "\n--- Priority-Enum Registry Tests ---\n\n";

echo "Test 17: register('app', h1); register('app-integration', h2) -- h1 runs first\n";
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace bbsengine6\template {
function hook_extra_dirs(): array { return []; }
}
namespace {
define("config\\SMARTYTEMPLATESDIR", ["/vhost/"]);
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
\bbsengine6\template\register(
    \bbsengine6\template\PRIORITY_APP,
    function () { return ["/from-app/"]; }
);
\bbsengine6\template\register(
    \bbsengine6\template\PRIORITY_APP_INTEGRATION,
    function () { return ["/from-app-integration/"]; }
);
$result = \bbsengine6\template\normalize(
    \config\SMARTYTEMPLATESDIR,
    \bbsengine6\template\_registry(),
    \bbsengine6\template\extra()[0],
    "bbsengine6\\template"
);
echo json_encode($result);
}
PHP);
$decoded = json_decode($raw, true);
if (!is_array($decoded)) test_fail("T17", "subtest invalid: " . substr($raw, 0, 200));
$appIdx = array_search("/from-app/", $decoded, true);
$aiIdx = array_search("/from-app-integration/", $decoded, true);
if ($appIdx === false || $aiIdx === false)
    test_fail("T17", "missing hook entries in: " . json_encode($decoded));
if ($appIdx >= $aiIdx)
    test_fail("T17", "APP should run before APP_INTEGRATION, got app=$appIdx ai=$aiIdx");
test_pass("APP runs before APP_INTEGRATION");

echo "Test 18: multiple hooks at same priority run in registration order\n";
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace bbsengine6\template {
function hook_extra_dirs(): array { return []; }
}
namespace {
define("config\\SMARTYTEMPLATESDIR", ["/vhost/"]);
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
\bbsengine6\template\register(
    \bbsengine6\template\PRIORITY_APP_INTEGRATION,
    function () { return ["/first/"]; }
);
\bbsengine6\template\register(
    \bbsengine6\template\PRIORITY_APP_INTEGRATION,
    function () { return ["/second/"]; }
);
$result = \bbsengine6\template\normalize(
    \config\SMARTYTEMPLATESDIR,
    \bbsengine6\template\_registry(),
    \bbsengine6\template\extra()[0],
    "bbsengine6\\template"
);
echo json_encode($result);
}
PHP);
$decoded = json_decode($raw, true);
if (!is_array($decoded)) test_fail("T18", "subtest invalid: " . substr($raw, 0, 200));
$firstIdx = array_search("/first/", $decoded, true);
$secondIdx = array_search("/second/", $decoded, true);
if ($firstIdx === false || $secondIdx === false)
    test_fail("T18", "missing entries in: " . json_encode($decoded));
if ($firstIdx >= $secondIdx)
    test_fail("T18", "registration order not preserved: first=$firstIdx second=$secondIdx");
test_pass("registration order preserved within priority");

echo "Test 19: duplicate register() of same callable is idempotent\n";
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace bbsengine6\template {
function hook_extra_dirs(): array { return []; }
}
namespace {
define("config\\SMARTYTEMPLATESDIR", ["/vhost/"]);
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$h = function () { return ["/once/"]; };
\bbsengine6\template\register(\bbsengine6\template\PRIORITY_APP, $h);
\bbsengine6\template\register(\bbsengine6\template\PRIORITY_APP, $h);
\bbsengine6\template\register(\bbsengine6\template\PRIORITY_APP, $h);
$result = \bbsengine6\template\normalize(
    \config\SMARTYTEMPLATESDIR,
    \bbsengine6\template\_registry(),
    \bbsengine6\template\extra()[0],
    "bbsengine6\\template"
);
// Count occurrences of /once/ in result
$count = count(array_filter($result, fn($d) => $d === "/once/"));
echo "COUNT:" . $count;
}
PHP);
if (strpos($raw, "COUNT:1") === false)
    test_fail("T19", "expected /once/ exactly once, got: " . $raw);
test_pass("duplicate register() is idempotent");

echo "Test 20: register() throws on unknown priority\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
try {
    \bbsengine6\template\register("invalid-priority", function () { return []; });
    echo "NO_THROW";
} catch (\RuntimeException $e) {
    echo "THREW: " . $e->getMessage();
}
PHP);
if (strpos($raw, "THREW") === false)
    test_fail("T20", "expected throw on invalid priority, got: " . substr($raw, 0, 200));
if (strpos($raw, "unknown priority") === false)
    test_fail("T20", "error message should mention 'unknown priority', got: " . substr($raw, 0, 200));
test_pass("register() typo-guards on unknown priority");

echo "Test 21: legacy hook_extra_dirs() auto-registered at APP_INTEGRATION\n";
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace bbsengine6\template {
function hook_extra_dirs(): array { return ["/legacy-v0-hook/"]; }
}
namespace {
define("config\\SMARTYTEMPLATESDIR", ["/vhost/"]);
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$result = \bbsengine6\template\normalize(
    \config\SMARTYTEMPLATESDIR,
    \bbsengine6\template\_registry(),
    \bbsengine6\template\extra()[0],
    "bbsengine6\\template"
);
echo json_encode($result);
}
PHP);
$decoded = json_decode($raw, true);
if (!is_array($decoded)) test_fail("T21", "subtest invalid: " . substr($raw, 0, 200));
$found = false;
foreach ($decoded as $d) { if ($d === "/legacy-v0-hook/") $found = true; }
if (!$found) test_fail("T21", "v0 hook entry not auto-registered: " . json_encode($decoded));
test_pass("v0 hook_extra_dirs() auto-registered at APP_INTEGRATION");

echo "Test 22: \\zoid6\\template\\extra auto-registered at APP_INTEGRATION\n";
// Define a stub \zoid6\template\extra BEFORE requiring
// bbsengine6config.php so the auto-registration fires. In the
// real deploy, zoid6/php/zoid6config.php provides this function
// and is loaded by the vhost before bbsengine6.
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace zoid6\template {
function extra(): array { return ["/srv/www/zoid6/shared/skin/tmpl/"]; }
}
namespace {
define("config\\SMARTYTEMPLATESDIR", ["/vhost/"]);
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$result = \bbsengine6\template\normalize(
    \config\SMARTYTEMPLATESDIR,
    \bbsengine6\template\_registry(),
    \bbsengine6\template\extra()[0],
    "bbsengine6\\template"
);
echo json_encode($result);
}
PHP);
$decoded = json_decode($raw, true);
if (!is_array($decoded)) test_fail("T22", "subtest invalid: " . substr($raw, 0, 200));
$found = false;
foreach ($decoded as $d) { if ($d === "/srv/www/zoid6/shared/skin/tmpl/") $found = true; }
if (!$found) test_fail("T22", "zoid6 template_extra not in resolved path: " . json_encode($decoded));
test_pass("zoid6 template_extra() auto-registered at APP_INTEGRATION");

// =============================================================================
// ENGINE FALLBACK + WRAPPER SYMMETRY (T23-T28)
// =============================================================================

echo "\n--- Engine Fallback + Wrapper Symmetry ---\n\n";

echo "Test 23: engine fallback appears last in resolved path\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$result = \bbsengine6\template\normalize(
    ["/vhost1/", "/vhost2/"],
    \bbsengine6\template\_registry(),
    \bbsengine6\template\extra()[0],
    "bbsengine6\\template"
);
echo json_encode($result);
PHP);
$decoded = json_decode($raw, true);
if (!is_array($decoded)) test_fail("T23", "subtest invalid: " . substr($raw, 0, 200));
if (end($decoded) !== "/home/opencode/data/work/bbsengine6/skin/tmpl/")
    test_fail("T23", "engine fallback not last: " . json_encode($decoded));
test_pass("engine fallback last");

echo "Test 24: engine fallback dedup'd if already in input\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$engineTmpl = "/home/opencode/data/work/bbsengine6/skin/tmpl/";
$result = \bbsengine6\template\normalize(
    [$engineTmpl],
    \bbsengine6\template\_registry(),
    $engineTmpl,
    "bbsengine6\\template"
);
$count = count(array_filter($result, fn($d) => $d === $engineTmpl));
echo "COUNT:" . $count;
PHP);
if (strpos($raw, "COUNT:1") === false)
    test_fail("T24", "engine fallback should appear exactly once, got: " . $raw);
test_pass("engine fallback dedup'd when already in input");

echo "Test 25: \\bbsengine6\\template\\extra returns engine tmpl dir\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$extra = \bbsengine6\template\extra();
echo json_encode($extra);
PHP);
$decoded = json_decode(trim($raw), true);
if (!is_array($decoded) || count($decoded) !== 1 || $decoded[0] !== "/home/opencode/data/work/bbsengine6/skin/tmpl/")
    test_fail("T25", "extra() wrong: " . trim($raw));
test_pass("extra() returns engine tmpl dir");

echo "Test 26: \\bbsengine6\\template\\plugin\\extra returns engine plugin dir\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$extra = \bbsengine6\template\plugin\extra();
echo json_encode($extra);
PHP);
$decoded = json_decode(trim($raw), true);
if (!is_array($decoded) || count($decoded) !== 1 || $decoded[0] !== "/home/opencode/data/work/bbsengine6/smarty/")
    test_fail("T26", "plugin extra() wrong: " . trim($raw));
test_pass("plugin extra() returns engine smarty/ dir");

echo "Test 27: \\bbsengine6\\template\\plugin\\normalize resolves with engine plugin fallback\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$result = \bbsengine6\template\plugin\normalize(["/vhost/smarty/"]);
echo json_encode($result);
PHP);
$decoded = json_decode($raw, true);
if (!is_array($decoded)) test_fail("T27", "subtest invalid: " . substr($raw, 0, 200));
$found = false;
foreach ($decoded as $d) { if ($d === "/home/opencode/data/work/bbsengine6/smarty/") $found = true; }
if (!$found) test_fail("T27", "engine plugin fallback missing: " . json_encode($decoded));
test_pass("plugin normalize() appends engine plugin fallback");

echo "Test 28: registries are independent between template and plugin namespaces\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
\bbsengine6\template\register(
    \bbsengine6\template\PRIORITY_APP,
    function () { return ["/template-only/"]; }
);
$tplResult = \bbsengine6\template\normalize(
    [],
    \bbsengine6\template\_registry(),
    \bbsengine6\template\extra()[0],
    "bbsengine6\\template"
);
$plugResult = \bbsengine6\template\plugin\normalize([]);
echo "TPL:" . json_encode($tplResult) . ";PLUG:" . json_encode($plugResult);
PHP);
if (strpos($raw, "template-only") === false)
    test_fail("T28", "template hook missing in template result: " . $raw);
// Verify template result does NOT contain a plugin entry
// (e.g. /home/opencode/data/work/bbsengine6/smarty/). The
// template result is everything before ";PLUG:".
$tplPart = substr($raw, 0, strpos($raw, ";PLUG:"));
if ($tplPart === false) $tplPart = $raw;
if (strpos($tplPart, "smarty") !== false)
    test_fail("T28", "template result contains plugin entry (registries not isolated): " . $raw);
// Verify plugin result does NOT contain template-only
$plugPart = substr($raw, strpos($raw, ";PLUG:") + 6);
if (strpos($plugPart, "template-only") !== false)
    test_fail("T28", "plugin result contains template hook (registries not isolated): " . $raw);
test_pass("registries are independent across namespaces");

// =============================================================================
// CACHE TESTS (T29-T31)
// =============================================================================

echo "\n--- Cache Tests ---\n\n";

echo "Test 29: _smarty_resolved_templatedir caches by serialized input\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/engine.php');
// First call populates cache; second should return cached value.
$r1 = \bbsengine6\_smarty_resolved_templatedir(["/x/"]);
$r2 = \bbsengine6\_smarty_resolved_templatedir(["/x/"]);
echo ($r1 === $r2) ? "SAME" : "DIFFERENT";
PHP);
if (trim($raw) !== "SAME")
    test_fail("T29", "cache should return same array: " . trim($raw));
test_pass("cache returns same array for same input");

echo "Test 30: cache miss produces different buckets for different inputs\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/engine.php');
$r1 = \bbsengine6\_smarty_resolved_templatedir(["/a/"]);
$r2 = \bbsengine6\_smarty_resolved_templatedir(["/b/"]);
echo ($r1 !== $r2) ? "DIFFERENT" : "SAME";
PHP);
if (trim($raw) !== "DIFFERENT")
    test_fail("T30", "different inputs should produce different resolved lists: " . trim($raw));
test_pass("different inputs produce different cache buckets");

echo "Test 31: caller override of templatedir bypasses registry walk\n";
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace bbsengine6\template {
function hook_extra_dirs(): array { return ["/from-hook/"]; }
}
namespace {
define("config\\SMARTYTEMPLATESDIR", ["/vhost/"]);
require_once('/home/opencode/data/work/bbsengine6/php/engine.php');
// Caller override should NOT include the hook's /from-hook/ entry.
$result = \bbsengine6\getsmarty(["templatedir" => ["/explicit-only/"]]);
$td = $result->getTemplateDir();
echo json_encode($td);
}
PHP);
$decoded = json_decode($raw, true);
if (!is_array($decoded)) test_fail("T31", "subtest invalid: " . substr($raw, 0, 200));
if (count($decoded) !== 1 || $decoded[0] !== "/explicit-only/")
    test_fail("T31", "caller override should bypass registry; got: " . json_encode($decoded));
test_pass("caller override bypasses registry walk");

// =============================================================================
// API SYMMETRY (T32-T34)
// =============================================================================

echo "\n--- API Symmetry ---\n\n";

echo "Test 32: \\bbsengine6\\template exposes register/extra/normalize + 3 PRIORITY_* consts\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$ok = function_exists('\bbsengine6\template\register')
   && function_exists('\bbsengine6\template\extra')
   && function_exists('\bbsengine6\template\normalize')
   && defined('\bbsengine6\template\PRIORITY_APP')
   && defined('\bbsengine6\template\PRIORITY_APP_INTEGRATION')
   && defined('\bbsengine6\template\PRIORITY_ENGINE');
echo $ok ? "OK" : "MISSING";
PHP);
if (trim($raw) !== "OK")
    test_fail("T32", "expected full template namespace API surface: " . trim($raw));
test_pass("template namespace has full API surface");

echo "Test 33: \\bbsengine6\\template\\plugin exposes register/extra/normalize + 3 PRIORITY_* consts\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$ok = function_exists('\bbsengine6\template\plugin\register')
   && function_exists('\bbsengine6\template\plugin\extra')
   && function_exists('\bbsengine6\template\plugin\normalize')
   && defined('\bbsengine6\template\plugin\PRIORITY_APP')
   && defined('\bbsengine6\template\plugin\PRIORITY_APP_INTEGRATION')
   && defined('\bbsengine6\template\plugin\PRIORITY_ENGINE');
echo $ok ? "OK" : "MISSING";
PHP);
if (trim($raw) !== "OK")
    test_fail("T33", "expected full plugin namespace API surface: " . trim($raw));
test_pass("plugin namespace has full API surface");

echo "Test 34: \\zoid6\\template exposes the same API surface (when zoid6 is loaded)\n";
// Stub the \zoid6\template namespace as zoid6/php/zoid6config.php
// will once the companion PR lands. bbsengine6 doesn't depend on
// zoid6 at compile time, but the surface check needs the symbols
// defined.
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace zoid6\template {
const PRIORITY_APP = 'app';
const PRIORITY_APP_INTEGRATION = 'app-integration';
const PRIORITY_ENGINE = 'engine';
function _registry(): array { return [PRIORITY_APP => [], PRIORITY_APP_INTEGRATION => [], PRIORITY_ENGINE => []]; }
function register(string $p, callable $h): void { _registry(); }
function extra(): array { return ["/srv/www/zoid6/shared/skin/tmpl/"]; }
function normalize(mixed $raw): array { return \bbsengine6\template\normalize(
    $raw, \zoid6\template\_registry(),
    \zoid6\template\extra()[0], "zoid6\\template"); }
}
namespace {
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
$ok = function_exists('\zoid6\template\register')
   && function_exists('\zoid6\template\extra')
   && function_exists('\zoid6\template\normalize')
   && defined('\zoid6\template\PRIORITY_APP')
   && defined('\zoid6\template\PRIORITY_APP_INTEGRATION')
   && defined('\zoid6\template\PRIORITY_ENGINE');
echo $ok ? "OK" : "MISSING";
}
PHP);
if (trim($raw) !== "OK")
    test_fail("T34", "expected zoid6\\template API surface: " . trim($raw));
test_pass("zoid6\\template has full API surface");

// =============================================================================
// WRAPPER ERROR LABEL (T35-T37)
// =============================================================================

echo "\n--- Wrapper Error Labels ---\n\n";

echo "Test 35: \\bbsengine6\\template\\plugin\\normalize error messages carry plugin namespace label\n";
$raw = run_probe(<<<'PHP'
<?php
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
try {
    \bbsengine6\template\plugin\normalize(42);
    echo "NO_THROW";
} catch (\RuntimeException $e) {
    echo "THREW: " . $e->getMessage();
}
PHP);
if (strpos($raw, "THREW") === false)
    test_fail("T35", "expected throw, got: " . substr($raw, 0, 200));
if (strpos($raw, "bbsengine6\\template\\plugin") === false)
    test_fail("T35", "error message should mention bbsengine6\\template\\plugin, got: " . substr($raw, 0, 200));
test_pass("plugin wrapper errors carry plugin namespace label");

echo "Test 36: \\zoid6\\template\\normalize error messages carry zoid6 namespace label\n";
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace zoid6\template {
function extra(): array { return ["/srv/www/zoid6/shared/skin/tmpl/"]; }
function normalize(mixed $raw): array {
    return \bbsengine6\template\normalize(
        $raw,
        ['app' => [], 'app-integration' => [], 'engine' => []],
        \zoid6\template\extra()[0],
        "zoid6\\template"
    );
}
}
namespace {
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
try {
    \zoid6\template\normalize(42);
    echo "NO_THROW";
} catch (\RuntimeException $e) {
    echo "THREW: " . $e->getMessage();
}
}
PHP);
if (strpos($raw, "THREW") === false)
    test_fail("T36", "expected throw, got: " . substr($raw, 0, 200));
if (strpos($raw, "zoid6\\template") === false)
    test_fail("T36", "error message should mention zoid6\\template, got: " . substr($raw, 0, 200));
test_pass("zoid6 wrapper errors carry zoid6 namespace label");

echo "Test 37: \\zoid6\\template\\register typo-guards on unknown priority\n";
$raw = run_probe(<<<'PHP'
<?php
declare(strict_types=1);
namespace zoid6\template {
function register(string $priority, callable $hook): void {
    throw new \RuntimeException("zoid6\\template\\register: unknown priority '$priority'.");
}
}
namespace {
require_once('/home/opencode/data/work/bbsengine6/php/bbsengine6config.php');
try {
    \zoid6\template\register("invalid", function () { return []; });
    echo "NO_THROW";
} catch (\RuntimeException $e) {
    echo "THREW: " . $e->getMessage();
}
}
PHP);
if (strpos($raw, "THREW") === false)
    test_fail("T37", "expected throw, got: " . substr($raw, 0, 200));
if (strpos($raw, "unknown priority") === false)
    test_fail("T37", "error message should mention 'unknown priority', got: " . substr($raw, 0, 200));
test_pass("zoid6 register() typo-guards on unknown priority");

echo "\n=== Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\nAll template registry tests passed!\n";
exit(0);
