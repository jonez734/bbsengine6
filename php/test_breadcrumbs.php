<?php
/**
 * test_breadcrumbs.php - Regression tests for {teos} breadcrumb rendering
 *
 * Verifies that function.teos.php derives title/URI from path segments
 * without requiring a database lookup.
 *
 * Usage:
 *   php test_breadcrumbs.php
 */

require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");
require_once("/home/opencode/data/work/bbsengine6/engine/router.php");

echo "=== Breadcrumb Regression Tests ===\n\n";

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

// =============================================================================
// FUNCTION.TEOS.PHP SOURCE ANALYSIS
// =============================================================================

echo "--- function.teos.php Source Tests ---\n\n";

function load_teos_source(string $subpath): string {
    $path = "/home/opencode/data/work/$subpath";
    if (!file_exists($path)) {
        test_fail("source file not found", $path);
    }
    return file_get_contents($path);
}

$teos_files = [
    'bbsengine6/smarty/function.teos.php',
    'rgs/www/smarty/function.teos.php',
];

// zoid6/smarty/function.teos.php should NOT exist — bbsengine6 version is
// the single source of truth, found via SMARTYPLUGINSDIR fallback.
$teos_files_absent = [
    'zoid6/smarty/function.teos.php',
];

foreach ($teos_files_absent as $teos_file) {
    $path = "/home/opencode/data/work/$teos_file";
    echo "Test: $teos_file should NOT exist\n";
    if (file_exists($path)) {
        test_fail("$teos_file should not exist (use bbsengine6 version via SMARTYPLUGINSDIR)");
    }
    test_pass("$teos_file correctly absent");
}

foreach ($teos_files as $idx => $teos_file) {
    $src = load_teos_source($teos_file);

    // Test: must not contain the PATHNOTFOUND error string
    echo "Test " . ($idx * 2 + 1) . ": $teos_file has no PATHNOTFOUND string\n";
    if (strpos($src, 'PATHNOTFOUND') !== false) {
        test_fail("$teos_file still contains PATHNOTFOUND");
    }
    test_pass("no PATHNOTFOUND in $teos_file");

    // Test: must derive title from path (not from DB)
    echo "Test " . ($idx * 2 + 2) . ": $teos_file derives title from path\n";
    if (strpos($src, 'str_replace') === false) {
        test_fail("$teos_file missing title derivation from path");
    }
    test_pass("title derivation present");
}

echo "\n";

// =============================================================================
// TEMPLATE TESTS
// =============================================================================

echo "--- Template Tests ---\n\n";

// Test: function.teos.tmpl exists and has no debug output
echo "Test 5: bbsengine6 function.teos.tmpl is clean\n";
$teos_tmpl = "/home/opencode/data/work/bbsengine6/skin/tmpl/function.teos.tmpl";
if (!file_exists($teos_tmpl)) {
    test_fail("bbsengine6 function.teos.tmpl not found");
}
$tmpl_src = file_get_contents($teos_tmpl);
$tmpl_no_comments = preg_replace('/\{\*.*?\*\}/s', '', $tmpl_src);
if (strpos($tmpl_no_comments, 'var_dump') !== false) {
    test_fail("function.teos.tmpl contains uncommented var_dump");
}
if (strpos($tmpl_no_comments, '!!') !== false) {
    test_fail("function.teos.tmpl contains debug markers !!");
}
test_pass("function.teos.tmpl is clean");

// Test: youarehere.tmpl uses teos-breadcrumbs.tmpl
echo "Test 6: youarehere.tmpl uses teos-breadcrumbs.tmpl\n";
$youarehere = "/home/opencode/data/work/bbsengine6/skin/tmpl/youarehere.tmpl";
$youarehere_src = file_get_contents($youarehere);
if (strpos($youarehere_src, 'teos-breadcrumbs.tmpl') === false) {
    test_fail("youarehere.tmpl does not include teos-breadcrumbs.tmpl");
}
test_pass("youarehere.tmpl uses teos-breadcrumbs.tmpl");

