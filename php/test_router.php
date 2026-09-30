<?php
/**
 * test_router.php - Tests for router handler registry
 * 
 * Usage:
 *   php test_router.php           # Run mock tests
 *   php test_router.php --db       # Run database integration tests
 */

require_once __DIR__ . "/bootstrap.php";
require_once("engine/router.php");

$run_db = in_array("--db", $argv);

echo "=== Testing router functions ===\n\n";

// =============================================================================
// MOCK TESTS (no database)
// =============================================================================

echo "--- Mock Tests ---\n\n";

// Test 1: ROUTER_NEXT constant exists
echo "Test 1: ROUTER_NEXT constant defined\n";
if (defined("ROUTER_NEXT") && ROUTER_NEXT === "ROUTER_NEXT") {
    echo "  ✓ PASS: ROUTER_NEXT = 'ROUTER_NEXT'\n";
} else {
    echo "  ✗ FAIL: ROUTER_NEXT not properly defined\n";
    exit(1);
}

// Test 2: ROUTER_RENDERED constant exists
echo "Test 2: ROUTER_RENDERED constant defined (replaces the implicit empty-string-as-success contract)\n";
if (defined("ROUTER_RENDERED") && ROUTER_RENDERED === "ROUTER_RENDERED") {
    echo "  ✓ PASS: ROUTER_RENDERED = 'ROUTER_RENDERED'\n";
} else {
    echo "  ✗ FAIL: ROUTER_RENDERED not properly defined\n";
    exit(1);
}

// Test 3: Handler order is correct
echo "Test 3: Handler order (index → blurb → folder → markdown → page → rawmarkdown)\n";
// @since 2026-09-29 — rawmarkdown appended at the end of the registry.
// Its pattern (\.md$) is non-overlapping with the other handlers (the
// 'markdown' handler's pattern no longer admits '.'), so position is
// cosmetic, but placing it last keeps the chrome-rendering handlers
// grouped together at the front of the chain.
$expectedOrder = ['index', 'blurb', 'folder', 'markdown', 'page', 'rawmarkdown'];
$handlers = router_gethandlers();
$actualOrder = array_keys($handlers);
if ($actualOrder === $expectedOrder) {
    echo "  ✓ PASS: Handler order is correct\n";
} else {
    echo "  ✗ FAIL: Handler order incorrect, got: " . implode(", ", $actualOrder) . "\n";
    exit(1);
}

// Test 3a: Each entry resolves to a callable FQCN. Legacy entries
// may be a bare FQCN string; new entries are arrays with a 'fn'
// key (and optional 'pattern'). Regression guard for the 2026-09-15
// namespace refactor (commit bfaca68), which left bare-name
// strings in router_gethandlers() and broke the dispatch loop on
// every HTTP request.
echo "Test 3a: Each handler entry resolves to an FQCN (regression guard for variable-function dispatch)\n";
$fqcn_ok = true;
foreach ($handlers as $name => $entry) {
    $fqcn = is_array($entry) ? ($entry['fn'] ?? null) : $entry;
    if (!is_string($fqcn) || strpos($fqcn, 'bbsengine6\\') !== 0) {
        echo "  ✗ FAIL: handler '$name' is not FQCN: " . var_export($entry, true) . "\n";
        $fqcn_ok = false;
    }
}
if (!$fqcn_ok) {
    exit(1);
}
echo "  ✓ PASS: all " . count($handlers) . " handlers have a callable FQCN\n";

// Test 3b: `error` is intentionally not in the registry (the
// dispatch loop falls through to router_handleError($uri) when no
// handler matches, so registering it would fire it twice on a
// miss). 2026-09-19.
echo "Test 3b: 'error' is not in the handler registry\n";
if (array_key_exists('error', $handlers)) {
    echo "  ✗ FAIL: 'error' key found in registry; dispatch loop would double-fire\n";
    exit(1);
}
echo "  ✓ PASS: 'error' not in registry (single source of truth via post-loop fallback)\n";

// Test 3c: Every non-null `pattern` is a valid PCRE regex.
echo "Test 3c: Handler patterns are valid PCRE\n";
$bad_patterns = [];
foreach ($handlers as $name => $entry) {
    if (!is_array($entry)) continue;
    $p = $entry['pattern'] ?? null;
    if ($p === null) continue;
    if (@preg_match($p, '') === false) {
        $bad_patterns[] = "$name: $p";
    }
}
if (!empty($bad_patterns)) {
    echo "  ✗ FAIL: invalid patterns: " . implode('; ', $bad_patterns) . "\n";
    exit(1);
}
echo "  ✓ PASS: all non-null patterns compile cleanly\n";

// Test 3d: Pattern skip behavior. Stub each handler to record
// whether it was invoked; dispatch a URI that should match only
// one handler; assert only that handler was called.
echo "Test 3d: Dispatch loop skips handlers whose pattern doesn't match\n";
$GLOBALS['__invoked'] = [];
$orig_handlers = $handlers;
$stub_handlers = [];
foreach ($orig_handlers as $name => $entry) {
    $stub_handlers[$name] = [
        'fn' => function (string $uri) use ($name) {
            $GLOBALS['__invoked'][$name] = ($GLOBALS['__invoked'][$name] ?? 0) + 1;
            return \bbsengine6\router\ROUTER_NEXT;
        },
        'pattern' => is_array($entry) ? ($entry['pattern'] ?? null) : null,
    ];
}

