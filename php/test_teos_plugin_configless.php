<?php
/**
 * test_teos_plugin_configless.php — Verify {teos} runs without
 * vhost config.php / database.php / engine.php on include_path.
 *
 * Regression test for the 2026-09-29 journal entry
 *   PHP Warning: require_once(config.php): Failed to open stream
 * which surfaced under mod_env + mod_rewrite + mod_proxy_fcgi
 * combos where VHOSTDOCROOT / VHOSTCONFIG did not propagate to
 * FPM. The previous fix (a9957a5 "fix(smarty/*): re-establish
 * vhost docroot on include_path at plugin load") was a defensive
 * workaround; this test pins the contract that the plugin no
 * longer relies on include_path for config.php at all.
 *
 * Usage:
 *   php test_teos_plugin_configless.php
 */

$bbsengine6_root = "/home/opencode/data/work/bbsengine6";
$smarty_lib      = "/srv/www/smarty-4.5.3/libs";

if (!is_dir($bbsengine6_root)) {
    fwrite(STDERR, "FATAL: bbsengine6 install not found at $bbsengine6_root\n");
    exit(2);
}
if (!is_dir($smarty_lib)) {
    $smarty_lib = $bbsengine6_root . "/vendor/smarty/smarty/libs";
    if (!is_dir($smarty_lib)) {
        fwrite(STDERR, "FATAL: smarty library not found (tried /srv/www/smarty-4.5.3/libs and $bbsengine6_root/vendor/smarty/smarty/libs)\n");
        exit(2);
    }
}

require_once $smarty_lib . "/Smarty.class.php";

putenv("BBSENGINEROOT=$bbsengine6_root");
putenv("TEOSURL=/test-teos/");

require_once $bbsengine6_root . "/smarty/function.teos.php";

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

echo "=== {teos} config-less plugin tests ===\n\n";

// -----------------------------------------------------------------------------
// Test 1: smarty_function_teos is defined after loading the plugin file.
// -----------------------------------------------------------------------------
echo "Test 1: smarty_function_teos is defined after require_once\n";
if (!function_exists('smarty_function_teos')) {
    test_fail("smarty_function_teos is not defined", "require_once did not register the callable");
}
test_pass("smarty_function_teos is defined");

// -----------------------------------------------------------------------------
// Test 2: \\bbsengine6\\util\\env is loaded by the plugin on first
// render (via BBSENGINEROOT require), proving the plugin doesn't
// depend on engine.php for it. util.php is required lazily inside
// smarty_function_teos so missing BBSENGINEROOT raises inside the
// render path, not as a fatal at file-scope.
// -----------------------------------------------------------------------------
echo "Test 2: \\bbsengine6\\util\\env is loaded after first render\n";
if (function_exists('bbsengine6\\util\\env')) {
    test_fail(
        "\\bbsengine6\\util\\env is already defined before any render",
        "plugin loads util.php eagerly; expected lazy load on first render"
    );
}
test_pass("\\bbsengine6\\util\\env not loaded at file scope (lazy load)");

// Trigger a render to force the lazy require.
$tmpdir = sys_get_temp_dir() . "/bbsengine6-teos-test-" . getmypid();
@mkdir("$tmpdir/templates", 0775, true);
@mkdir("$tmpdir/templates_c", 0775, true);
copy(
    $bbsengine6_root . "/skin/tmpl/function.teos.tmpl",
    "$tmpdir/templates/function.teos.tmpl"
);
file_put_contents("$tmpdir/templates/caller.tmpl", "{teos path=\"rec.arts.tv.the-a-team\"}\n");

$smarty_lazy = new Smarty();
$smarty_lazy->setTemplateDir("$tmpdir/templates");
$smarty_lazy->setCompileDir("$tmpdir/templates_c");
$smarty_lazy->setPluginsDir([
    $bbsengine6_root . "/smarty/",
    $smarty_lib . "/plugins/",
]);
$smarty_lazy->fetch("caller.tmpl");

if (!function_exists('bbsengine6\\util\\env')) {
    test_fail("\\bbsengine6\\util\\env is not defined after first render", "BBSENGINEROOT require path did not load util.php");
}
test_pass("\\bbsengine6\\util\\env loaded after first render");

// -----------------------------------------------------------------------------
// Test 3: Render {teos path="..."} through a parent Smarty instance and
// verify the output uses TEOSURL from env (not from a config.php constant).
// -----------------------------------------------------------------------------
echo "Test 3: {teos} renders with TEOSURL from env (no config.php)\n";

