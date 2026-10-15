<?php
/**
 * test_blurb.php - Tests for blurb handler functions
 * 
 * Usage:
 *   php test_blurb.php           # Run mock tests
 *   php test_blurb.php --db       # Run database integration tests
 */

require_once("/home/opencode/data/work/bbsengine6/php/bootstrap.php");

$run_db = in_array("--db", $argv);

echo "=== Testing blurb functions ===\n\n";

// =============================================================================
// MOCK TESTS (no database)
// =============================================================================

echo "--- Mock Tests ---\n\n";

// Test 1: URI to blurbID conversion
echo "Test 1: URI to blurbID conversion\n";
$uri = "ec/john-edward";
$expected = "ec.john-edward";
$actual = str_replace("/", ".", preg_replace('/\.md$/', '', $uri));
if ($actual === $expected) {
    echo "  ✓ PASS: ec/john-edward → ec.john-edward\n";
} else {
    echo "  ✗ FAIL: expected '$expected', got '$actual'\n";
    exit(1);
}

// Test 2: Strips .md extension
echo "Test 2: Strip .md extension\n";
$uri = "ec/john-edward.md";
$expected = "ec/john-edward";
$actual = preg_replace('/\.md$/', '', $uri);
if ($actual === $expected) {
    echo "  ✓ PASS: ec/john-edward.md → ec/john-edward\n";
} else {
    echo "  ✗ FAIL: expected '$expected', got '$actual'\n";
    exit(1);
}

// Test 3: Full blurbID generation from filepath
echo "Test 3: Full blurbID generation from filepath\n";
$filepath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/ec/john-edward.md";
$teospath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/";
$relative = str_replace($teospath, "", $filepath);
$blurbid = preg_replace('/\.md$/', '', $relative);
$blurbid = str_replace("/", ".", $blurbid);
if ($blurbid === "ec.john-edward") {
    echo "  ✓ PASS: /srv/www/vhosts/zoidtechnologies.com/html/teos/ec/john-edward.md → ec.john-edward\n";
} else {
    echo "  ✗ FAIL: expected 'ec.john-edward', got '$blurbid'\n";
    exit(1);
}

// Test 4: Nested path conversion
echo "Test 4: Nested path conversion\n";
$filepath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/comp/lang/python/intro.md";
$teospath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/";
$relative = str_replace($teospath, "", $filepath);
$blurbid = preg_replace('/\.md$/', '', $relative);
$blurbid = str_replace("/", ".", $blurbid);
if ($blurbid === "comp.lang.python.intro") {
    echo "  ✓ PASS: Nested path converts correctly\n";
} else {
    echo "  ✗ FAIL: expected 'comp.lang.python.intro', got '$blurbid'\n";
    exit(1);
}

// Test 5: Root-level file
echo "Test 5: Root-level file\n";
$filepath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/about.md";
$teospath = "/srv/www/vhosts/zoidtechnologies.com/html/teos/";
$relative = str_replace($teospath, "", $filepath);
$blurbid = preg_replace('/\.md$/', '', $relative);
$blurbid = str_replace("/", ".", $blurbid);
if ($blurbid === "about") {
    echo "  ✓ PASS: Root-level file converts correctly\n";
} else {
    echo "  ✗ FAIL: expected 'about', got '$blurbid'\n";
    exit(1);
}

echo "\n";

// =============================================================================
// FRONTMATTER PARSING TESTS (added 2026-10-15)
// =============================================================================

echo "--- Frontmatter Parsing Tests ---\n\n";

// @since 2026-10-15 — `parseMarkdownSections()` now returns the
// parsed frontmatter under a `frontmatter` key (in addition to
// the legacy `title` and `sections` keys). These tests pin that
// contract: the new field is populated from a `---\n...\n---`
// block, and missing/non-frontmatter inputs return an empty
// array. The downstream `lastmodified` logic in
// `bbsengine6\blurb\display()` reads from this `frontmatter`
// key directly; if a future refactor drops the `frontmatter`
// key, the blurb page will silently fall back to filemtime
// instead of the deploy-managed timestamp.
//
// We exercise the contract via the lower-level
// \bbsengine6\markdown\parseDocument() directly so these
// mock-mode tests do not require the full engine.php include
// chain (which has third-party HTML_QuickForm2 deps not present
// in the test environment).