// Swap the registry by overriding router_gethandlers via a
// runkit-less trick: the dispatch loop calls router_gethandlers()
// every iteration, so we can't easily monkey-patch it from here
// without runkit. Instead, test the pattern logic directly: pick
// the `page` handler (narrowest pattern), then assert its pattern
// rejects a URI that should go to markdown/blurb/folder.
$page_entry = $handlers['page'];
$page_pattern = is_array($page_entry) ? $page_entry['pattern'] : null;
if ($page_pattern === null) {
    echo "  ✗ FAIL: page handler has no pattern\n";
    exit(1);
}
$should_match = (bool) preg_match($page_pattern, 'contact-us');
$should_miss  = (bool) preg_match($page_pattern, 'rec/arts/star-trek');
if (!$should_match) {
    echo "  ✗ FAIL: page pattern should match 'contact-us'\n";
    exit(1);
}
if ($should_miss) {
    echo "  ✗ FAIL: page pattern should NOT match 'rec/arts/star-trek'\n";
    exit(1);
}
echo "  ✓ PASS: page pattern matches 'contact-us', rejects 'rec/arts/star-trek'\n";

// Test 3e: Dispatch smoke test. Actually invokes router() so the
// variable-function call inside the dispatch loop is exercised.
// Catches the 2026-09-16 regression where router_gethandlers()
// returned bare-name strings; bare names broke because PHP
// variable-function lookup goes to the global namespace, not
// the call-site namespace, so every request threw
// `Call to undefined function router_handleIndex()`.
//
// FQCN call: test_router.php runs in the global namespace, so
// an unqualified `router()` would itself be a lookup miss.
//
// Post-C1: 'error' is no longer in the registry, so on a miss
// the dispatch loop falls through to router_handleError($uri).
// The new contract (ROUTER_RENDERED) routes through page\error()
// → displaypage(), which prints to stdout. The dispatch loop
// returns ''. We accept either:
//   - empty-string return with page\error chrome on stdout, OR
//   - non-empty-string return with "Page Not Found" body (legacy
//     shape, if displaypage throws).
echo "Test 3e: router() dispatches through full handler chain without 'undefined function' errors\n";
ob_start();
$dispatch_result = \bbsengine6\router\router("nonexistent/xyz123");
$dispatch_body = ob_get_clean();
$ok = false;
if ($dispatch_result === '' && $dispatch_body !== '') {
    $ok = true; // ROUTER_RENDERED path: chrome on stdout, return ''
} elseif (is_string($dispatch_result)
          && strlen($dispatch_result) > 0
          && strpos($dispatch_result, "Page Not Found") !== false) {
    $ok = true; // legacy inline body path
}
if ($ok) {
    echo "  ✓ PASS: router() dispatch complete (result=" . var_export($dispatch_result, true)
         . ", body length=" . strlen($dispatch_body) . ")\n";
} else {
    echo "  ✗ FAIL: router() did not produce an error path: "
         . "result=" . var_export($dispatch_result, true)
         . ", body length=" . strlen($dispatch_body) . "\n";
    exit(1);
}

// Test 4: URI to blurbID conversion
echo "Test 4: URI to blurbID conversion (used by blurb handler)\n";
$uri = "ec/john-edward";
$expected = "ec.john-edward";
$actual = str_replace("/", ".", preg_replace('/\.md$/', '', $uri));
if ($actual === $expected) {
    echo "  ✓ PASS: ec/john-edward → ec.john-edward\n";
} else {
    echo "  ✗ FAIL: expected '$expected', got '$actual'\n";
    exit(1);
}

// Test 5: YAML frontmatter parsing
echo "Test 5: YAML frontmatter parsing\n";
$md = "---\ntitle: Test Page\ndate: 2024-01-01\n---\n\nbody here\n";
require_once("markdown.php");
[$metadata, $body] = \bbsengine6\markdown\splitFrontmatter($md);
if ($metadata['title'] === 'Test Page' && $metadata['date'] === '2024-01-01' && $body === "body here\n") {
    echo "  ✓ PASS: YAML frontmatter parsed correctly\n";
} else {
    echo "  ✗ FAIL: YAML parsing failed\n";
    exit(1);
}

// Test 6: Filepath construction for teos
echo "Test 6: Filepath construction\n";
$teospath = '/srv/www/vhosts/zoidtechnologies.com/html/teos/';
$uri = 'ec/john-edward';
$filepath = $teospath . $uri . ".md";
if ($filepath === '/srv/www/vhosts/zoidtechnologies.com/html/teos/ec/john-edward.md') {
    echo "  ✓ PASS: filepath constructed correctly\n";
} else {
    echo "  ✗ FAIL: filepath incorrect: $filepath\n";
    exit(1);
}

// Test 6a: router_handleMarkdown source pre-strips ".md" before
// the filesystem probe. Pre-2026-09-29 the HTTP entry-point
// stripped a trailing ".md" from the URI, so the markdown
// handler's filesystem probe of "<reluri>.md" was a clean
// <slug>.md match. After 2026-09-29 the entry-point no longer
// strips, so the handler must defensively preg_replace('/\.md$/',
// '', $reluri) before the probe to avoid double-appending to
// "<slug>.md.md". Pins the defensive-strip-then-append shape.
echo "Test 6a: router_handleMarkdown defensively strips '.md' before filesystem probe (post 2026-09-29 entry-point-strip removal)\n";
$router_src = file_get_contents(__DIR__ . "/../engine/router.php");
if (preg_match('/function\s+router_handleMarkdown\s*\([^)]*\)\s*\{(.*?)^\}/sm', $router_src, $m)) {
    $handler_body = $m[1];
    // Required shape: preg_replace('/\.md$/', '', $reluri) appears
    // BEFORE the safe_path_web(... '.md') call. The literal probe
    // alone (without the strip) would double-append when called
    // with a dot-bearing URI.
    $strip_pos = strpos($handler_body, "preg_replace('/\\\\.md\\$/', '', ");
    $probe_pos = strpos($handler_body, "router_safe_path_web([");
    if ($strip_pos === false) {
        echo "  ✗ FAIL: router_handleMarkdown missing the defensive preg_replace('/\\\\.md\\$/', '', ...) strip; " .
             "a future regression that delivers a '.md'-suffixed URI here would double-append and miss.\n";
        exit(1);
    }
    if ($probe_pos === false || $strip_pos > $probe_pos) {
        echo "  ✗ FAIL: defensive .md strip must appear BEFORE the filesystem probe; " .
             "found strip at $strip_pos, probe at $probe_pos.\n";
        exit(1);
    }
    echo "  ✓ PASS: router_handleMarkdown defensively preg_replace()s '.md' before safe_path_web() probe\n";
} else {
    echo "  ✗ FAIL: could not extract router_handleMarkdown body\n";
    exit(1);
}