// Build a minimal Smarty setup. We deliberately do NOT call
// \\bbsengine6\\getsmarty() because that requires SMARTYTEMPLATESDIR
// etc. defined by config.php. Instead, we replicate the minimum: a
// Smarty instance with the bbsengine6/smarty/ plugin dir and a
// temp template dir containing a copy of function.teos.tmpl.
// Test 2 already created $tmpdir; reuse it.
$smarty = new Smarty();
$smarty->setTemplateDir("$tmpdir/templates");
$smarty->setCompileDir("$tmpdir/templates_c");
$smarty->setPluginsDir([
    $bbsengine6_root . "/smarty/",
    $smarty_lib . "/plugins/",
]);

$rendered = $smarty->fetch("caller.tmpl");

if (strpos($rendered, 'href="/test-teos/rec/arts/tv/the-a-team/"') === false) {
    test_fail(
        "rendered output does not contain expected href",
        "got: " . substr($rendered, 0, 200)
    );
}
test_pass("rendered href uses TEOSURL from env");

if (strpos($rendered, 'data-contenturl="/test-teos/rec/arts/tv/the-a-team/detail?bare"') === false) {
    test_fail(
        "rendered output does not contain expected data-contenturl",
        "got: " . substr($rendered, 0, 200)
    );
}
test_pass("rendered data-contenturl uses TEOSURL from env");

// -----------------------------------------------------------------------------
// Test 4: When TEOSURL is unset, the default NEEDINFO marker surfaces
// in the rendered HTML rather than an empty string.
//
// Runs in a subprocess because PHP constants are process-global: once
// Test 3 has defined TEOSURL via the plugin, putenv("TEOSURL") alone
// can't undefine it for this process.
// -----------------------------------------------------------------------------
echo "Test 4: missing TEOSURL surfaces NEEDINFO marker in rendered HTML\n";

$child_script = <<<'PHP'
<?php
$bbsengine6_root = getenv("BBSENGINEROOT");
$smarty_lib = "/srv/www/smarty-4.5.3/libs";
require_once $smarty_lib . "/Smarty.class.php";
require_once $bbsengine6_root . "/smarty/function.teos.php";

$tmpdir = sys_get_temp_dir() . "/bbsengine6-teos-test-child";
@mkdir("$tmpdir/templates", 0775, true);
@mkdir("$tmpdir/templates_c", 0775, true);
copy("$bbsengine6_root/skin/tmpl/function.teos.tmpl", "$tmpdir/templates/function.teos.tmpl");
file_put_contents("$tmpdir/templates/caller.tmpl", "{teos path=\"rec.arts.tv.the-a-team\"}\n");

$smarty = new Smarty();
$smarty->setTemplateDir("$tmpdir/templates");
$smarty->setCompileDir("$tmpdir/templates_c");
$smarty->setPluginsDir([$bbsengine6_root . "/smarty/", $smarty_lib . "/plugins/"]);
echo $smarty->fetch("caller.tmpl");
PHP;

$child_file = tempnam(sys_get_temp_dir(), 'bbsengine6-teos-child-');
file_put_contents($child_file, $child_script);

$env = [
    "BBSENGINEROOT" => $bbsengine6_root,
    "PATH"          => getenv("PATH"),
];
$descriptors = [0 => ["pipe", "r"], 1 => ["pipe", "w"], 2 => ["pipe", "w"]];
$proc = proc_open(["php", $child_file], $descriptors, $pipes, null, $env);
if (!is_resource($proc)) {
    test_fail("could not start child php process for Test 4");
}
$child_out = stream_get_contents($pipes[1]);
fclose($pipes[1]);
fclose($pipes[2]);
proc_close($proc);
unlink($child_file);

if (strpos($child_out, 'NEEDINFO:function.teos.100:TEOSURL') === false) {
    test_fail(
        "NEEDINFO marker not present in child-process output",
        "got: " . substr($child_out, 0, 200)
    );
}
test_pass("NEEDINFO marker surfaces in rendered HTML");

// -----------------------------------------------------------------------------
// Test 5: Missing BBSENGINEROOT raises a clear RuntimeException, not a
// silent include_once warning. Also runs in a subprocess for the same
// reason (PHP constants persist in the parent).
// -----------------------------------------------------------------------------
echo "Test 5: missing BBSENGINEROOT raises RuntimeException\n";