// Test: parseDocument includes `doc` key with parsed
// frontmatter key/value pairs captured. blurb.php's
// parseMarkdownSections() wraps this and re-exports it under
// the `frontmatter` key, so a contract break at either layer
// surfaces in a downstream refactor.
require_once("/home/opencode/data/work/bbsengine6/php/markdown.php");

echo "Test 5a: parseDocument returns parsed frontmatter (markdown layer)\n";
$markdown = "---\nfolder-path: rec/arts/sci-fi/\nlastmodified: 2026-10-15 04:05:15 GMT (00:05:15 NYC)\n---\n\n# Title\n\nBody.\n";
$doc = \bbsengine6\markdown\parseDocument($markdown, split: true);
if (is_array($doc) && isset($doc["doc"]) && is_array($doc["doc"])) {
    if (($doc["doc"]["folder-path"] ?? null) === "rec/arts/sci-fi/" &&
        ($doc["doc"]["lastmodified"] ?? null) === "2026-10-15 04:05:15 GMT (00:05:15 NYC)") {
        echo "  ✓ PASS: frontmatter key/value pairs captured\n";
    } else {
        echo "  ✗ FAIL: frontmatter missing expected keys: " . var_export($doc["doc"], true) . "\n";
        exit(1);
    }
} else {
    echo "  ✗ FAIL: parseDocument did not return a 'doc' key\n";
    exit(1);
}

echo "Test 5b: parseDocument returns doc array (possibly with title from split) for input without frontmatter\n";
// When there's no `---\n...\n---` block, splitFrontmatter returns
// an empty metadata array, then parseDocument in split=true mode
// re-assigns $doc["title"] from the first H1 of the rendered
// HTML. So the doc array is non-empty (just has a title) but
// the original frontmatter keys (folder-path, lastmodified, etc.)
// are absent. This is the contract blurb.php::display() relies
// on for the `lastmodified` display fallback to filemtime.
$doc = \bbsengine6\markdown\parseDocument("# Just a title\n\nNo frontmatter here.\n", split: true);
if (is_array($doc) && isset($doc["doc"]) && is_array($doc["doc"])) {
    if (!isset($doc["doc"]["folder-path"]) && !isset($doc["doc"]["lastmodified"])) {
        echo "  ✓ PASS: no-frontmatter input has no lastmodified key (filemtime fallback will apply)\n";
    } else {
        echo "  ✗ FAIL: unexpected frontmatter keys: " . var_export($doc["doc"], true) . "\n";
        exit(1);
    }
} else {
    echo "  ✗ FAIL: parseDocument did not return a 'doc' key\n";
    exit(1);
}

echo "Test 5c: parseDocument reads legacy `date:` key as create date\n";
// The `date:` key is the legacy create-date field per the
// 2026-10-15 frontmatter contract change. It should be surfaced
// in the parsed frontmatter under the `date` key (the read
// fallback is for the create date; the `lastmodified` display
// does not use it).
$doc = \bbsengine6\markdown\parseDocument("---\nfolder-path: rec/\ndate: 2026-10-15 03:00:00 GMT (23:00:00 NYC)\n---\n\n# Title\n", split: true);
if (is_array($doc) && ($doc["doc"]["date"] ?? null) === "2026-10-15 03:00:00 GMT (23:00:00 NYC)") {
    echo "  ✓ PASS: legacy `date:` key surfaces in frontmatter\n";
} else {
    echo "  ✗ FAIL: expected 'date' key, got " . var_export($doc["doc"] ?? null, true) . "\n";
    exit(1);
}