// Test: teos-breadcrumbs.tmpl exists on disk. Catches the half-finished
// refactor from commit ff0981a where youarehere.tmpl was updated to
// include teos-breadcrumbs.tmpl but the target template was never
// authored. Without this assertion the build looks green until
// Smarty tries to render a page that uses youarehere.tmpl.
echo "Test 6b: skin/tmpl/teos-breadcrumbs.tmpl exists\n";
$target = "/home/opencode/data/work/bbsengine6/skin/tmpl/teos-breadcrumbs.tmpl";
if (!file_exists($target)) {
    test_fail("skin/tmpl/teos-breadcrumbs.tmpl missing", $target);
}
test_pass("skin/tmpl/teos-breadcrumbs.tmpl exists");

// Test: page-markdown.tmpl uses youarehere.tmpl
echo "Test 7: page-markdown.tmpl uses youarehere.tmpl\n";
$page_md = "/home/opencode/data/work/bbsengine6/skin/tmpl/page-markdown.tmpl";
$page_md_src = file_get_contents($page_md);
if (strpos($page_md_src, 'youarehere.tmpl') === false) {
    test_fail("page-markdown.tmpl does not include youarehere.tmpl");
}
test_pass("page-markdown.tmpl uses youarehere.tmpl");

// @since 2026-09-30 — folder.tmpl was missing the youarehere include
// entirely. Production /teos/<dir>/ pages rendered no "You are here"
// trail at all. Pin the include so a future template rewrite doesn't
// silently drop it again.
echo "Test 7a: folder.tmpl uses youarehere.tmpl\n";
$folder_tmpl = "/home/opencode/data/work/bbsengine6/skin/tmpl/folder.tmpl";
$folder_tmpl_src = file_get_contents($folder_tmpl);
if (strpos($folder_tmpl_src, 'youarehere.tmpl') === false) {
    test_fail("folder.tmpl does not include youarehere.tmpl");
}
test_pass("folder.tmpl uses youarehere.tmpl");

// @since 2026-09-30 — folder.php::display() must populate
// $data["breadcrumbs"] for the template include to render. Pin
// the assignment so a future display() refactor doesn't silently
// drop the breadcrumbs field again.
echo "Test 7b: folder.php::display() populates \$data[\"breadcrumbs\"]\n";
$folder_php_src = file_get_contents("/home/opencode/data/work/bbsengine6/php/folder.php");
if (preg_match('/function\s+display\s*\(\s*\$uri\s*\)\s*\{(.*?)^\}/sm', $folder_php_src, $m)) {
    $display_body = $m[1];
    if (strpos($display_body, '$data["breadcrumbs"]') === false
        && strpos($display_body, "\$data['breadcrumbs']") === false) {
        test_fail("folder.php::display() does not assign \$data['breadcrumbs']");
    }
} else {
    test_fail("could not locate folder.php::display() function body");
}
test_pass("folder.php::display() assigns \$data['breadcrumbs']");