$child_script5 = <<<'PHP'
<?php
$bbsengine6_root = "/home/opencode/data/work/bbsengine6";
$smarty_lib = "/srv/www/smarty-4.5.3/libs";
require_once $smarty_lib . "/Smarty.class.php";
require_once $bbsengine6_root . "/smarty/function.teos.php";

$tmpdir = sys_get_temp_dir() . "/bbsengine6-teos-test-child5";
@mkdir("$tmpdir/templates", 0775, true);
@mkdir("$tmpdir/templates_c", 0775, true);
copy("$bbsengine6_root/skin/tmpl/function.teos.tmpl", "$tmpdir/templates/function.teos.tmpl");
file_put_contents("$tmpdir/templates/caller.tmpl", "{teos path=\"rec.arts.tv.the-a-team\"}\n");

$smarty = new Smarty();
$smarty->setTemplateDir("$tmpdir/templates");
$smarty->setCompileDir("$tmpdir/templates_c");
$smarty->setPluginsDir([$bbsengine6_root . "/smarty/", $smarty_lib . "/plugins/"]);
try {
    $smarty->fetch("caller.tmpl");
    echo "NO_EXCEPTION";
} catch (\RuntimeException $e) {
    echo "RUNTIME_EXCEPTION:" . $e->getMessage();
}
PHP;

$child_file5 = tempnam(sys_get_temp_dir(), 'bbsengine6-teos-child5-');
file_put_contents($child_file5, $child_script5);

// Intentionally omit BBSENGINEROOT from $env.
$env5 = ["PATH" => getenv("PATH")];
$descriptors5 = [0 => ["pipe", "r"], 1 => ["pipe", "w"], 2 => ["pipe", "w"]];
$proc5 = proc_open(["php", $child_file5], $descriptors5, $pipes5, null, $env5);
if (!is_resource($proc5)) {
    test_fail("could not start child php process for Test 5");
}
$child_out5 = stream_get_contents($pipes5[1]);
$child_err5 = stream_get_contents($pipes5[2]);
fclose($pipes5[1]);
fclose($pipes5[2]);
proc_close($proc5);
unlink($child_file5);

if (strpos($child_out5, 'RUNTIME_EXCEPTION') === false) {
    test_fail(
        "missing BBSENGINEROOT did not raise RuntimeException",
        "stdout: " . substr($child_out5, 0, 200) . " stderr: " . substr($child_err5, 0, 400)
    );
}
if (strpos($child_out5, 'BBSENGINEROOT') === false) {
    test_fail(
        "RuntimeException message does not mention BBSENGINEROOT",
        "stdout: " . substr($child_out5, 0, 200) . " stderr: " . substr($child_err5, 0, 400)
    );
}
test_pass("missing BBSENGINEROOT raises RuntimeException");

// -----------------------------------------------------------------------------
// Test 6: Static guard -- the plugin file must not contain a bare
// require_once("config.php"). This is the literal regression marker.
// -----------------------------------------------------------------------------
echo "Test 6: function.teos.php does not bare-require config.php\n";

$src = file_get_contents($bbsengine6_root . "/smarty/function.teos.php");
if (preg_match('/require_once\s*\(\s*["\']config\.php["\']\s*\)/', $src)) {
    test_fail("function.teos.php still contains require_once(\"config.php\")");
}
test_pass("function.teos.php has no bare require_once(\"config.php\")");

// -----------------------------------------------------------------------------
// Test 7: Static guard -- the plugin file must not bare-require engine.php.
// -----------------------------------------------------------------------------
echo "Test 7: function.teos.php does not bare-require engine.php\n";

if (preg_match('/require_once\s*\(\s*["\']engine\.php["\']\s*\)/', $src)) {
    test_fail("function.teos.php still contains require_once(\"engine.php\")");
}
test_pass("function.teos.php has no bare require_once(\"engine.php\")");

// -----------------------------------------------------------------------------
// Cleanup
// -----------------------------------------------------------------------------
@unlink("$tmpdir/templates/caller.tmpl");
@unlink("$tmpdir/templates/function.teos.tmpl");
@rmdir("$tmpdir/templates");
@unlink("$tmpdir/templates_c/caller.tmpl.php");
@rmdir("$tmpdir/templates_c");
@rmdir("$tmpdir");

echo "\n=== Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\nAll {teos} config-less plugin tests passed!\n";
exit(0);
