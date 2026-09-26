<?php
/**
 * test_router_vhostconfig.php — Verifies engine/vhostconfig.php's
 * VHOSTCONFIG resolution contract:
 *
 *   1. VHOSTCONFIG env var (absolute path) wins when set and readable.
 *   2. SCRIPT_FILENAME fallback walks up to html/ and probes known
 *      vhost subdirs (config.php, teos/, org/, com/, bbsengine.org/).
 *   3. Nothing resolvable -> return false; caller emits a warning.
 *
 * Style mirrors test_smarty_template.php: CLI-driven, exits 1
 * on first failure. Tests run in child PHP processes so we can probe
 * different env/SCRIPT_FILENAME setups without polluting the parent.
 *
 * @since 2026-09-24
 */

set_include_path("/home/opencode/data/work/bbsengine6/php:" . get_include_path());

echo "=== Router VHOSTCONFIG Tests ===\n\n";

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
 * Run a generated PHP probe in a child process. The probe script is
 * written to a temp file and executed via `php`. Returns the child's
 * stdout+stderr as a string.
 *
 * $env overrides may be set to control the child process's env vars
 * (VHOSTCONFIG, SCRIPT_FILENAME, etc.). They are exported inline
 * before `php` so the child sees them via getenv().
 */
function run_router_probe(string $probePhp, array $env = []): string {
    $probe = tempnam(sys_get_temp_dir(), 'bbsengine6_rvc_');
    file_put_contents($probe, $probePhp);

    $envPrefix = '';
    foreach ($env as $k => $v) {
        // Export inline. escapeshellarg() protects both sides.
        $envPrefix .= $k . '=' . escapeshellarg($v) . ' ';
    }

    $cmd = $envPrefix
         . "php "
         . "-d display_errors=0 -d log_errors=0 "
         . escapeshellarg($probe) . " 2>&1";
    $output = shell_exec($cmd);
    unlink($probe);
    return (string)$output;
}

/**
 * Build a fake vhost tree under a temp dir and return key paths.
 * Mirrors the /srv/www/vhosts/<host>/html/<vhost>/config.php layout.
 */
function setup_fake_vhost(string $vhostName, string $marker): array {
    $root = sys_get_temp_dir() . '/bbsengine6_rvc_' . bin2hex(random_bytes(4));
    $htmlDir = $root . '/html';
    @mkdir($htmlDir . '/engine', 0755, true);
    if ($vhostName !== '') {
        @mkdir($htmlDir . '/' . $vhostName, 0755, true);
        file_put_contents($htmlDir . '/' . $vhostName . '/config.php',
            "<?php\n"
          . "define('FAKE_VHOST_CONFIG_LOADED', '" . addslashes($marker) . "');\n");
    } else {
        file_put_contents($htmlDir . '/config.php',
            "<?php\n"
          . "define('FAKE_VHOST_CONFIG_LOADED', '" . addslashes($marker) . "');\n");
    }
    return [
        'root'   => $root,
        'html'   => $htmlDir,
        'engine' => $htmlDir . '/engine',
    ];
}

function teardown_fake_vhost(array $info): void {
    if (!is_dir($info['root'])) return;
    $rii = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($info['root'], RecursiveDirectoryIterator::SKIP_DOTS),
        RecursiveIteratorIterator::CHILD_FIRST
    );
    foreach ($rii as $f) {
        $f->isDir() ? @rmdir($f->getPathname()) : @unlink($f->getPathname());
    }
    @rmdir($info['root']);
}

// =============================================================================
// VHOSTCONFIG resolution tests
// =============================================================================

echo "Test R1: VHOSTCONFIG env wins when set and readable\n";
$tmpDir = sys_get_temp_dir();
$fakeConfig = $tmpDir . '/fake_vhost_config_' . bin2hex(random_bytes(4)) . '.php';
file_put_contents($fakeConfig,
    "<?php\n"
  . "define('FAKE_VHOST_CONFIG_LOADED', 'env-var-path');\n");