echo "Test 5d: strtotime parses the new `lastmodified` format (after stripping parenthetical TZ)\n";
// The frontmatter timestamp format is
// `YYYY-MM-DD HH:MM:SS GMT (HH:MM:NN TZ)`. PHP's strtotime
// cannot parse the parenthetical TZ suffix; blurb.php::display()
// strips everything from the first ` (` onward before
// handing the string to strtotime. This test pins that
// strip-and-parse flow.
$stamp = "2026-10-15 04:05:15 GMT (00:05:15 NYC)";
$gmStamp = preg_replace('/\s*\(.*\)\s*$/', '', $stamp);
$epoch = strtotime($gmStamp);
if (is_int($epoch) && $epoch > 0) {
    $expected = gmmktime(4, 5, 15, 10, 15, 2026);
    if ($epoch === $expected) {
        echo "  ✓ PASS: stripped '$stamp' to '$gmStamp' → epoch $epoch (= gmmktime 2026-10-15 04:05:15 UTC)\n";
    } else {
        echo "  ✗ FAIL: epoch $epoch != expected gmmktime $expected\n";
        exit(1);
    }
} else {
    echo "  ✗ FAIL: strtotime could not parse '$gmStamp'\n";
    exit(1);
}

echo "\n";

// =============================================================================
// DATABASE INTEGRATION TESTS
// =============================================================================

if ($run_db) {
    echo "--- Database Integration Tests ---\n\n";
    
    // Set up test database
    define("SYSTEMDSN", "pgsql:host=127.0.0.1;port=5432;dbname=zoid6test");
    
    require_once("/home/opencode/data/work/bbsengine6/php/database.php");
    require_once("/home/opencode/data/work/bbsengine6/php/blurb.php");
    
    // Test 1: isBlurb returns true for existing blurb
    echo "Test 6: isBlurb returns true for existing blurb\n";
    $result = \bbsengine6\blurb\isBlurb("ec.biblical-prophets-mediumship-prophecy");
    if ($result === true) {
        echo "  ✓ PASS: isBlurb('ec.biblical-prophets-mediumship-prophecy') = true\n";
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        exit(1);
    }
    
    // Test 2: isBlurb returns false for non-existing blurb
    echo "Test 7: isBlurb returns false for non-existing blurb\n";
    $result = \bbsengine6\blurb\isBlurb("nonexistent.blah");
    if ($result === false) {
        echo "  ✓ PASS: isBlurb('nonexistent.blah') = false\n";
    } else {
        echo "  ✗ FAIL: expected false, got " . var_export($result, true) . "\n";
        exit(1);
    }
    
    // Test 3: isBlurb handles .md suffix
    echo "Test 8: isBlurb handles .md suffix\n";
    $result = \bbsengine6\blurb\isBlurb("ec.biblical-prophets-mediumship-prophecy.md");
    if ($result === true) {
        echo "  ✓ PASS: isBlurb handles .md suffix\n";
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        exit(1);
    }
    
    // Test 4: isBlurb with nested path
    echo "Test 9: isBlurb with nested path\n";
    // Create a nested path blurb for testing (using existing member)
    $pdo = \bbsengine6\database\connect(SYSTEMDSN);
    $pdo->exec("INSERT INTO engine.__blurb (id, kind, attributes, contentfilename, datecreated, createdbymoniker) 
                VALUES ('comp.lang.python', 'markdown', '{\"title\": \"Python\"}', 'comp/lang/python.md', NOW(), 'jam') 
                ON CONFLICT (id) DO NOTHING");
    
    $result = \bbsengine6\blurb\isBlurb("comp.lang.python");
    if ($result === true) {
        echo "  ✓ PASS: isBlurb('comp.lang.python') = true\n";
    } else {
        echo "  ✗ FAIL: expected true, got " . var_export($result, true) . "\n";
        exit(1);
    }
    
    echo "\n";
}

echo "=== All tests passed! ===\n";
