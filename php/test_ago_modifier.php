<?php
/**
 * test_ago_modifier.php -- Verifies the bbsengine6 `|ago` Smarty modifier
 * is installed and resolves through the org vhost's plugin path.
 *
 * Checks:
 *   1. Install: smarty/modifier.ago.php loads and defines smarty_modifier_ago.
 *   2. Output: fixed offsets from time() return the expected phrases.
 *   3. Registry: \bbsengine6\template\plugin\normalize() on the org vhost's
 *      SMARTYPLUGINSDIR list includes both www/org/smarty/ and bbsengine6/smarty/.
 *   4. Render: a minimal template using |ago renders through getsmarty()
 *      with the org vhost's SMARTYPLUGINSDIR (no dependency on index.tmpl).
 *
 * Usage:
 *   php test_ago_modifier.php
 */

$root = dirname(__DIR__);
set_include_path($root . "/php:" . get_include_path());

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

echo "=== |ago modifier Tests ===\n\n";

// -----------------------------------------------------------------------------
// 1. Install
// -----------------------------------------------------------------------------
echo "Test 1: smarty/modifier.ago.php defines smarty_modifier_ago\n";
$agoFile = $root . "/smarty/modifier.ago.php";
if (!is_file($agoFile)) {
    test_fail("install", "missing $agoFile");
}
require_once($agoFile);
if (!function_exists('smarty_modifier_ago')) {
    test_fail("install", "smarty_modifier_ago() not defined after require");
}
test_pass("install", "smarty_modifier_ago defined");

// -----------------------------------------------------------------------------
// 2. Output strings for fixed offsets from now
// -----------------------------------------------------------------------------
// Sub-minute offsets: time() inside the modifier may tick forward by a
// second or two, so accept the expected count or count+1 (and "a few
// seconds" for zero). Minute and larger ranges are exact.
echo "\nTest 2: output strings for fixed offsets\n";
$now = time();
$exact = [
    ['label' => '1 minute',   'offset' => 60,         'expect' => '1 minute'],
    ['label' => '10 minutes', 'offset' => 600,        'expect' => '10 minutes'],
    ['label' => '1 hour',     'offset' => 3600,       'expect' => '1 hour'],
    ['label' => '5 hours',    'offset' => 5 * 3600,   'expect' => '5 hours'],
    ['label' => '1 day',      'offset' => 86400,      'expect' => '1 day'],
    ['label' => '3 days',     'offset' => 3 * 86400,  'expect' => '3 days'],
    ['label' => '2 weeks',    'offset' => 14 * 86400, 'expect' => '2 weeks'],
];
$tickable = [
    ['label' => 'now (0s)',   'offset' => 0,  'expect' => ['a few seconds']],
    ['label' => '1 second',   'offset' => 1,  'expect' => ['1 second', '2 seconds']],
    ['label' => '30 seconds', 'offset' => 30, 'expect' => ['30 seconds', '31 seconds']],
];
foreach ($tickable as $c) {
    $actual = smarty_modifier_ago($now - $c['offset']);
    if (!in_array($actual, $c['expect'], true)) {
        test_fail("ago {$c['label']}", "expected one of [" . implode(', ', $c['expect']) . "] got [$actual]");
    }
    test_pass("ago {$c['label']}", "[$actual]");
}
foreach ($exact as $c) {
    $actual = smarty_modifier_ago($now - $c['offset']);
    if ($actual !== $c['expect']) {
        test_fail("ago {$c['label']}", "expected [{$c['expect']}] got [$actual]");
    }
    test_pass("ago {$c['label']}", "[$actual]");
}