$probePhp = <<<PHP
<?php
require_once('/home/opencode/data/work/bbsengine6/engine/vhostconfig.php');
\$resolved = \\bbsengine6\\router\\router_resolve_vhost_config();
echo "RESOLVED=" . var_export(\$resolved, true) . "\n";
echo "FAKE_VHOST_CONFIG_LOADED=" . (defined('FAKE_VHOST_CONFIG_LOADED') ? FAKE_VHOST_CONFIG_LOADED : 'UNDEFINED') . "\n";
PHP;
$raw = run_router_probe($probePhp, ['VHOSTCONFIG' => $fakeConfig]);
@unlink($fakeConfig);
if (strpos($raw, "FAKE_VHOST_CONFIG_LOADED=env-var-path") === false)
    test_fail("R1", "VHOSTCONFIG env not honored. Output: " . substr($raw, 0, 600));
if (strpos($raw, "RESOLVED=" . $fakeConfig) === false && strpos($raw, "RESOLVED='" . $fakeConfig . "'") === false)
    test_fail("R1", "returned path wrong. Output: " . substr($raw, 0, 600));
test_pass("VHOSTCONFIG env var wins and returns absolute path");

echo "\nTest R2: VHOSTCONFIG pointing at nonexistent file -> falls through\n";
$fake = setup_fake_vhost('teos', 'fake-teos');
$probePhp = <<<PHP
<?php
\$_SERVER['SCRIPT_FILENAME'] = '{$fake['engine']}/router.php';
require_once('/home/opencode/data/work/bbsengine6/engine/vhostconfig.php');
\$resolved = \\bbsengine6\\router\\router_resolve_vhost_config();
echo "RESOLVED=" . var_export(\$resolved, true) . "\n";
echo "FAKE_VHOST_CONFIG_LOADED=" . (defined('FAKE_VHOST_CONFIG_LOADED') ? FAKE_VHOST_CONFIG_LOADED : 'UNDEFINED') . "\n";
PHP;
$raw = run_router_probe($probePhp, ['VHOSTCONFIG' => '/nonexistent/path/to/config.php']);
if (strpos($raw, "FAKE_VHOST_CONFIG_LOADED=fake-teos") === false)
    test_fail("R2", "bad VHOSTCONFIG should fall through to SCRIPT_FILENAME. Output: " . substr($raw, 0, 600));
test_pass("bad VHOSTCONFIG falls through to SCRIPT_FILENAME");
teardown_fake_vhost($fake);

echo "\nTest R3: SCRIPT_FILENAME fallback resolves teos/config.php\n";
$fake = setup_fake_vhost('teos', 'fake-teos');
$probePhp = <<<PHP
<?php
\$_SERVER['SCRIPT_FILENAME'] = '{$fake['engine']}/router.php';
require_once('/home/opencode/data/work/bbsengine6/engine/vhostconfig.php');
\$resolved = \\bbsengine6\\router\\router_resolve_vhost_config();
echo "FAKE_VHOST_CONFIG_LOADED=" . (defined('FAKE_VHOST_CONFIG_LOADED') ? FAKE_VHOST_CONFIG_LOADED : 'UNDEFINED') . "\n";
PHP;
$raw = run_router_probe($probePhp);
if (strpos($raw, "FAKE_VHOST_CONFIG_LOADED=fake-teos") === false)
    test_fail("R3", "teos/config.php not loaded. Output: " . substr($raw, 0, 600));
test_pass("SCRIPT_FILENAME fallback finds html/teos/config.php");
teardown_fake_vhost($fake);

echo "\nTest R4: SCRIPT_FILENAME fallback resolves flat layout (html/config.php)\n";
$fake = setup_fake_vhost('', 'flat-layout');
$probePhp = <<<PHP
<?php
\$_SERVER['SCRIPT_FILENAME'] = '{$fake['engine']}/router.php';
require_once('/home/opencode/data/work/bbsengine6/engine/vhostconfig.php');
\$resolved = \\bbsengine6\\router\\router_resolve_vhost_config();
echo "FAKE_VHOST_CONFIG_LOADED=" . (defined('FAKE_VHOST_CONFIG_LOADED') ? FAKE_VHOST_CONFIG_LOADED : 'UNDEFINED') . "\n";
PHP;
$raw = run_router_probe($probePhp);
if (strpos($raw, "FAKE_VHOST_CONFIG_LOADED=flat-layout") === false)
    test_fail("R4", "flat html/config.php not loaded. Output: " . substr($raw, 0, 600));