// Test 6b: HTTP entry-point no longer strips a trailing ".md"
// from the URI before passing it to router(). The strip was
// removed on 2026-09-29 to enable raw text/plain dispatch on
// /<uri>.md URLs (see router_handleRawMarkdown in
// engine/router.php and the file-header docblock). Handlers
// that don't care about extensions now pattern-gate or strip
// them themselves.
echo "Test 6b: HTTP entry-point does NOT strip trailing .md from URI\n";
if (preg_match('/preg_replace\s*\(\s*[\'"]\/\\\\\.md\\\$\/[\'"]/', $router_src)) {
    echo "  ✗ FAIL: HTTP entry-point still strips .md; raw markdown handler will not fire.\n";
    exit(1);
}
echo "  ✓ PASS: HTTP entry-point preserves .md suffix in URI\n";

// Test 6c: isBlurb() reads TEOSDIR via \bbsengine6\util\env(),
// not via the legacy `defined('TEOSDIR') ? TEOSDIR : <hardcoded
// fallback>` pattern. Regression guard for the 2026-09-28
// blurb.php canonicalization (commit 03b665d).
//
// Pre-fix, isBlurb() read TEOSDIR via the constant-with-fallback
// pattern, so a getenv()-only override (a vhost whose htaccess
// set TEOSDIR via SetEnv but whose zoid6config.php wasn't loaded)
// was silently ignored and the helper probed the hardcoded prod
// path. Post-fix, the helper calls \bbsengine6\util\env() which
// honors getenv() first, then the constant, then the empty
// default — matching router_handleFolder / router_handleMarkdown.
//
// Source-level assertion (vs runtime): the test environment can't
// load engine.php's PEAR/Smarty/QuickForm2 deps without a full
// prod-like setup, so we assert against the source code instead.
// Test 6a/6b use the same source-reading technique. A future
// runtime test can replace this once the test env is sorted.
echo "Test 6c: isBlurb() reads TEOSDIR via \\\\bbsengine6\\\\util\\\\env() (not via the legacy constant-with-hardcoded-fallback pattern)\n";
$blurb_src = file_get_contents(__DIR__ . "/blurb.php");
if (preg_match('/function\s+isBlurb\s*\([^)]*\)\s*\{(.*?)^\}/sm', $blurb_src, $m)) {
    $body = $m[1];
    if (!preg_match('/\\\\bbsengine6\\\\util\\\\env\s*\(\s*[\'"]TEOSDIR[\'"]\s*\)/', $body)) {
        echo "  ✗ FAIL: isBlurb() does not call \\\\bbsengine6\\\\util\\\\env('TEOSDIR'); " .
             "the constant-with-fallback pattern would silently miss vhost-level SetEnv overrides.\n";
        exit(1);
    }
    if (preg_match('/defined\s*\(\s*[\'"]TEOSDIR[\'"]\s*\)/', $body)) {
        echo "  ✗ FAIL: isBlurb() still uses the legacy `defined('TEOSDIR')` pattern; " .
             "route through env() instead.\n";
        exit(1);
    }
    // The hardcoded prod-path fallback is the foot-gun we're guarding
    // against. It used to be: '/srv/www/vhosts/zoidtechnologies.com/html/teos/'
    // If it ever sneaks back in, this assertion catches it.
    if (preg_match('#/srv/www/vhosts/zoidtechnologies\.com/html/teos/#', $body)) {
        echo "  ✗ FAIL: isBlurb() still hardcodes the prod teos path; " .
             "use \\\\bbsengine6\\\\util\\\\env() with an empty default instead.\n";
        exit(1);
    }
    echo "  ✓ PASS: isBlurb() routes TEOSDIR through env() with no constant-with-fallback pattern\n";
} else {
    echo "  ✗ FAIL: could not extract isBlurb() body\n";
    exit(1);
}

// Test 6d: display() (the blurb renderer) reads TEOSDIR the same
// way isBlurb() does. Symmetry guard: if either function drifts
// back to the legacy pattern, the other still works but the
// mismatch is a foot-gun for future callers.
echo "Test 6d: display() reads TEOSDIR via \\\\bbsengine6\\\\util\\\\env() (symmetric with isBlurb)\n";
if (preg_match('/function\s+display\s*\([^)]*\)\s*\{(.*?)^\}/sm', $blurb_src, $m)) {
    $body = $m[1];
    if (!preg_match('/\\\\bbsengine6\\\\util\\\\env\s*\(\s*[\'"]TEOSDIR[\'"]\s*\)/', $body)) {
        echo "  ✗ FAIL: display() does not call \\\\bbsengine6\\\\util\\\\env('TEOSDIR'); " .
             "the renderer would silently miss vhost-level SetEnv overrides.\n";
        exit(1);
    }
    if (preg_match('/defined\s*\(\s*[\'"]TEOSDIR[\'"]\s*\)/', $body)) {
        echo "  ✗ FAIL: display() still uses the legacy `defined('TEOSDIR')` pattern.\n";
        exit(1);
    }
    if (preg_match('#/srv/www/vhosts/zoidtechnologies\.com/html/teos/#', $body)) {
        echo "  ✗ FAIL: display() still hardcodes the prod teos path.\n";
        exit(1);
    }
    echo "  ✓ PASS: display() routes TEOSDIR through env() with no constant-with-fallback pattern\n";
} else {
    echo "  ✗ FAIL: could not extract display() body\n";
    exit(1);
}