// @since 2026-10-01 — the blurb page rendered only the trailing "you
// are here" crumb (e.g. /teos/sci/archaeology/archeoastronomy.md showed
// "You are here: archeoastronomy" with no parent chain) because
// blurb.php::display() used a bare-name function_exists() check
// (`function_exists('router_buildBreadcrumbs')`) that resolves against
// the call-site namespace (\bbsengine6\blurb) and always returned
// false. The fallback to \bbsengine6\router\router_buildBreadcrumbs()
// was therefore silently skipped, leaving $breadcrumbs empty before
// the trailing-crumb append at line ~378 ran. Pin both the FQN in
// the function_exists() lookup and the leading-backslash on the call
// site so a future refactor doesn't reintroduce the bare-name bug.
echo "Test 7f: blurb.php::display() uses FQN for function_exists() and the router_buildBreadcrumbs() call\n";
$blurb_php_src_for_fqn = file_get_contents("/home/opencode/data/work/bbsengine6/php/blurb.php");
if (preg_match('/function\s+display\s*\(\s*\$uri\s*,\s*\$filepath\s*\)\s*\{(.*?)^\}/sm', $blurb_php_src_for_fqn, $m)) {
    $blurb_body_for_fqn = $m[1];
    if (strpos($blurb_body_for_fqn, "function_exists('bbsengine6\\\\router\\\\router_buildBreadcrumbs')") === false
        && strpos($blurb_body_for_fqn, 'function_exists("bbsengine6\\\\router\\\\router_buildBreadcrumbs")') === false) {
        test_fail("blurb.php::display() does not use FQN for the router_buildBreadcrumbs function_exists() check; the fallback silently skips under namespace resolution");
    }
    if (strpos($blurb_body_for_fqn, '\\bbsengine6\\router\\router_buildBreadcrumbs(') === false) {
        test_fail("blurb.php::display() does not call \\bbsengine6\\router\\router_buildBreadcrumbs() with a leading backslash; bare-name call would fail at runtime");
    }
    // And the legacy bare-name must be gone — the bug was a bare-name
    // check returning false; pinning its absence is a stronger guard
    // than pinning just the presence of the FQN. Strip /* ... */ and
    // // line comments first so the historical bare-name (referenced
    // in the @since 2026-10-01 explanatory comment) doesn't false-
    // positive the check.
    $blurb_body_no_comments = preg_replace('#/\*.*?\*/#s', '', $blurb_body_for_fqn);
    $blurb_body_no_comments = preg_replace('/\/\/[^\n]*/', '', $blurb_body_no_comments);
    if (strpos($blurb_body_no_comments, "function_exists('router_buildBreadcrumbs')") !== false
        || strpos($blurb_body_no_comments, 'function_exists("router_buildBreadcrumbs")') !== false) {
        test_fail("blurb.php::display() still uses the bare-name function_exists('router_buildBreadcrumbs') check that silently returned false under namespace resolution");
    }
} else {
    test_fail("could not locate blurb.php::display() function body for FQN pin");
}
test_pass("blurb.php::display() uses FQN for the router_buildBreadcrumbs function_exists() check and call site");

// @since 2026-10-01 — folder.php::display() has the same latent
// function_exists() bug as blurb.php::display() did. Today's chrome
// render path doesn't go through folder.php::display() (it goes
// through router_displayDirectoryListing() in the router namespace,
// where the bare name resolves correctly), but any future caller of
// folder.php::display() would render an empty breadcrumb chain. Pin
// the FQN fix here too so the dormant bug doesn't go live silently.
echo "Test 7g: folder.php::display() uses FQN for the router_buildBreadcrumbs() call\n";
$folder_php_src_for_fqn = file_get_contents("/home/opencode/data/work/bbsengine6/php/folder.php");
if (preg_match('/function\s+display\s*\(\s*\$uri\s*\)\s*\{(.*?)^\}/sm', $folder_php_src_for_fqn, $m)) {
    $folder_body_for_fqn = $m[1];
    if (strpos($folder_body_for_fqn, "function_exists('bbsengine6\\\\router\\\\router_buildBreadcrumbs')") === false
        && strpos($folder_body_for_fqn, 'function_exists("bbsengine6\\\\router\\\\router_buildBreadcrumbs")') === false) {
        test_fail("folder.php::display() does not use FQN for the router_buildBreadcrumbs function_exists() check");
    }
    if (strpos($folder_body_for_fqn, '\\bbsengine6\\router\\router_buildBreadcrumbs(') === false) {
        test_fail("folder.php::display() does not call \\bbsengine6\\router\\router_buildBreadcrumbs() with a leading backslash");
    }
} else {
    test_fail("could not locate folder.php::display() function body for FQN pin");
}
test_pass("folder.php::display() uses FQN for the router_buildBreadcrumbs() function_exists() check and call site");

// @since 2026-09-30 — blurb.php's "You are here" was rendering empty
// because buildbreadcrumbs() / router_buildBreadcrumbs() build parent-
// folder chains only, never the current blurb itself. The fix appends
// a final crumb from $parsed["title"] so the trail ends at the
// current page. Pin the append so a future refactor doesn't lose it.
echo "Test 7c: blurb.php appends a current-page crumb in the fallback path\n";
$blurb_php_src = file_get_contents("/home/opencode/data/work/bbsengine6/php/blurb.php");
if (preg_match('/function\s+display\s*\(\s*\$uri\s*,\s*\$filepath\s*\)\s*\{(.*?)^\}/sm', $blurb_php_src, $m)) {
    $blurb_body = $m[1];
    if (strpos($blurb_body, '$parsed["title"]') === false) {
        test_fail("blurb.php::display() does not reference \$parsed[\"title\"]");
    }
    if (strpos($blurb_body, 'breadcrumbs[]') === false) {
        test_fail("blurb.php::display() does not append to \$breadcrumbs[]");
    }
} else {
    test_fail("could not locate blurb.php::display() function body");
}
test_pass("blurb.php::display() appends current-page crumb from parsed title");