// -----------------------------------------------------------------------------
// 3. Registry resolution for the org vhost
// -----------------------------------------------------------------------------
echo "\nTest 3: plugin registry includes org and engine smarty/ dirs\n";
if (!is_file($root . "/www/org/config-prod.php")) {
    test_fail("registry", "missing www/org/config-prod.php");
}
require_once($root . "/php/bbsengine6config.php");
// The org vhost's list (www/org/config-prod.php:48) is its own smarty/ dir only.
$orgDir = $root . "/www/org/smarty/";
$engineDir = $root . "/smarty/";
$resolved = \bbsengine6\template\plugin\normalize([0 => $orgDir]);
if (!in_array($orgDir, $resolved, true)) {
    test_fail("registry", "org dir $orgDir not in " . implode(", ", $resolved));
}
if (!in_array($engineDir, $resolved, true)) {
    test_fail("registry", "engine dir $engineDir not in " . implode(", ", $resolved));
}
test_pass("registry", "org and engine plugin dirs both resolved (" . count($resolved) . " entries)");

// -----------------------------------------------------------------------------
// 4. Render a minimal template using |ago through getsmarty()
// -----------------------------------------------------------------------------
echo "\nTest 4: |ago renders through getsmarty() with org SMARTYPLUGINSDIR\n";

// QuickForm2 stub: engine.php requires it. Same convention as
// test_smarty_template.php run_probe().
$stubDir = sys_get_temp_dir() . '/bbsengine6_test_stubs';
if (!is_dir($stubDir . '/HTML/QuickForm2/Element/Captcha')) {
    @mkdir($stubDir . '/HTML/QuickForm2/Element/Captcha', 0755, true);
    file_put_contents($stubDir . '/HTML/QuickForm2/Element/Captcha/ReCaptcha.php',
        '<?php class HTML_QuickForm2_Element_Captcha_ReCaptcha {}');
}

$workDir = sys_get_temp_dir() . '/ago_render_' . getmypid();
$tmplDir = $workDir . '/tmpl';
$compileDir = $workDir . '/compile';
@mkdir($tmplDir, 0755, true);
@mkdir($compileDir, 0755, true);
file_put_contents($tmplDir . '/ago_probe.tmpl', "AGO[{\$ts|ago}]\n");

$probe = $workDir . '/probe.php';
file_put_contents($probe, '<?php
// getcurrenturi() (engine.php) reads these; set them as a web request would.
$_SERVER["REQUEST_SCHEME"] = "https";
$_SERVER["SERVER_NAME"] = "localhost";
$_SERVER["HTTP_HOST"] = "localhost";
$_SERVER["REQUEST_URI"] = "/";
$_SERVER["REQUEST_METHOD"] = "GET";
set_include_path("' . $root . '/php:/srv/www/smarty:/usr/share/pear:/usr/share/php:' . $stubDir . ':" . get_include_path());
// Mirror the org vhost: its SMARTYPLUGINSDIR is only its own smarty/ dir.
define("config\\SMARTYPLUGINSDIR", [0 => "' . $orgDir . '"]);
require_once("' . $root . '/php/bbsengine6config.php");
require_once("' . $root . '/php/engine.php");
$s = \bbsengine6\getsmarty([
    "templatedir" => ["' . $tmplDir . '"],
    "compiledir" => "' . $compileDir . '",
]);
$s->assign("ts", time() - 7200);
echo $s->fetch("ago_probe.tmpl");
');

$out = (string)shell_exec("php -d display_errors=1 " . escapeshellarg($probe) . " 2>&1");

// Clean up before evaluating, so failures don't leak temp files.
$cleanup = function () use ($workDir) {
    if (!is_dir($workDir)) return;
    foreach (['tmpl/ago_probe.tmpl', 'probe.php'] as $f) @unlink($workDir . '/' . $f);
    foreach (glob($workDir . '/compile/*') ?: [] as $f) @unlink($f);
    @rmdir($workDir . '/compile');
    @rmdir($workDir . '/tmpl');
    @rmdir($workDir);
};

if (!preg_match('/AGO\[(2 hours|1 hour)\]/', $out)) {
    $cleanup();
    test_fail("render", "expected AGO[2 hours] or AGO[1 hour]; output: " . substr($out, 0, 400));
}
$cleanup();
test_pass("render", "|ago rendered through getsmarty() with org plugin path");

echo "\n=== Results: $passed passed, $failed failed ===\n";
exit($failed === 0 ? 0 : 1);
