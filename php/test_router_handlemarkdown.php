<?php
/**
 * test_router_handlemarkdown.php - regression test for the
 * 2026-09-19 router_handleMarkdown ".md strip" regression.
 *
 * Pins the filesystem-probe behavior in isolation: the probe
 * must append ".md" to the bare slug it receives from the
 * dispatch loop, because the HTTP entry-point has already
 * stripped ".md" from the URI once at the top of the script.
 *
 * Scope: this test ONLY covers the probe (safe_path_web with
 * <slug>.md) plus negative cases. It deliberately does NOT
 * invoke router_handleMarkdown() as a whole, because that
 * pulls in router_displayMarkdownFile() -> displaypage() ->
 * Smarty compile (with side-effects that depend on the
 * vhost's plugin/skin search paths being healthy), which is
 * orthogonal to the .md-strip regression.
 *
 * Usage:
 *   php test_router_handlemarkdown.php
 */

require_once __DIR__ . "/bootstrap.php";
require_once("util.php");

echo "=== Testing router_handleMarkdown .md probe shape ===\n\n";

// --- helpers --------------------------------------------------------------

function test_pass(string $name) {
    echo "  PASS: $name\n";
}

function test_fail(string $name, string $detail = '') {
    $suffix = $detail !== '' ? " - $detail" : '';
    echo "  FAIL: $name$suffix\n";
    exit(1);
}

// --- fixture --------------------------------------------------------------

$fixtureRoot = sys_get_temp_dir() . "/bbsengine6_test_mdprobe_" . bin2hex(random_bytes(4));
if (!mkdir($fixtureRoot . "/comp/lang/python", 0777, true)) {
    test_fail("could not create fixture root", $fixtureRoot);
}

$marker = "# Variables\n\nBody content here.\n";
$markdownPath = $fixtureRoot . "/comp/lang/python/variables.md";
if (file_put_contents($markdownPath, $marker) === false) {
    test_fail("could not write fixture .md", $markdownPath);
}

// --- Test 1: probe with .md suffix resolves to the on-disk file -----------

echo "Test 1: probe '<slug>.md' resolves to the on-disk file under TEOSDIR\n";
$resolved = \bbsengine6\util\safe_path_web(
    ['comp/lang/python/variables.md'],
    ['base_dir' => $fixtureRoot]
);
if (is_string($resolved) && $resolved === realpath($markdownPath)) {
    test_pass(".md probe resolves to <TEOSDIR>/comp/lang/python/variables.md");
} else {
    test_fail(
        ".md probe did not resolve to the on-disk .md file",
        "got " . var_export($resolved, true)
        . " expected " . realpath($markdownPath)
    );
}

// --- Test 2: bare probe (without .md) does NOT match ----------------------

echo "Test 2: probe '<slug>' (bare) does NOT match - regression of pre-2026-09-26 behavior\n";
$bareProbe = \bbsengine6\util\safe_path_web(
    ['comp/lang/python/variables'],
    ['base_dir' => $fixtureRoot]
);
// safe_path_web returns a normalized path on success even when the
// file does not exist on disk (it does the "allow non-existent
// final target" branch). The handler's file_exists() check is
// what distinguishes a hit from a miss. So:
$bareExistsOnDisk = is_string($bareProbe) && file_exists($bareProbe);
$mdExistsOnDisk = is_string($resolved) && file_exists($resolved);
if ($bareExistsOnDisk === false && $mdExistsOnDisk === true) {
    test_pass("bare probe misses; .md probe hits (proves .md is load-bearing)");
} else {
    test_fail(
        "bare/.md resolution inverted",
        "bareExists=" . var_export($bareExistsOnDisk, true)
        . " mdExists=" . var_export($mdExistsOnDisk, true)
    );
}

// --- Test 3: containment check rejects escapes (path-traversal guard) -----

echo "Test 3: '.md' probe still rejects '../etc/passwd.md' (path-traversal guard)\n";
$escape = \bbsengine6\util\safe_path_web(
    ['../../../etc/passwd.md'],
    ['base_dir' => $fixtureRoot]
);
// safe_path_web normalizes '..' components; the resolved path
// should either be false or stay under base_dir. We assert it
// does not equal an unrelated '/etc/passwd' path.
if ($escape === false
    || (is_string($escape)
        && !str_contains($escape, '/etc/passwd')
        && (strpos($escape, realpath($fixtureRoot)) === 0 || !is_dir(dirname($escape))))) {
    test_pass("'.md' probe escape attempt is neutralized");
} else {
    test_fail(
        ".md probe did not guard path-traversal",
        "got " . var_export($escape, true)
    );
}

// --- Test 4: trailing-slash slug edge case -------------------------------

echo "Test 4: trailing slash in input slug is handled safely\n";
$trail = \bbsengine6\util\safe_path_web(
    ['/comp/lang/python/variables.md/'],
    ['base_dir' => $fixtureRoot]
);
// safe_path_web splits on '/' and rejects empties; if everything
// collapses to nothing (because the trailing / clobbers the last
// token after the basename), it returns false. Either is a safe
// outcome - the handler would then return ROUTER_NEXT and the
// request would 404, not 500.
if ($trail === false
    || (is_string($trail) && $trail === realpath($markdownPath))) {
    test_pass("trailing-slash slug handled without leaking escape");
} else {
    test_fail(
        "trailing-slash slug produced unsafe path",
        "got " . var_export($trail, true)
    );
}

// --- cleanup --------------------------------------------------------------

$rii = new \RecursiveIteratorIterator(
    new \RecursiveDirectoryIterator(
        $fixtureRoot,
        \FilesystemIterator::SKIP_DOTS
    ),
    \RecursiveIteratorIterator::CHILD_FIRST
);
foreach ($rii as $f) {
    @rmdir($f->getPathname()) or @unlink($f->getPathname());
}
@rmdir($fixtureRoot);

echo "\n=== All tests passed! ===\n";