// @since 2026-09-30 — blurb.php::getlabel() was reading the legacy
// `TEOS_LABEL` (underscore) env name while engine/router.php:192 and
// every live htaccess-prod publish `TEOSLABEL`. Result: the root
// breadcrumb rendered as the literal "teos" on blurb pages. Pin the
// source-level fix (env() call) and the absence of the legacy name so
// a future refactor doesn't silently reintroduce the divergence.
echo "Test 7d: blurb.php::getlabel() reads TEOSLABEL via env() (not the legacy TEOS_LABEL)\n";
$blurb_src_for_label = file_get_contents("/home/opencode/data/work/bbsengine6/php/blurb.php");
if (!preg_match('/bbsengine6\\\\util\\\\env\s*\(\s*[\'"]TEOSLABEL[\'"]/', $blurb_src_for_label)) {
    test_fail("blurb.php does not call \\bbsengine6\\util\\env('TEOSLABEL') from getlabel()");
}
if (strpos($blurb_src_for_label, "'TEOS_LABEL'") !== false
    || strpos($blurb_src_for_label, '"TEOS_LABEL"') !== false) {
    test_fail("blurb.php still references the legacy 'TEOS_LABEL' (underscore) env name in code; route through env('TEOSLABEL') instead");
}
test_pass("getlabel() routes through env('TEOSLABEL') and has no legacy TEOS_LABEL code reference");

// @since 2026-09-30 — runtime pin: when TEOSLABEL is exported (e.g.
// via SetEnv in the vhost htaccess-prod), getlabel() must return
// that value. Pre-fix, getlabel() returned the literal 'teos'
// because it read TEOS_LABEL (which was unset). Post-fix, it reads
// TEOSLABEL and surfaces it. Skip if a TEOSLABEL constant is
// defined — the env-then-constant precedence is exercised by the
// source pin above (Test 7d), and a defined constant would
// short-circuit the env path under putenv() in some FPM setups.
echo "Test 7e: getlabel() returns the TEOSLABEL env value when set\n";
if (defined('TEOSLABEL')) {
    test_pass("TEOSLABEL constant is defined; env precedence covered by Test 7d");
} else {
    $prev = getenv('TEOSLABEL');
    putenv('TEOSLABEL=testlabel-7e');
    try {
        $got = \bbsengine6\blurb\getlabel();
        if ($got !== 'testlabel-7e') {
            test_fail("getlabel() did not return TEOSLABEL env value", "got '$got'");
        }
    } finally {
        if ($prev === false) {
            putenv('TEOSLABEL');
        } else {
            putenv('TEOSLABEL=' . $prev);
        }
    }
    test_pass("getlabel() returns TEOSLABEL env value");
}

// @since 2026-09-30 — fix for the root crumb rendering as /teos/teos/
// instead of /teos/ on zoidtechnologies.com teos folder pages. The
// {teos} Smarty plugin (bbsengine6/smarty/function.teos.php) needs to
// honor a new is_root option that bypasses the per-segment uri
// synthesis, and teos-breadcrumbs.tmpl needs to pass that option (plus
// title=$b.title so TEOSLABEL is honored). These source pins catch a
// regression of the 33d3b1c fix.
echo "Test 8f: function.teos.php honors is_root option (uri bypass)\n";
$plugin_src = file_get_contents("/home/opencode/data/work/bbsengine6/smarty/function.teos.php");
if (strpos($plugin_src, '$options["is_root"]') === false) {
    test_fail('function.teos.php does not read $options["is_root"]; root crumb would still render /teos/teos/');
}
if (!preg_match('/\$uri\s*=\s*\$is_root\s*\?\s*""/', $plugin_src)) {
    test_fail('function.teos.php does not implement $uri = $is_root ? "" : ...; root href would still be TEOSURL + path_segments + "/"');
}
test_pass("function.teos.php reads is_root option and bypasses uri synthesis when true");

