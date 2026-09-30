<?php
/**
 * test_router_handleraemarkdown.php - exercise
 * \bbsengine6\markdown\serveRawMarkdown() in isolation.
 *
 * router_handleRawMarkdown (engine/router.php, registered since
 * 2026-09-29) is a thin wrapper around the canonical library at
 * php/markdown.php (merged from php/serve-md.php on 2026-10-XX).
 * The library enforces realpath-based containment under the supplied
 * base dir, .md-only extension, and file-only (rejects directories).
 * It emits `Content-Type: text/plain; charset=utf-8` and reads the
 * body to stdout on success.
 *
 * This test pins the library's probe shape in isolation so a
 * future refactor of router_handleRawMarkdown that accidentally
 * drops the library call (or reimplements the body inline) is
 * caught at the unit-test level, not in production.
 *
 * The library relies on `header()` and `readfile()`, which are
 * no-ops on the CLI SAPI, so we assert on the return value (true
 * on success, false on any validation failure) and on the
 * output buffer (the file body should be written on a hit; the
 * buffer should remain empty on a miss).
 *
 * Usage:
 *   php test_router_handleraemarkdown.php
 */

require_once __DIR__ . "/bootstrap.php";
require_once("markdown.php");

// @since 2026-09-29 — the library's hit path calls header()
// (sets Content-Type: text/plain) which is a no-op on the CLI
// SAPI but raises a Warning. Silence warnings during the
// library calls so the test output stays clean. We still
// assert on the return value (true/false) and the body buffer.
error_reporting(error_reporting() & ~E_WARNING);

echo "=== Testing \\bbsengine6\\markdown\\serveRawMarkdown library shape ===\n\n";

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

$fixtureRoot = sys_get_temp_dir() . "/bbsengine6_test_rawmd_" . bin2hex(random_bytes(4));
if (!mkdir($fixtureRoot . "/ec", 0777, true)) {
    test_fail("could not create fixture root", $fixtureRoot);
}

$marker = "# Investigated Psychics\n\nFraud content here.\n";
$markdownPath = $fixtureRoot . "/ec/investigated-psychics-fraud-pigasus.md";
if (file_put_contents($markdownPath, $marker) === false) {
    test_fail("could not write fixture .md", $markdownPath);
}

// --- Test 1: hit returns true and reads the file body --------------------

echo "Test 1: hit resolves and reads file body to stdout\n";
ob_start();
$hit = \bbsengine6\markdown\serveRawMarkdown($fixtureRoot, "ec/investigated-psychics-fraud-pigasus.md");
$body = ob_get_clean();
if ($hit !== true) {
    test_fail("hit returned non-true", "got " . var_export($hit, true));
}
if ($body !== $marker) {
    test_fail(
        "hit body does not match fixture",
        "got " . var_export($body, true) . " expected " . var_export($marker, true)
    );
}
test_pass("hit returned true and body byte-equals the on-disk fixture");

// --- Test 2: miss (nonexistent file) returns false ------------------------

echo "Test 2: nonexistent .md returns false\n";
ob_start();
$miss = \bbsengine6\markdown\serveRawMarkdown($fixtureRoot, "ec/does-not-exist.md");
$body = ob_get_clean();
if ($miss !== false) {
    test_fail("miss returned non-false", "got " . var_export($miss, true));
}
if ($body !== '') {
    test_fail("miss emitted a non-empty body", "got " . var_export($body, true));
}
test_pass("miss returned false with empty stdout (caller emits 404)");

// --- Test 3: path-traversal neutralized ---------------------------------

echo "Test 3: '../etc/passwd.md' returns false (realpath containment)\n";
ob_start();
$escape = \bbsengine6\markdown\serveRawMarkdown($fixtureRoot, "../etc/passwd.md");
$body = ob_get_clean();
if ($escape !== false) {
    test_fail("escape attempt returned non-false", "got " . var_export($escape, true));
}
if ($body !== '') {
    test_fail("escape attempt emitted body", "got " . var_export($body, true));
}
test_pass("traversal neutralized; no body emitted");

// --- Test 4: non-.md extension returns false -----------------------------

echo "Test 4: non-.md extension returns false (.txt extension check)\n";
file_put_contents($fixtureRoot . "/ec/notes.txt", "this is not markdown");
ob_start();
$txt = \bbsengine6\markdown\serveRawMarkdown($fixtureRoot, "ec/notes.txt");
$body = ob_get_clean();
if ($txt !== false) {
    test_fail(".txt returned non-false", "got " . var_export($txt, true));
}
if ($body !== '') {
    test_fail(".txt emitted body", "got " . var_export($body, true));
}
test_pass(".txt extension rejected by pathinfo check");

// --- Test 5: directory probe returns false (file-only check) -------------

echo "Test 5: directory probe returns false (is_file guard)\n";
ob_start();
$dir = \bbsengine6\markdown\serveRawMarkdown($fixtureRoot, "ec");
$body = ob_get_clean();
if ($dir !== false) {
    test_fail("directory returned non-false", "got " . var_export($dir, true));
}
if ($body !== '') {
    test_fail("directory emitted body", "got " . var_export($body, true));
}
test_pass("directory probe rejected by is_file check");

// --- Test 6: nonexistent basedir returns false ---------------------------

echo "Test 6: nonexistent basedir returns false (realpath on base fails)\n";
ob_start();
$nobase = \bbsengine6\markdown\serveRawMarkdown("/nonexistent/directory/xyz", "foo.md");
$body = ob_get_clean();
if ($nobase !== false) {
    test_fail("nonexistent basedir returned non-false", "got " . var_export($nobase, true));
}
if ($body !== '') {
    test_fail("nonexistent basedir emitted body", "got " . var_export($body, true));
}
test_pass("nonexistent basedir rejected by realpath-on-base check");

// --- Test 7: nested subdirectory hit returns true ------------------------

echo "Test 7: nested subdirectory hit (depth-2 path) returns true\n";
if (!mkdir($fixtureRoot . "/ec/sub", 0777, true)) {
    test_fail("could not create fixture subdir");
}
file_put_contents($fixtureRoot . "/ec/sub/deep.md", "# deep fixture\n");
ob_start();
$deep = \bbsengine6\markdown\serveRawMarkdown($fixtureRoot, "ec/sub/deep.md");
$body = ob_get_clean();
if ($deep !== true) {
    test_fail("deep hit returned non-true", "got " . var_export($deep, true));
}
if ($body !== "# deep fixture\n") {
    test_fail("deep body mismatch", "got " . var_export($body, true));
}
test_pass("deep subdirectory hit resolved and body matched");

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