// Test 6e: \bbsengine6\util\env() precedence. Asserts the helper
// returns getenv() first, then the constant, then the default.
// This is the contract every handler now relies on; pinning it
// here so a future refactor of util.php can't silently break
// the rest of the chain.
//
// We can't extract the env() function body with a simple regex
// because the body contains nested braces that defeat lazy
// matching. Instead, extract the body via brace counting (the
// same shape util.php uses internally to find function ranges
// for docblock cleanup, etc.). Then assert getenv() comes
// before defined() in that body.
echo "Test 6e: \\\\bbsengine6\\\\util\\\\env() precedence is getenv() > constant > default\n";
$env_helper_src = file_get_contents(__DIR__ . "/util.php");
$fn_pos = strpos($env_helper_src, "function env(string");
if ($fn_pos === false) {
    echo "  ✗ FAIL: could not find function env() in util.php\n";
    exit(1);
}
$open = strpos($env_helper_src, "{", $fn_pos);
if ($open === false) {
    echo "  ✗ FAIL: could not find opening brace of env() in util.php\n";
    exit(1);
}
// Brace-counted extraction: walk forward from the opening
// brace, decrementing depth on `}` and incrementing on `{`,
// stopping when depth hits 0. Skips `}` and `{` inside strings
// by using a simple character-class match — adequate for
// util.php's code style (no embedded `}` or `{` in string
// literals inside env()).
$depth = 1;
$i = $open + 1;
while ($i < strlen($env_helper_src) && $depth > 0) {
    $c = $env_helper_src[$i];
    if ($c === "{") $depth++;
    elseif ($c === "}") $depth--;
    $i++;
}
if ($depth !== 0) {
    echo "  ✗ FAIL: brace counting did not balance inside env() body\n";
    exit(1);
}
$env_body = substr($env_helper_src, $open + 1, $i - $open - 2);

$getenv_pos = strpos($env_body, "getenv(\$key)");
$defined_pos = strpos($env_body, "defined(\$key)");
if ($getenv_pos === false) {
    echo "  ✗ FAIL: env() does not call getenv(\$key); the vhost htaccess SetEnv contract would not be honored.\n";
    exit(1);
}
if ($defined_pos === false) {
    echo "  ✗ FAIL: env() does not fall back to defined(\$key); tests / partial-deploys would have no TEOSDIR.\n";
    exit(1);
}
if ($getenv_pos > $defined_pos) {
    echo "  ✗ FAIL: env() reads the constant before getenv(); the vhost htaccess SetEnv contract would not be honored.\n";
    exit(1);
}
echo "  ✓ PASS: env() reads getenv() before defined() (env wins, then constant, then default)\n";

// Test 6f: 'markdown' handler's pattern no longer admits '.md' (or
// any '.') in the URI. The entry-point strip was removed on
// 2026-09-29 to enable raw .md dispatch via router_handleRawMarkdown,
// so the markdown handler's pattern must naturally reject dot-bearing
// URIs at the registry level (otherwise they'd be coerced through the
// chrome-rendered branch instead of the raw branch). Pins both:
//   - a dot-bearing URI like 'ec/foo.md' is rejected by the
//     pattern (preg_match returns 0); and
//   - a bare URI like 'ec/foo' is still accepted (preg_match returns 1).
echo "Test 6f: 'markdown' handler pattern excludes dot-bearing URIs (post 2026-09-29 .md-strip removal)\n";
$md_entry = $handlers['markdown'];
$md_pattern = is_array($md_entry) ? ($md_entry['pattern'] ?? null) : null;
if ($md_pattern === null) {
    echo "  ✗ FAIL: markdown handler has no pattern\n";
    exit(1);
}
if (@preg_match($md_pattern, 'ec/foo.md') === 1) {
    echo "  ✗ FAIL: markdown pattern matched 'ec/foo.md'; .md URIs would be chrome-rendered instead of dispatched to router_handleRawMarkdown\n";
    exit(1);
}
if (@preg_match($md_pattern, 'ec/foo') !== 1) {
    echo "  ✗ FAIL: markdown pattern did NOT match bare 'ec/foo'; chrome-rendered dispatch is broken\n";
    exit(1);
}
echo "  ✓ PASS: markdown pattern rejects dot-bearing URIs and accepts bare URIs\n";