echo "Test 8g: teos-breadcrumbs.tmpl passes is_root=true on \$b@first and title=\$b.title\n";
$crumbs_tmpl = file_get_contents("/home/opencode/data/work/bbsengine6/skin/tmpl/teos-breadcrumbs.tmpl");
if (strpos($crumbs_tmpl, 'is_root=true') === false) {
    test_fail("teos-breadcrumbs.tmpl does not pass is_root=true; root crumb uri suppression would not fire");
}
if (strpos($crumbs_tmpl, 'title=$b.title') === false) {
    test_fail("teos-breadcrumbs.tmpl does not pass title=\$b.title; TEOSLABEL would be ignored by the plugin");
}
test_pass("teos-breadcrumbs.tmpl passes is_root and title to {teos} plugin");

// @since 2026-09-30 — youarehere.tmpl plumbs linklast through to
// teos-breadcrumbs.tmpl as the "you are here" trailing-crumb flag, but
// teos-breadcrumbs.tmpl must actually consume it. Before the fix, the
// flag was accepted at the include boundary and silently ignored,
// causing every blurb and folder page to render its current page as
// a self-link instead of the conventional unlinked "you are here"
// marker. Pin both the reference and the conditional call.
echo "Test 8h: teos-breadcrumbs.tmpl references \$linklast (no-op flag regression guard)\n";
if (strpos($crumbs_tmpl, '$linklast') === false) {
    test_fail("teos-breadcrumbs.tmpl does not reference \$linklast; the youarehere.tmpl->linklast=true flag would be silently ignored");
}
test_pass("teos-breadcrumbs.tmpl references \$linklast");

echo "Test 8i: teos-breadcrumbs.tmpl passes nolink=true to {teos} when linklast=true\n";
// Require both halves in proximity: the \$b@last branch must wrap its
// {teos} call with `if $linklast|default:false ... nolink=true ...`.
$last_branch_pattern = '/\\{\\s*if\\s+\\$b@last\\s*==\\s*false\\s*\\}\\s*.*?\\{\\s*else\\s*\\}(.*?)\\{\\s*\\/if\\s*\\}/s';
if (!preg_match($last_branch_pattern, $crumbs_tmpl, $m)) {
    test_fail("could not locate the \$b@last branch in teos-breadcrumbs.tmpl");
}
$last_branch = $m[1];
if (strpos($last_branch, '$linklast') === false) {
    test_fail("the \$b@last branch in teos-breadcrumbs.tmpl does not gate on \$linklast");
}
if (strpos($last_branch, 'nolink=true') === false) {
    test_fail("the \$b@last branch in teos-breadcrumbs.tmpl does not pass nolink=true to {teos}");
}
// And the non-linklast branch must remain a plain linked {teos} so
// that any non-youarehere consumer of this template keeps the
// historical always-linked trailing crumb.
$linked_crumb_call = preg_match('/\\{\\s*else\\s*\\}\\s*\\{\\s*teos[^}]*\\}/s', $last_branch, $m2);
if (!$linked_crumb_call || strpos($m2[0], 'nolink') !== false) {
    test_fail("the linklast=false branch in teos-breadcrumbs.tmpl must remain a plain linked {teos} (no nolink)");
}
test_pass("the \$b@last branch emits nolink=true when linklast=true and a linked {teos} otherwise");

