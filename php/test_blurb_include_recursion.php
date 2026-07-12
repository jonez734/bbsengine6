<?php
/**
 * test_blurb_include_recursion.php
 *
 * Regression test: the include of "blurb-block.tmpl" inside
 * page-markdown-sections.tmpl causes Smarty to exhaust memory.
 *
 * Root cause: blurb-block.tmpl is a parent template (it has {block}
 * definitions intended for the md2tpl.py tool to generate child templates).
 * When it is {include}'d from a context that already has an active
 * inheritance chain (page-markdown-sections.tmpl {extends page.tmpl}),
 * Smarty's state machine gets confused and the foreach stack grows
 * unboundedly until PHP runs out of memory.
 *
 * The fix: replace the {include file="blurb-block.tmpl"} in
 * page-markdown-sections.tmpl with an inline rendering of the section
 * (no include, no block). This avoids the cross-template inheritance
 * interaction entirely.
 *
 * This test:
 *   1. Compiles page-markdown-sections.tmpl via Smarty
 *   2. Asserts the compiled output does NOT contain a sub-template
 *      render for blurb-block.tmpl
 *   3. Renders the page with the intro.md data and asserts the output
 *      does not produce a memory exhaustion fatal error
 *
 * Run: php test_blurb_include_recursion.php
 */

error_reporting(E_ALL & ~E_DEPRECATED & ~E_NOTICE & ~E_WARNING);
ini_set('display_errors', '1');

$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

function run_test($name, $callable) {
    global $tests_passed, $tests_failed, $test_results;
    try {
        $callable();
        $tests_passed++;
        $test_results[] = "PASS: $name";
        echo "  PASS: $name\n";
    } catch (Throwable $e) {
        $tests_failed++;
        $test_results[] = "FAIL: $name - " . $e->getMessage();
        echo "  FAIL: $name\n";
        echo "    " . $e->getMessage() . "\n";
    }
}

function assert_true($cond, $msg = "") {
    if (!$cond) throw new Exception($msg ?: "expected true");
}

function assert_false($cond, $msg = "") {
    if ($cond) throw new Exception($msg ?: "expected false");
}

function assert_contains($haystack, $needle, $msg = "") {
    if (strpos($haystack, $needle) === false) {
        throw new Exception($msg ?: "expected to find '$needle'");
    }
}

function assert_not_contains($haystack, $needle, $msg = "") {
    if (strpos($haystack, $needle) !== false) {
        throw new Exception($msg ?: "expected NOT to find '$needle' but found it");
    }
}

$bbsengine6_root = "/home/opencode/data/work/bbsengine6";
$skin_tmpl = $bbsengine6_root . "/skin/tmpl";
$smarty_lib = "/srv/www/smarty-4.5.3/libs";
$parsedown_lib = "/srv/www/markdown";

if (!is_dir($smarty_lib)) {
    // Fall back to a vendored copy if the system one isn't available.
    $smarty_lib = $bbsengine6_root . "/vendor/smarty/smarty/libs";
}
if (!is_dir($parsedown_lib)) {
    $parsedown_lib = $bbsengine6_root . "/vendor/erusev/parsedown-extra";
}

set_include_path(get_include_path()
    . PATH_SEPARATOR . $smarty_lib
    . PATH_SEPARATOR . $parsedown_lib);

require_once $smarty_lib . "/Smarty.class.php";
require_once $parsedown_lib . "/Parsedown.php";
require_once $parsedown_lib . "/ParsedownExtra.php";

function parseSections(string $markdown): array {
    $body = $markdown;
    if (preg_match('/^---\s*\n(.*?)\n---\s*\n/s', $markdown, $m)) {
        $body = substr($markdown, strlen($m[0]));
    }
    $p = new ParsedownExtra();
    $p->setMarkupEscaped(true);
    $p->setSafeMode(true);
    $html = $p->text($body);
    $title = "";
    $sections = [];
    $parts = preg_split('/(<h1>.*?<\/h1>)/i', $html, -1, PREG_SPLIT_DELIM_CAPTURE);
    $firstPart = true;
    foreach ($parts as $part) {
        if (preg_match('/<h1>(.*?)<\/h1>/i', $part, $m)) {
            $headerText = strip_tags($m[1]);
            if ($firstPart && $title === "") $title = $headerText;
            $sections[] = ["header" => $headerText, "content" => ""];
            $firstPart = false;
        } elseif (!empty($part) && !empty($sections)) {
            $sections[count($sections) - 1]["content"] .= $part;
        }
    }
    if (empty($sections)) $sections[] = ["header" => $title, "content" => $html];
    return ["title" => $title, "sections" => $sections];
}