// Test 6g: 'rawmarkdown' handler is registered with a pattern that
// matches '.md$' URIs and nothing else. Pins the registry shape so
// a future refactor that renames the handler or changes the pattern
// can't silently break the raw text/plain dispatch contract.
echo "Test 6g: 'rawmarkdown' handler is registered with pattern matching '.md$' URIs\n";
if (!array_key_exists('rawmarkdown', $handlers)) {
    echo "  ✗ FAIL: 'rawmarkdown' handler not in registry; /<uri>.md URLs will fall through to the styled 404\n";
    exit(1);
}
$rm_entry = $handlers['rawmarkdown'];
$rm_pattern = is_array($rm_entry) ? ($rm_entry['pattern'] ?? null) : null;
if ($rm_pattern === null) {
    echo "  ✗ FAIL: rawmarkdown handler has no pattern\n";
    exit(1);
}
if (@preg_match($rm_pattern, 'ec/foo.md') !== 1) {
    echo "  ✗ FAIL: rawmarkdown pattern did NOT match 'ec/foo.md'\n";
    exit(1);
}
if (@preg_match($rm_pattern, 'ec/foo') === 1) {
    echo "  ✗ FAIL: rawmarkdown pattern matched bare 'ec/foo'; bare URIs would be dispatched as raw text/plain\n";
    exit(1);
}
// Also assert the handler's FQCN is callable (regression guard for
// the variable-function dispatch loop).
$rm_fqcn = is_array($rm_entry) ? ($rm_entry['fn'] ?? null) : $rm_entry;
if (!is_string($rm_fqcn) || !function_exists($rm_fqcn)) {
    echo "  ✗ FAIL: rawmarkdown handler FQCN not callable: " . var_export($rm_fqcn, true) . "\n";
    exit(1);
}
echo "  ✓ PASS: rawmarkdown handler registered with .md$ pattern and callable FQCN\n";

// Test 6h: router_handleRawMarkdown reads TEOSDIR via env() (not the
// legacy constant-with-hardcoded-fallback pattern) and delegates to
// bbsengine6\markdown\serveRawMarkdown(). Source-level assertion: same
// shape as Test 6c/6d/6e.
echo "Test 6h: router_handleRawMarkdown reads TEOSDIR via env() and uses serveRawMarkdown()\n";
$rm_body = '';
if (preg_match('/function\s+router_handleRawMarkdown\s*\([^)]*\)\s*\{(.*?)^\}/sm', $router_src, $m)) {
    $rm_body = $m[1];
}
if ($rm_body === '') {
    echo "  ✗ FAIL: could not extract router_handleRawMarkdown body\n";
    exit(1);
}
if (strpos($rm_body, 'env("TEOSDIR")') === false) {
    echo "  ✗ FAIL: router_handleRawMarkdown does not call env(\"TEOSDIR\"); " .
         "the vhost htaccess SetEnv contract would not be honored.\n";
    exit(1);
}
if (strpos($rm_body, 'serveRawMarkdown(') === false) {
    echo "  ✗ FAIL: router_handleRawMarkdown does not call bbsengine6\\markdown\\serveRawMarkdown(); " .
         "the canonical library would not be reused.\n";
    exit(1);
}
if (strpos($rm_body, 'ROUTER_RENDERED') === false) {
    echo "  ✗ FAIL: router_handleRawMarkdown never returns ROUTER_RENDERED; " .
         "the HTTP entry-point would double-emit (echo '' on top of the body).\n";
    exit(1);
}
echo "  ✓ PASS: router_handleRawMarkdown uses env(\"TEOSDIR\") + serveRawMarkdown() + ROUTER_RENDERED\n";

// Test 6i: end-to-end router() dispatch for /<uri>.md returns
// text/plain raw markdown. This is the test that would have caught
// the 2026-09-29 incident on zoidtechnologies.com/teos/ec/<slug>.md
// returning text/html chrome instead of text/plain raw. The earlier
// tests (6f/6g/6h) only pin the registry shape and source-level
// function bodies; they don't exercise the full dispatch path. Test 6i
// creates a temp fixture tree, sets TEOSDIR via putenv(), invokes
// \bbsengine6\router\router() on a .md URI, and asserts three things:
//   1. return value === '' (ROUTER_RENDERED sentinel, see router()
//      line 782),
//   2. body byte-equals the on-disk marker (proves raw markdown
//      was streamed, not chrome HTML),
//   3. headers_list() contains 'Content-Type: text/plain' (proves
//      \bbsengine6\markdown\serveRawMarkdown() emitted the header —
//      i.e. the function is actually defined and reachable). This is
//      the assertion that catches the missing require_once('markdown.php')
//      regression: without it, the handler throws "undefined
//      function" and the test fails at step 1.
echo "Test 6i: end-to-end router() dispatch for /<uri>.md returns text/plain raw markdown\n";

$fixtureRoot = sys_get_temp_dir() . "/bbsengine6_test_router_md_" . bin2hex(random_bytes(4));
if (!mkdir($fixtureRoot . "/ec", 0777, true)) {
    echo "  ✗ FAIL: could not create fixture root\n";
    exit(1);
}
$marker = "# Investigated Psychics\n\nFraud content here.\n";
$mdPath = $fixtureRoot . "/ec/investigated-psychics-fraud-pigasus.md";
if (file_put_contents($mdPath, $marker) === false) {
    echo "  ✗ FAIL: could not write fixture .md\n";
    exit(1);
}

// Silence CLI E_WARNING on header() calls — the library emits a
// header that's buffered into headers_list() but raises a Warning
// under CLI SAPI. Same convention as test_router_handleraemarkdown.php:36.
error_reporting(error_reporting() & ~E_WARNING);

putenv("TEOSDIR=$fixtureRoot");