test_pass("flat layout (html/config.php) found via SCRIPT_FILENAME fallback");
teardown_fake_vhost($fake);

echo "\nTest R5: nothing resolvable -> returns false (no fatal)\n";
$probePhp = <<<PHP
<?php
unset(\$_SERVER['SCRIPT_FILENAME']);
require_once('/home/opencode/data/work/bbsengine6/engine/vhostconfig.php');
\$resolved = \\bbsengine6\\router\\router_resolve_vhost_config();
echo "RESOLVED=" . var_export(\$resolved, true) . "\n";
echo "NO_FATAL\n";
PHP;
$raw = run_router_probe($probePhp);
if (strpos($raw, "NO_FATAL") === false)
    test_fail("R5", "unexpected fatal when nothing resolvable. Output: " . substr($raw, 0, 600));
if (strpos($raw, "RESOLVED=false") === false)
    test_fail("R5", "expected RESOLVED=false. Output: " . substr($raw, 0, 600));
test_pass("nothing resolvable returns false without fatal");

echo "\nTest R6: VHOSTCONFIG takes precedence over SCRIPT_FILENAME\n";
$fake = setup_fake_vhost('teos', 'fake-teos-would-load-without-env');
$tmpDir = sys_get_temp_dir();
$overrideConfig = $tmpDir . '/override_config_' . bin2hex(random_bytes(4)) . '.php';
file_put_contents($overrideConfig,
    "<?php\n"
  . "define('FAKE_VHOST_CONFIG_LOADED', 'env-overrides-script');\n");
$probePhp = <<<PHP
<?php
\$_SERVER['SCRIPT_FILENAME'] = '{$fake['engine']}/router.php';
require_once('/home/opencode/data/work/bbsengine6/engine/vhostconfig.php');
\$resolved = \\bbsengine6\\router\\router_resolve_vhost_config();
echo "FAKE_VHOST_CONFIG_LOADED=" . (defined('FAKE_VHOST_CONFIG_LOADED') ? FAKE_VHOST_CONFIG_LOADED : 'UNDEFINED') . "\n";
PHP;
$raw = run_router_probe($probePhp, ['VHOSTCONFIG' => $overrideConfig]);
@unlink($overrideConfig);
if (strpos($raw, "FAKE_VHOST_CONFIG_LOADED=env-overrides-script") === false)
    test_fail("R6", "VHOSTCONFIG should win over SCRIPT_FILENAME. Output: " . substr($raw, 0, 600));
test_pass("VHOSTCONFIG takes precedence over SCRIPT_FILENAME fallback");
teardown_fake_vhost($fake);

echo "\nTest R7: empty VHOSTCONFIG -> falls through\n";
$fake = setup_fake_vhost('org', 'fake-org');
$probePhp = <<<PHP
<?php
\$_SERVER['SCRIPT_FILENAME'] = '{$fake['engine']}/router.php';
require_once('/home/opencode/data/work/bbsengine6/engine/vhostconfig.php');
\$resolved = \\bbsengine6\\router\\router_resolve_vhost_config();
echo "FAKE_VHOST_CONFIG_LOADED=" . (defined('FAKE_VHOST_CONFIG_LOADED') ? FAKE_VHOST_CONFIG_LOADED : 'UNDEFINED') . "\n";
PHP;
$raw = run_router_probe($probePhp, ['VHOSTCONFIG' => '']);
if (strpos($raw, "FAKE_VHOST_CONFIG_LOADED=fake-org") === false)
    test_fail("R7", "empty VHOSTCONFIG should fall through. Output: " . substr($raw, 0, 600));
test_pass("empty VHOSTCONFIG falls through to SCRIPT_FILENAME");
teardown_fake_vhost($fake);

echo "\n=== Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\nAll router VHOSTCONFIG tests passed!\n";