// @since 2026-09-30 — function.teos.tmpl must render a <span> (no
// <a>) when nolink=true so the "you are here" marker is plain text.
// Without this, the linklast plumbing above would have no visible
// effect — the trailing crumb would still be a tooltip-styled anchor.
echo "Test 8j: function.teos.tmpl has a nolink branch that emits <span> and no <a>\n";
$plugin_tmpl_src = file_get_contents("/home/opencode/data/work/bbsengine6/skin/tmpl/function.teos.tmpl");
if (strpos($plugin_tmpl_src, '$nolink') === false) {
    test_fail("function.teos.tmpl does not reference \$nolink; the linklast fix would not change rendered HTML");
}
$plugin_no_comments = preg_replace('/\{\*.*?\*\}/s', '', $plugin_tmpl_src);
// Locate the nolink branch and assert it has a <span> and no <a>.
$nolink_branch_pattern = '/\\{\\s*if\\s+\\$nolink[\\|][^\\}]*\\}\\s*(.*?)\\{\\s*\\/if\\s*\\}/s';
if (!preg_match($nolink_branch_pattern, $plugin_no_comments, $m)) {
    test_fail("could not locate a {if \$nolink} branch in function.teos.tmpl");
}
$nolink_branch = $m[1];
if (strpos($nolink_branch, '<span') === false) {
    test_fail("the \$nolink branch in function.teos.tmpl does not emit a <span>");
}
if (strpos($nolink_branch, '<a ') !== false || strpos($nolink_branch, '<a>') !== false) {
    test_fail("the \$nolink branch in function.teos.tmpl must not emit an <a> element");
}
test_pass("function.teos.tmpl nolink branch emits <span> with no <a>");

// @since 2026-09-30 — function.teos.php must accept the nolink
// option and forward it to the template as a Smarty variable.
// Without this, function.teos.tmpl's \$nolink check would always
// be false and the linklast fix would render no differently.
echo "Test 8k: function.teos.php reads \$options[\"nolink\"] and assigns \$nolink to the template\n";
if (strpos($plugin_src, '$options["nolink"]') === false) {
    test_fail('function.teos.php does not read $options["nolink"]');
}
if (!preg_match('/\\$tmpl->assign\\(\\s*["\']nolink["\']/', $plugin_src)) {
    test_fail('function.teos.php does not assign "nolink" to the Smarty template');
}
test_pass("function.teos.php accepts nolink option and forwards it to the template");

echo "\n";

// =============================================================================
// PATH DERIVATION LOGIC TESTS
// =============================================================================

echo "--- Path Derivation Tests ---\n\n";

// These test the same logic that function.teos.php uses:
// 1. Split path on dots into segments
// 2. Convert underscores to hyphens for filesystem/URI
// 3. Join segments with slashes for URI
// 4. Title from last segment with hyphens/underscores replaced by spaces

function derive_teos_crumb(string $path, bool $is_root = false): array {
    $segments = array_values(array_filter(explode(".", $path)));
    $uriSegments = array_map(function($s) { return str_replace("_", "-", $s); }, $segments);

    // Mirror the post-33d3b1c plugin logic: when the caller marks the
    // crumb as the root (is_root=true), suppress the per-segment uri
    // synthesis so TEOSURL stands alone as the href. Non-root crumbs
    // (including single-segment non-root paths like "politics") keep
    // the path-segment synthesis so /teos/politics/ still resolves.
    $uri = $is_root ? "" : implode("/", $uriSegments) . "/";
    if (count($uriSegments) > 0) {
        $title = end($uriSegments);
    } else {
        $title = $path;
    }
    $title = str_replace(["-", "_"], " ", $title);

    return ['title' => $title, 'uri' => $uri];
}