try {
    ob_start();
    $result = \bbsengine6\router\router("ec/investigated-psychics-fraud-pigasus.md");
    $body = ob_get_clean();

    // Capture headers_list() after router() returns, before any
    // output that would trigger headers_sent(). On CLI SAPI the
    // header() call still registers into the internal header list
    // (just with an E_WARNING we silenced); headers_list() returns
    // the buffered list regardless of SAPI.
    $headers = headers_list();
    $contentType = '';
    foreach ($headers as $h) {
        if (stripos($h, 'Content-Type:') === 0) {
            $contentType = trim(substr($h, strlen('Content-Type:')));
            break;
        }
    }

    // Assert 1: router() return === '' means the dispatch loop saw
    // ROUTER_RENDERED and short-circuited (router.php:782). A
    // chrome-rendered return would also be '', but only the body
    // assertion below distinguishes the two.
    if ($result !== '') {
        echo "  ✗ FAIL: router() did not return ROUTER_RENDERED (got: "
             . var_export($result, true) . ")\n";
        exit(1);
    }

    // Assert 2: body byte-equals marker. Chrome-rendered output
    // would be ~10KB+ of HTML; this catches the dispatch-order
    // regression where markdown's handler consumes .md URIs.
    if ($body !== $marker) {
        echo "  ✗ FAIL: body did not match fixture marker (got "
             . strlen($body) . " bytes; expected " . strlen($marker) . ")\n";
        exit(1);
    }

    // Assert 3: Content-Type was emitted as text/plain. This is the
    // assertion that catches the missing require_once('markdown.php')
    // bug: without the require_once, \bbsengine6\markdown\serveRawMarkdown()
    // is undefined, the handler throws, and headers_list() won't
    // contain the text/plain header.
    if (stripos($contentType, 'text/plain') === false) {
        echo "  ✗ FAIL: Content-Type was not text/plain (got: "
             . var_export($contentType, true) . ")\n";
        exit(1);
    }

    echo "  ✓ PASS: router() returned ROUTER_RENDERED, body matched fixture, "
         . "Content-Type=text/plain\n";
} finally {
    // Cleanup regardless of pass/fail
    putenv("TEOSDIR");
    @unlink($mdPath);
    @rmdir($fixtureRoot . "/ec");
    @rmdir($fixtureRoot);
}

echo "\n";

// =============================================================================
// DATABASE INTEGRATION TESTS
// =============================================================================

if ($run_db) {
    echo "--- Database Integration Tests ---\n\n";
    
    define("SYSTEMDSN", "pgsql:host=127.0.0.1;port=5432;dbname=zoid6test");
    
    require_once("/home/opencode/data/work/bbsengine6/php/database.php");
    require_once("/home/opencode/data/work/bbsengine6/php/blurb.php");
    
    // Test 1: Blurb handler detects existing blurb (mock - just check isBlurb is called correctly)
    echo "Test 7: isBlurb returns true for existing blurb\n";
    $result = \bbsengine6\blurb\isBlurb("ec.biblical-prophets-mediumship-prophecy");
    if ($result === true) {
        echo "  ✓ PASS: isBlurb('ec.biblical-prophets-mediumship-prophecy') = true\n";
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        exit(1);
    }
    
    // Test 2: Blurb handler returns ROUTER_NEXT for non-existent blurb
    echo "Test 8: isBlurb returns false for non-existent\n";
    $result = \bbsengine6\blurb\isBlurb("nonexistent/page");
    if ($result === false) {
        echo "  ✓ PASS: isBlurb returns false for non-existent\n";
    } else {
        echo "  ✗ FAIL: expected false\n";
        exit(1);
    }
    
    // Test 3: Router handles non-existent content
    echo "Test 9: Router handles non-existent content gracefully (no duplication)\n";
    // FQCN call: test_router.php runs in the global namespace, so
    // an unqualified router() is a lookup miss. Same shape as
    // Test 3e (which runs unconditionally), but here we exercise
    // the path through the database-aware blurb handler before
    // falling through to router_handleError.
    //
    // Production contract (post-fix):
    //   - page\error() prints the styled chrome via displaypage()
    //     and returns null.
    //   - router_handleError then returns ROUTER_RENDERED.
    //   - The dispatch loop maps ROUTER_RENDERED -> '' so the
    //     HTTP entry-point's `echo $router_result` is a no-op.
    //   - The handler NEVER emits a trailing <html><title>404>
    //     fallback block in production; that would duplicate the
    //     already-printed styled chrome.
    //
    // Capture stdout and assert there's exactly one <title> tag
    // (i.e. the styled chrome is present once, with no trailing
    // duplicate block). The pre-fix shape had two <title> tags
    // (the styled chrome + the trailing fallback).
    ob_start();
    $result = \bbsengine6\router\router("nonexistent/xyz123");
    $body = ob_get_clean();
    $titleCount = substr_count($body, '<title>');
    if ($result === ''
        && $titleCount === 1
        && strpos($body, 'bbsengine.org errormessage.tmpl') !== false) {
        echo "  ✓ PASS: router returned ''; stdout contains exactly one styled error (title count=$titleCount)\n";
    } else {
        echo "  ✗ FAIL: expected '' return + single styled body; got result="
             . var_export($result, true) . ", title count=$titleCount, body length=" . strlen($body) . "\n";
        exit(1);
    }
    echo "\n";
}

// =============================================================================
// URL GENERATION TESTS
// =============================================================================

echo "--- URL Generation Tests ---\n\n";

// Test: sig URI must produce valid URL when concatenated with TEOSURL
echo "Test 10: sig URI produces valid URL (no missing slash)\n";
// TEOSURL = /teos/ (with trailing slash), sig.uri = rec/arts/star-trek/ (no leading slash)
$teosurl = '/teos/';
$item_uri = '/teos/rec/arts/star-trek/';
$teosbase = rtrim($teosurl, '/');
$reluri = ltrim(substr($item_uri, strlen($teosbase)), '/');
$full_url = rtrim($teosurl, '/') . '/' . $reluri;
echo "  reluri = '$reluri'\n";
echo "  full URL = '$full_url'\n";
if ($full_url === '/teos/rec/arts/star-trek/') {
    echo "  ✓ PASS: URL is correct\n";
} else {
    echo "  ✗ FAIL: expected /teos/rec/arts/star-trek/, got $full_url\n";
    exit(1);
}

