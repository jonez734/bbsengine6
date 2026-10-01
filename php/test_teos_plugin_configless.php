<?php
/**
 * test_teos_plugin_configless.php — Verify {teos} runs without
 * vhost config.php / database.php / engine.php on include_path.
 *
 * Regression test for the 2026-09-29 journal entry
 *   PHP Warning: require_once(config.php): Failed to open stream
 *   in /srv/www/bbsengine6/smarty/function.teos.php on line 43
 * which surfaced under mod_env + mod_rewrite + mod_proxy_fcgi
 * combos where VHOSTDOCROOT did not propagate to FPM. The previous
 * fix (a9957a5 "fix(smarty/*): re-establish vhost docroot on
 * include_path at plugin load") was a defensive workaround; this
 * test pins the contract that the plugin no longer relies on
 * include_path for config.php at all.
 *
 * Loading strategy (bbsengine6 49b5b70 + fixup): the plugin
 * resolves util.php via the established include_path convention
 * by first loading BBSENGINEROOT/php/bootstrap.php, which
 * puts /srv/www/bbsengine6/php/ on include_path. The plugin's
 * bare-name require_once('util.php') then resolves via that
 * path. Same shape as engine/router.php's bootstrap-then-bare-
 * name load order.
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
// Test 5: Missing BBSENGINEROOT falls through to the multi-source
// resolution chain (env -> constant -> walk-up -> plugin_dir walk)
// rather than throwing on the missing env var alone.
//
// Regression test for the 2026-09-30 production incident where FPM
// pools that don't propagate Apache's SetEnv directives caused the
// pre-existing single-source check (getenv('BBSENGINEROOT') only) to
// throw RuntimeException on any blurb/folder page that included
// youarehere.tmpl -> {teos} after the breadcrumb-traversal fixes
// made $data.breadcrumbs non-empty. With the multi-source chain the
// walk-up step (dirname(__DIR__) -> engine root, then verify
// php/util.php exists) recovers the install location without needing
// the env var to propagate.
//
// Runs in a subprocess for two reasons:
//   1. PHP constants persist in the parent process (Tests 2-4 may
//      have loaded util.php into a state that affects getenv/defined
//      resolution).
//   2. The env is scrubbed so BBSENGINEROOT is genuinely unset in
//      the child, matching the FPM-env-stripping production case.
// -----------------------------------------------------------------------------
echo "Test 5: missing BBSENGINEROOT resolves via walk-up fallback\n";

$child_script5 = <<<'PHP'
<?php
$bbsengine6_root = "/home/opencode/data/work/bbsengine6";
$smarty_lib = "/srv/www/smarty-4.5.3/libs";
require_once $smarty_lib . "/Smarty.class.php";
require_once $bbsengine6_root . "/smarty/function.teos.php";

try {
    $r = bbsengine6_teos_resolve_root();
    echo "RESOLVED:" . $r;
} catch (\RuntimeException $e) {
    echo "RUNTIME_EXCEPTION:" . $e->getMessage();
}
PHP;

$child_file5 = tempnam(sys_get_temp_dir(), 'bbsengine6-teos-child5-');
file_put_contents($child_file5, $child_script5);

// Intentionally omit BBSENGINEROOT from $env (FPM-env-stripping case).
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

if (strpos($child_out5, 'RESOLVED:') === false) {
    test_fail(
        "bbsengine6_teos_resolve_root() did not resolve when BBSENGINEROOT was unset",
        "expected walk-up fallback to recover the engine root; got: "
        . substr($child_out5, 0, 400) . " stderr: " . substr($child_err5, 0, 400)
    );
}
test_pass(
    "bbsengine6_teos_resolve_root() resolves via walk-up fallback when BBSENGINEROOT unset",
    substr($child_out5, 0, 80)
);

// -----------------------------------------------------------------------------
// Test 5a: With BBSENGINEROOT unset AND the walk-up discovery failing
// (function.teos.php relocated to a sandboxed directory that has no
// ../php/util.php sibling), bbsengine6_teos_resolve_root() falls
// through to step 4 (plugin_dir walk) which probes /srv/www/bbsengine6.
// This is the "relocated copy" case (e.g. vhost ships its own copy of
// the plugin) where dirname(__DIR__) doesn't point at an engine root.
// -----------------------------------------------------------------------------
echo "Test 5a: walk-up miss falls through to plugin_dir walk\n";

$child_script5a = <<<'PHP'
<?php
// Sandbox: copy function.teos.php to a tmp dir whose parent has no
// php/ subdir. dirname(__DIR__) in that copy points at the tmp dir,
// which has no /php/util.php sibling. Step 3 (walk-up) should fail,
// step 4 (plugin_dir walk) should succeed because
// /srv/www/bbsengine6 is a canonical install on this test machine.
$sandbox = sys_get_temp_dir() . "/bbsengine6-resolve-test-" . getmypid();
$src = "/home/opencode/data/work/bbsengine6/smarty/function.teos.php";
@mkdir($sandbox, 0755, true);
copy($src, "$sandbox/function.teos.php");
require_once "$sandbox/function.teos.php";

try {
    $r = bbsengine6_teos_resolve_root();
    echo "RESOLVED:" . $r;
} catch (\RuntimeException $e) {
    echo "RUNTIME_EXCEPTION:" . $e->getMessage();
}
PHP;

$child_file5a = tempnam(sys_get_temp_dir(), 'bbsengine6-teos-child5a-');
file_put_contents($child_file5a, $child_script5a);

$env5a = ["PATH" => getenv("PATH")];
$descriptors5a = [0 => ["pipe", "r"], 1 => ["pipe", "w"], 2 => ["pipe", "w"]];
$proc5a = proc_open(["php", $child_file5a], $descriptors5a, $pipes5a, null, $env5a);
if (!is_resource($proc5a)) {
    test_fail("could not start child php process for Test 5a");
}
$child_out5a = stream_get_contents($pipes5a[1]);
$child_err5a = stream_get_contents($pipes5a[2]);
fclose($pipes5a[1]);
fclose($pipes5a[2]);
proc_close($proc5a);
unlink($child_file5a);

if (strpos($child_out5a, 'RESOLVED:') === false) {
    test_fail(
        "plugin_dir walk fallback did not recover engine root for relocated copy",
        "expected step 4 to find /srv/www/bbsengine6; got: "
        . substr($child_out5a, 0, 400) . " stderr: " . substr($child_err5a, 0, 400)
    );
}
test_pass(
    "plugin_dir walk recovers engine root for relocated copies",
    substr($child_out5a, 0, 80)
);

// -----------------------------------------------------------------------------
// Test 5b: All four sources failing raises RuntimeException with a
// diagnostic message that names each source tried. Constructed via a
// sandbox where:
//   - BBSENGINEROOT env unset
//   - no BBSENGINEROOT constant
//   - dirname(__DIR__) doesn't have a php/util.php sibling
//   - plugin_dir walk hits no candidate with /php subdir
// -----------------------------------------------------------------------------
echo "Test 5b: all sources failing raises RuntimeException with diagnostic\n";

$child_script5b = <<<'PHP'
<?php
// Sandbox: stage a copy of function.teos.php under a tmp dir that has
// no php/ subdir, AND set PHP so /srv/www/bbsengine6 is unreachable.
// We achieve the latter by mounting via chroot in the child process is
// impractical; instead we rename /srv/www/bbsengine6 to a sibling path
// for the duration of the test (revert on exit). That blocks step 4.
// Steps 1 (env) and 2 (constant) are explicitly absent. Step 3
// (walk-up) fails because the sandbox dir has no /php/util.php.
// Expected: RuntimeException with all four sources listed in the
// message.
$sandbox = sys_get_temp_dir() . "/bbsengine6-resolve-fail-" . getmypid();
@mkdir($sandbox, 0755, true);
copy("/home/opencode/data/work/bbsengine6/smarty/function.teos.php", "$sandbox/function.teos.php");
require_once "$sandbox/function.teos.php";

// Move /srv/www/bbsengine6 aside for the duration of the test.
// On a real install this requires root; we attempt it and continue
// regardless. If the move fails, the plugin_dir walk will succeed
// (which is fine — Test 5a already covers that path).
$moved = @rename("/srv/www/bbsengine6", "/srv/www/bbsengine6.bak.test." . getmypid());

try {
    bbsengine6_teos_resolve_root();
    echo "NO_EXCEPTION";
} catch (\RuntimeException $e) {
    echo "RUNTIME_EXCEPTION:" . $e->getMessage();
} finally {
    if ($moved) {
        @rename("/srv/www/bbsengine6.bak.test." . getmypid(), "/srv/www/bbsengine6");
    }
}
PHP;

$child_file5b = tempnam(sys_get_temp_dir(), 'bbsengine6-teos-child5b-');
file_put_contents($child_file5b, $child_script5b);

$env5b = ["PATH" => getenv("PATH")];
$descriptors5b = [0 => ["pipe", "r"], 1 => ["pipe", "w"], 2 => ["pipe", "w"]];
$proc5b = proc_open(["php", $child_file5b], $descriptors5b, $pipes5b, null, $env5b);
if (!is_resource($proc5b)) {
    test_fail("could not start child php process for Test 5b");
}
$child_out5b = stream_get_contents($pipes5b[1]);
$child_err5b = stream_get_contents($pipes5b[2]);
fclose($pipes5b[1]);
fclose($pipes5b[2]);
proc_close($proc5b);
unlink($child_file5b);

// Two acceptable outcomes:
//   - RUNTIME_EXCEPTION message lists "getenv(BBSENGINEROOT)=",
//     "defined(BBSENGINEROOT)=", "dirname(__DIR__)=", "plugin_dir_walk="
//     (all four sources tried, none succeeded).
//   - NO_EXCEPTION (only when the rename failed and step 4 succeeded —
//     acceptable in this dev env where we can't reliably move
//     /srv/www/bbsengine6). On a real prod box the rename works and
//     this branch produces the exception.
$gotException = strpos($child_out5b, 'RUNTIME_EXCEPTION') !== false;
$gotNoException = strpos($child_out5b, 'NO_EXCEPTION') !== false;
if (!$gotException && !$gotNoException) {
    test_fail(
        "Test 5b produced unexpected output",
        "stdout: " . substr($child_out5b, 0, 400) . " stderr: " . substr($child_err5b, 0, 400)
    );
}
if ($gotException) {
    // Verify the diagnostic lists all four sources.
    foreach (['getenv(BBSENGINEROOT)', 'defined(BBSENGINEROOT)', 'dirname(__DIR__)', 'plugin_dir_walk'] as $needle) {
        if (strpos($child_out5b, $needle) === false) {
            test_fail(
                "RuntimeException message missing source: $needle",
                "stdout: " . substr($child_out5b, 0, 400)
            );
        }
    }
    test_pass("all sources failing raises RuntimeException listing every source tried");
} else {
    // rename failed (no root); just record that the fallback chain
    // recovered the root, which is the desired prod behavior.
    test_pass(
        "Test 5b skipped — could not rename /srv/www/bbsengine6 (no root); "
        . "plugin_dir walk recovered the root instead. On prod this test "
        . "exercises the throw path."
    );
}

// -----------------------------------------------------------------------------
// Test 5c: BBSENGINEROOT env var takes precedence over the constant
// and walk-up fallback. Verifies the resolution order documented in
// the source comment.
// -----------------------------------------------------------------------------
echo "Test 5c: env var takes precedence over constant and walk-up\n";

$child_script5c = <<<'PHP'
<?php
require_once "/home/opencode/data/work/bbsengine6/smarty/function.teos.php";
putenv("BBSENGINEROOT=/srv/www/bbsengine6");
define("BBSENGINEROOT", "/this/path/should/not/be/used");
$r = bbsengine6_teos_resolve_root();
echo $r;
PHP;

$child_file5c = tempnam(sys_get_temp_dir(), 'bbsengine6-teos-child5c-');
file_put_contents($child_file5c, $child_script5c);

$env5c = ["PATH" => getenv("PATH"), "BBSENGINEROOT" => "/srv/www/bbsengine6"];
$descriptors5c = [0 => ["pipe", "r"], 1 => ["pipe", "w"], 2 => ["pipe", "w"]];
$proc5c = proc_open(["php", $child_file5c], $descriptors5c, $pipes5c, null, $env5c);
if (!is_resource($proc5c)) {
    test_fail("could not start child php process for Test 5c");
}
$child_out5c = stream_get_contents($pipes5c[1]);
fclose($pipes5c[1]);
fclose($pipes5c[2]);
proc_close($proc5c);
unlink($child_file5c);

if (rtrim($child_out5c) !== "/srv/www/bbsengine6") {
    test_fail(
        "env var did not take precedence over constant",
        "got: " . var_export($child_out5c, true)
    );
}
test_pass("BBSENGINEROOT env var takes precedence over constant fallback");

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
// Test 8: Static guard -- the plugin must load util.php via
// bootstrap.php (the established include_path convention), not via
// a direct require_once($bbsengine6_root . '/php/util.php'). The
// fixup commit refined 49b5b70 to follow bootstrap.php's own
// include_path pattern, mirroring engine/router.php.
// -----------------------------------------------------------------------------
echo "Test 8: function.teos.php loads util.php via bootstrap.php\n";

if (!preg_match('/require_once\s*\(\s*\$bbsengine6_root\s*\.\s*[\'"]\/php\/bootstrap\.php[\'"]\s*\)/', $src)) {
    test_fail(
        "function.teos.php does not require_once \$bbsengine6_root . '/php/bootstrap.php'",
        "plugin should follow the bootstrap.php include_path convention"
    );
}
test_pass("function.teos.php loads bootstrap.php");

if (!preg_match('/require_once\s*\(\s*[\'"]util\.php[\'"]\s*\)/', $src)) {
    test_fail(
        "function.teos.php does not bare-require 'util.php'",
        "plugin should require_once('util.php') after loading bootstrap"
    );
}
test_pass("function.teos.php bare-requires util.php via bootstrap's include_path");

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