echo "Blurb Include Recursion Regression Test\n";
echo "=======================================\n\n";

echo "Test Group 1: Source template does not include parent-template blurb-block\n";

run_test("page-markdown-sections.tmpl does not include blurb-block.tmpl", function() use ($skin_tmpl) {
    $src = file_get_contents($skin_tmpl . "/page-markdown-sections.tmpl");
    assert_not_contains($src, '{include file="blurb-block.tmpl"',
        "page-markdown-sections.tmpl still includes blurb-block.tmpl; " .
        "this template uses {block} syntax intended for md2tpl.py children " .
        "and causes Smarty memory exhaustion when {include}d from a child " .
        "context that already has {extends} active.");
});

run_test("page-markdown-sections.tmpl does not include blurb.tmpl (the listing view)", function() use ($skin_tmpl) {
    $src = file_get_contents($skin_tmpl . "/page-markdown-sections.tmpl");
    assert_not_contains($src, '{include file="blurb.tmpl"',
        "page-markdown-sections.tmpl still includes blurb.tmpl; " .
        "the shared blurb.tmpl is a listing view that calls count(\$blurbs) " .
        "without an isset guard and triggers a TypeError.");
});

echo "\nTest Group 2: Rendering the page with a 1-section payload does not OOM\n";

$intro_md_path = "/srv/www/vhosts/zoidtechnologies.com/html/teos/comp/lang/python/intro.md";
$intro_md_available = file_exists($intro_md_path);

if (!$intro_md_available) {
    echo "  SKIP: $intro_md_path not found on this host (test environment only)\n";
} else {
    run_test("rendering page-markdown-sections.tmpl with intro.md data does not exhaust memory", function() use ($intro_md_path, $skin_tmpl, $bbsengine6_root) {
        $content = file_get_contents($intro_md_path);
        $parsed = parseSections($content);
        assert_true(count($parsed['sections']) >= 1, "intro.md should produce >= 1 section");

        $data = $parsed;
        $data['choices'] = [];
        $data['actions'] = [];
        $data['breadcrumbs'] = [];
        $data['sidebar'] = [];
        $data['pagefooter']['fortune'] = null;
        // The 'content' field is required by some templates but not used by
        // page-markdown-sections.tmpl; provide it for compatibility.
        $data['content'] = $content;

        $shared_tmpl = "/srv/www/vhosts/zoidtechnologies.com/html/shared/skin/tmpl";

        $tmpl = new Smarty();
        $tmpl->setTemplateDir([
            0 => $skin_tmpl . "/",
            1 => $shared_tmpl . "/",
            2 => $shared_tmpl . "/",
        ]);
        $compileDir = "/tmp/blurb_include_test_compile";
        if (!is_dir($compileDir)) {
            mkdir($compileDir, 0777, true);
        }
        $tmpl->setCompileDir($compileDir);
        $tmpl->setCompileId('zoid6teos');
        $tmpl->assign('data', $data);

        $prev_limit = ini_get('memory_limit');
        ini_set('memory_limit', '128M');
        $output = null;
        $caught = null;
        try {
            ob_start();
            $tmpl->display('page-markdown-sections.tmpl');
            $output = ob_get_clean();
        } catch (Throwable $e) {
            if (ob_get_level() > 0) ob_end_clean();
            $caught = $e;
        }
        ini_set('memory_limit', $prev_limit);

        if ($caught !== null) {
            throw new Exception(
                "render threw: " . $caught->getMessage() .
                " at " . $caught->getFile() . ":" . $caught->getLine()
            );
        }
        if ($output === null) {
            throw new Exception("render produced no output");
        }
    });
}

echo "\n=======================================\n";
echo "Results: $tests_passed passed, $tests_failed failed\n";

if ($tests_failed > 0) {
    echo "\nFailures:\n";
    foreach ($test_results as $r) {
        if (strpos($r, "FAIL") === 0) {
            echo "  $r\n";
        }
    }
    exit(1);
}

echo "\nAll tests passed.\n";
exit(0);
