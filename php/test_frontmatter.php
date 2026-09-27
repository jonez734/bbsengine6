<?php
/**
 * test_frontmatter.php - Edge-case tests for \bbsengine6\markdown\splitFrontmatter
 *
 * Pins the behavior of the closing-delimiter regex and per-line
 * value trim, including the 2026-09-27 fix that loosens the
 * closing to accept EOF and strips CRLF \r from values.
 *
 * Run: php test_frontmatter.php
 *
 * Exit code 0 on full pass, 1 on any failure.
 */

error_reporting(E_ALL);
ini_set("display_errors", 1);

set_include_path("/home/opencode/data/work/bbsengine6/vendor/erusev/parsedown:" .
                 "/home/opencode/data/work/bbsengine6/vendor/erusev/parsedown-extra:" .
                 get_include_path());

require_once("/home/opencode/data/work/bbsengine6/php/markdown.php");

$passed = 0;
$failed = 0;

function assert_frontmatter(string $label, string $input, array $wantMeta, string $wantBody): void
{
    global $passed, $failed;
    [$meta, $body] = \bbsengine6\markdown\splitFrontmatter($input);
    if ($meta === $wantMeta && $body === $wantBody) {
        echo "  ✓ PASS: $label\n";
        $passed++;
        return;
    }
    echo "  ✗ FAIL: $label\n";
    echo "    input: " . json_encode($input) . "\n";
    echo "    want:  " . json_encode([$wantMeta, $wantBody]) . "\n";
    echo "    got:   " . json_encode([$meta, $body]) . "\n";
    $failed++;
}

echo "=== splitFrontmatter edge cases ===\n\n";

echo "--- standard parse ---\n";
assert_frontmatter(
    "standard title + body",
    "---\ntitle: foo\n---\nbody",
    ["title" => "foo"],
    "body"
);

echo "\n--- closing delimiter: EOF / trailing whitespace (2026-09-27 fix) ---\n";
assert_frontmatter(
    "closing --- at EOF (no trailing newline)",
    "---\ntitle: foo\n---",
    ["title" => "foo"],
    ""
);
assert_frontmatter(
    "closing --- followed by trailing space, then newline",
    "---\ntitle: foo\n--- \nbody",
    ["title" => "foo"],
    "body"
);
assert_frontmatter(
    "closing --- followed by trailing space, then EOF",
    "---\ntitle: foo\n--- ",
    ["title" => "foo"],
    ""
);
assert_frontmatter(
    "closing --- followed by multiple trailing spaces and newline",
    "---\ntitle: foo\n---   \nbody",
    ["title" => "foo"],
    "body"
);

echo "\n--- --- / ---- embedded in title values ---\n";
assert_frontmatter(
    "title containing literal ' ---'",
    "---\ntitle: foo --- bar\n---\nbody",
    ["title" => "foo --- bar"],
    "body"
);
assert_frontmatter(
    "title ending in ' ----' (four dashes)",
    "---\ntitle: foo ----\n---\nbody",
    ["title" => "foo ----"],
    "body"
);
assert_frontmatter(
    "title containing '---' inside double quotes",
    "---\ntitle: \"Foo --- bar\"\n---\nbody",
    ["title" => "Foo --- bar"],
    "body"
);
assert_frontmatter(
    "title containing '---' inside single quotes",
    "---\ntitle: 'Foo --- bar'\n---\nbody",
    ["title" => "Foo --- bar"],
    "body"
);

echo "\n--- blank line / whitespace before closing ---\n";
assert_frontmatter(
    "blank line between last value and closing ---",
    "---\ntitle: foo\n\n---\nbody",
    ["title" => "foo"],
    "body"
);

echo "\n--- edge cases that must reject frontmatter ---\n";
assert_frontmatter(
    "closing --- followed by non-whitespace garbage",
    "---\ntitle: foo\n---garbage\n",
    [],
    "---\ntitle: foo\n---garbage\n"
);
assert_frontmatter(
    "leading whitespace before opening ---",
    "  ---\ntitle: foo\n---\n",
    [],
    "  ---\ntitle: foo\n---\n"
);
assert_frontmatter(
    "no whitespace between --- and title on opening line",
    "---title: foo\n---\n",
    [],
    "---title: foo\n---\n"
);

echo "\n--- CRLF input (2026-09-27 fix strips \\r from values) ---\n";
assert_frontmatter(
    "CRLF frontmatter strips \\r from value",
    "---\r\ntitle: foo\r\n---\r\nbody",
    ["title" => "foo"],
    "body"
);

echo "\n--- empty / minimal input ---\n";
assert_frontmatter(
    "empty title value",
    "---\ntitle:\n---\nbody",
    ["title" => ""],
    "body"
);
assert_frontmatter(
    "empty input",
    "",
    [],
    ""
);
assert_frontmatter(
    "no frontmatter at all",
    "plain content only",
    [],
    "plain content only"
);

echo "\n--- known limitation: multi-line title without block scalar ---\n";
assert_frontmatter(
    "multi-line 'title:' keeps only first line (line-by-line parser)",
    "---\ntitle: line1\nline2\n---\nbody",
    ["title" => "line1"],
    "body"
);

echo "\n--- multiple --- blocks (only the first is parsed) ---\n";
assert_frontmatter(
    "second --- block in body is left in body verbatim",
    "---\ntitle: foo\n---\n---\nbar\n---\n",
    ["title" => "foo"],
    "---\nbar\n---\n"
);

echo "\n--- comment-only / whitespace-only frontmatter ---\n";
assert_frontmatter(
    "comment-only frontmatter yields no keys",
    "---\n# only a comment\n---\nbody",
    [],
    "body"
);

echo "\n";
echo "====================================\n";
echo "Total: " . ($passed + $failed) . "  Passed: $passed  Failed: $failed\n";
echo "====================================\n";

exit($failed > 0 ? 1 : 0);