// Test: relative URI has no leading /
echo "Test 11: relative URI has no leading /\n";
$item_uri2 = '/teos/comp/python/';
$reluri2 = ltrim(substr($item_uri2, strlen($teosbase)), '/');
if (strpos($reluri2, '/') === 0) {
    echo "  ✗ FAIL: reluri has leading /: $reluri2\n";
    exit(1);
} else {
    echo "  ✓ PASS: reluri = $reluri2\n";
}

// Test: TEOSURL + reluri joins with exactly one slash
echo "Test 12: TEOSURL + reluri joins correctly\n";
$teosurl_ns = '/teos';  // without trailing slash (fallback)
$teosbase_ns = rtrim($teosurl_ns, '/');
$reluri3 = ltrim(substr($item_uri, strlen($teosbase_ns)), '/');
$full_url3 = $teosurl_ns . '/' . $reluri3;
if ($full_url3 === '/teos/rec/arts/star-trek/') {
    echo "  ✓ PASS: $full_url3\n";
} else {
    echo "  ✗ FAIL: expected /teos/rec/arts/star-trek/, got $full_url3\n";
    exit(1);
}

echo "\n";

// =============================================================================
// BREADCRUMB TESTS
// =============================================================================

echo "--- Breadcrumb Tests ---\n\n";

// Define TEOSURL for breadcrumb tests
if (!defined('TEOSURL')) {
    define('TEOSURL', '/teos/');
}

// Test: router_buildBreadcrumbs with path segments
echo "Test 13: router_buildBreadcrumbs builds correct crumbs\n";
$breadcrumbs = router_buildBreadcrumbs("rec/arts/star-trek");
if (count($breadcrumbs) === 4) {
    echo "  ✓ PASS: 4 breadcrumbs for rec/arts/star-trek\n";
} else {
    echo "  ✗ FAIL: expected 4 breadcrumbs, got " . count($breadcrumbs) . "\n";
    exit(1);
}

// Test: breadcrumb titles
echo "Test 14: breadcrumb titles are title-cased\n";
if ($breadcrumbs[1]['title'] === 'rec' && $breadcrumbs[2]['title'] === 'arts' && $breadcrumbs[3]['title'] === 'star trek') {
    echo "  ✓ PASS: titles = rec, arts, star trek\n";
} else {
    echo "  ✗ FAIL: titles = " . $breadcrumbs[1]['title'] . ", " . $breadcrumbs[2]['title'] . ", " . $breadcrumbs[3]['title'] . "\n";
    exit(1);
}

// Test: breadcrumb URIs
echo "Test 15: breadcrumb URIs have trailing slash\n";
if ($breadcrumbs[0]['uri'] === '/teos/' && $breadcrumbs[3]['uri'] === '/teos/rec/arts/star-trek/') {
    echo "  ✓ PASS: URIs = /teos/, /teos/rec/arts/star-trek/\n";
} else {
    echo "  ✗ FAIL: uri[0]=" . $breadcrumbs[0]['uri'] . " uri[3]=" . $breadcrumbs[3]['uri'] . "\n";
    exit(1);
}

// Test: empty URI returns empty array
echo "Test 16: empty URI returns empty breadcrumbs\n";
$empty = router_buildBreadcrumbs("");
if (empty($empty)) {
    echo "  ✓ PASS: empty URI → empty breadcrumbs\n";
} else {
    echo "  ✗ FAIL: expected empty array\n";
    exit(1);
}

// Test: breadcrumbs work without DB (auto-generated fallback)
echo "Test 17: breadcrumbs auto-generate without DB connection\n";
// This tests that router_buildBreadcrumbs returns valid crumbs even when DB is unavailable
$crumbs_no_db = router_buildBreadcrumbs("comp/lang/python");
if (count($crumbs_no_db) === 4
    && $crumbs_no_db[0]['path'] === 'teos'
    && $crumbs_no_db[1]['path'] === 'comp'
    && $crumbs_no_db[2]['path'] === 'comp.lang'
    && $crumbs_no_db[3]['path'] === 'comp.lang.python'
    && $crumbs_no_db[0]['uri'] === '/teos/'
    && $crumbs_no_db[1]['uri'] === '/teos/comp/'
    && $crumbs_no_db[2]['uri'] === '/teos/comp/lang/'
    && $crumbs_no_db[3]['uri'] === '/teos/comp/lang/python/') {
    echo "  ✓ PASS: auto-generated breadcrumbs correct\n";
} else {
    echo "  ✗ FAIL: auto-generated breadcrumbs incorrect\n";
    exit(1);
}

// Test: single segment produces one crumb
echo "Test 18: single segment URI produces one crumb\n";
$crumbs_single = router_buildBreadcrumbs("rec");
if (count($crumbs_single) === 2
    && $crumbs_single[0]['path'] === 'teos'
    && $crumbs_single[0]['title'] === 'teos'
    && $crumbs_single[0]['uri'] === '/teos/'
    && $crumbs_single[1]['path'] === 'rec'
    && $crumbs_single[1]['title'] === 'rec'
    && $crumbs_single[1]['uri'] === '/teos/rec/') {
    echo "  ✓ PASS: single crumb correct\n";
} else {
    echo "  ✗ FAIL: single crumb incorrect\n";
    exit(1);
}