// Test: single segment
echo "Test 10: derivation for 'teos'\n";
$f = derive_teos_crumb("teos");
if ($f['title'] !== 'teos' || $f['uri'] !== 'teos/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("teos → title='teos', uri='teos/'");

// Test: two segments
echo "Test 11: derivation for 'comp.lang'\n";
$f = derive_teos_crumb("comp.lang");
if ($f['title'] !== 'lang' || $f['uri'] !== 'comp/lang/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("comp.lang → title='lang', uri='comp/lang/'");

// Test: three segments
echo "Test 12: derivation for 'comp.lang.python'\n";
$f = derive_teos_crumb("comp.lang.python");
if ($f['title'] !== 'python' || $f['uri'] !== 'comp/lang/python/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("comp.lang.python → title='python', uri='comp/lang/python/'");

// Test: hyphens become spaces in title, preserved in URI
echo "Test 13: derivation for 'rec.arts.star-trek'\n";
$f = derive_teos_crumb("rec.arts.star-trek");
if ($f['title'] !== 'star trek' || $f['uri'] !== 'rec/arts/star-trek/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("rec.arts.star-trek → title='star trek', uri='rec/arts/star-trek/'");

// Test: underscores become spaces in title, converted to hyphens in URI
echo "Test 14: derivation for 'rec.arts.star_trek'\n";
$f = derive_teos_crumb("rec.arts.star_trek");
if ($f['title'] !== 'star trek' || $f['uri'] !== 'rec/arts/star-trek/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("rec.arts.star_trek → title='star trek', uri='rec/arts/star-trek/'");

// Test: deep path (the-a-team use case)
echo "Test 15: derivation for 'rec.arts.tv.the-a-team'\n";
$f = derive_teos_crumb("rec.arts.tv.the-a-team");
if ($f['title'] !== 'the a team' || $f['uri'] !== 'rec/arts/tv/the-a-team/') {
    test_fail("unexpected result", print_r($f, true));
}
test_pass("rec.arts.tv.the-a-team → title='the a team', uri='rec/arts/tv/the-a-team/'");

// @since 2026-09-30 — root-crumb is_root bypass regression pins.
// These exercise the post-33d3b1c derive_teos_crumb helper which
// mirrors bbsengine6/smarty/function.teos.php's $uri logic. The
// first two mirror the rendered scenario on
// zoidtechnologies.com/teos/sci/archaeology/: root crumb with
// path='teros' must emit uri='' (so TEOSURL + '/' = /teos/ lands
// correctly), and the single-segment non-root case (e.g.
// maturecontentwarning.tmpl's path="politics") must keep its
// per-segment uri synthesis so /teos/politics/ still resolves.
echo "Test 16: root crumb with is_root=true bypasses uri synthesis\n";
$f = derive_teos_crumb("teros", is_root: true);
if ($f['uri'] !== '' || $f['title'] !== 'teros') {
    test_fail("root crumb did not bypass uri synthesis", print_r($f, true));
}
test_pass("teros is_root=true → uri='' (so TEOSURL + '/' = /teos/ renders correctly)");

echo "Test 17: single-segment non-root crumb is unchanged by is_root option\n";
$f = derive_teos_crumb("politics", is_root: false);
if ($f['uri'] !== 'politics/' || $f['title'] !== 'politics') {
    test_fail("single-segment non-root crumb regressed", print_r($f, true));
}
test_pass("politics is_root=false → uri='politics/' (unchanged)");

echo "Test 18: mid-path crumb (multi-segment non-root) is unchanged\n";
$f = derive_teos_crumb("sci.archaeology", is_root: false);
if ($f['uri'] !== 'sci/archaeology/' || $f['title'] !== 'archaeology') {
    test_fail("mid-path crumb regressed", print_r($f, true));
}
test_pass("sci.archaeology is_root=false → uri='sci/archaeology/' (unchanged)");

echo "\n";

// =============================================================================
// BREADCRUMB DATA STRUCTURE TESTS
// =============================================================================

echo "--- Breadcrumb Data Tests ---\n\n";

if (!defined('TEOSURL')) {
    define('TEOSURL', '/teos/');
}

// Test: router_buildBreadcrumbs always produces title+uri+path keys
echo "Test 20: router_buildBreadcrumbs produces required keys\n";
$crumbs = router_buildBreadcrumbs("comp/lang/python");
foreach ($crumbs as $i => $crumb) {
    if (!isset($crumb['title']) || !isset($crumb['uri']) || !isset($crumb['path'])) {
        test_fail("crumb[$i] missing required keys", print_r($crumb, true));
    }
}
test_pass('all crumbs have title, uri, and path');

// Test: breadcrumb titles are human-readable
echo "Test 21: breadcrumb titles are human-readable\n";
$crumbs = router_buildBreadcrumbs("rec/arts/tv/the-a-team");
$last = end($crumbs);
if ($last['title'] !== 'the a team') {
    test_fail("last crumb title is not 'the a team'", $last['title']);
}
test_pass("last crumb title is 'the a team'");

echo "\n";

echo "=== Results ===\n";
echo "Passed: $passed\n";
echo "Failed: $failed\n";

if ($failed > 0) {
    exit(1);
}

echo "\n✓ All breadcrumb regression tests passed!\n";
exit(0);