// Test: hyphens in segments are title-cased with spaces
echo "Test 19: hyphens in segments become spaces in title\n";
$crumbs_hyphen = router_buildBreadcrumbs("rec/arts/star-trek");
if ($crumbs_hyphen[3]['title'] === 'star trek' && $crumbs_hyphen[3]['path'] === 'rec.arts.star-trek') {
    echo "  ✓ PASS: star-trek → 'star trek', path = rec.arts.star-trek\n";
} else {
    echo "  ✗ FAIL: title=" . $crumbs_hyphen[3]['title'] . " path=" . $crumbs_hyphen[3]['path'] . "\n";
    exit(1);
}

// Test: trailing slash in URI is handled
echo "Test 20: trailing slash in URI is handled\n";
$crumbs_trail = router_buildBreadcrumbs("rec/arts/");
if (count($crumbs_trail) === 3) {
    echo "  ✓ PASS: trailing slash ignored, 3 crumbs\n";
} else {
    echo "  ✗ FAIL: expected 3 crumbs, got " . count($crumbs_trail) . "\n";
    exit(1);
}

// =============================================================================
// router_collectDirectoryItems — YAML frontmatter title handling (2026-09-27)
// =============================================================================
// folder.tmpl prints {$item.title} raw, so router_collectDirectoryItems must
// htmlspecialchars-escape YAML-derived titles. These tests pin that contract
// and the empty/whitespace-title fallback to the filename.

function _rcfi_setup_tmpdir(): string {
    $tmp = sys_get_temp_dir() . "/rcfi_test_" . bin2hex(random_bytes(4));
    mkdir($tmp);
    return $tmp;
}

function _rcdi_helper(array $files, string $uri): array {
    $dir = _rcfi_setup_tmpdir();
    foreach ($files as $name => $content) {
        file_put_contents($dir . "/" . $name, $content);
    }
    $items = \bbsengine6\router\router_collectDirectoryItems($dir, $uri);
    foreach ($files as $name => $_) {
        @unlink($dir . "/" . $name);
    }
    @rmdir($dir);
    return $items;
}

echo "Test 21: router_collectDirectoryItems escapes HTML in YAML title (XSS)\n";
$items = _rcdi_helper(
    ["xss.md" => "---\ntitle: <b>oops</b>\n---\nbody"],
    "test"
);
$byFile = [];
foreach ($items as $it) { $byFile[$it['filename']] = $it; }
if (isset($byFile['xss.md']) && $byFile['xss.md']['title'] === '&lt;b&gt;oops&lt;/b&gt;') {
    echo "  ✓ PASS: HTML tags in title escaped\n";
} else {
    echo "  ✗ FAIL: expected '&lt;b&gt;oops&lt;/b&gt;', got " .
        var_export($byFile['xss.md']['title'] ?? '(missing)', true) . "\n";
    exit(1);
}

echo "Test 22: router_collectDirectoryItems falls back to filename on empty title\n";
$items = _rcdi_helper(
    ["empty-title.md" => "---\ntitle:\n---\nbody"],
    "test"
);
$byFile = [];
foreach ($items as $it) { $byFile[$it['filename']] = $it; }
if (isset($byFile['empty-title.md']) && $byFile['empty-title.md']['title'] === 'empty-title') {
    echo "  ✓ PASS: empty title falls back to filename\n";
} else {
    echo "  ✗ FAIL: expected 'empty-title', got " .
        var_export($byFile['empty-title.md']['title'] ?? '(missing)', true) . "\n";
    exit(1);
}

echo "Test 23: router_collectDirectoryItems falls back to filename on whitespace-only title\n";
$items = _rcdi_helper(
    ["ws-title.md" => "---\ntitle:    \n---\nbody"],
    "test"
);
$byFile = [];
foreach ($items as $it) { $byFile[$it['filename']] = $it; }
if (isset($byFile['ws-title.md']) && $byFile['ws-title.md']['title'] === 'ws-title') {
    echo "  ✓ PASS: whitespace-only title falls back to filename\n";
} else {
    echo "  ✗ FAIL: expected 'ws-title', got " .
        var_export($byFile['ws-title.md']['title'] ?? '(missing)', true) . "\n";
    exit(1);
}

echo "Test 24: router_collectDirectoryItems escapes ampersands in YAML title\n";
$items = _rcdi_helper(
    ["amp.md" => "---\ntitle: real & stuff\n---\nbody"],
    "test"
);
$byFile = [];
foreach ($items as $it) { $byFile[$it['filename']] = $it; }
if (isset($byFile['amp.md']) && $byFile['amp.md']['title'] === 'real &amp; stuff') {
    echo "  ✓ PASS: ampersand escaped to &amp;\n";
} else {
    echo "  ✗ FAIL: expected 'real &amp; stuff', got " .
        var_export($byFile['amp.md']['title'] ?? '(missing)', true) . "\n";
    exit(1);
}

echo "Test 25: router_collectDirectoryItems strips literal quotes from YAML title\n";
$items = _rcdi_helper(
    ["quoted.md" => "---\ntitle: \"quoted\"\n---\nbody"],
    "test"
);
$byFile = [];
foreach ($items as $it) { $byFile[$it['filename']] = $it; }
if (isset($byFile['quoted.md']) && $byFile['quoted.md']['title'] === 'quoted') {
    echo "  ✓ PASS: literal quotes stripped\n";
} else {
    echo "  ✗ FAIL: expected 'quoted', got " .
        var_export($byFile['quoted.md']['title'] ?? '(missing)', true) . "\n";
    exit(1);
}

echo "\n";

echo "=== All tests passed! ===\n";
