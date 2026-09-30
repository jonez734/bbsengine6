<?php
/**
 * markdown.php - Shared Markdown handling primitives
 *
 * Single home for everything related to .md files:
 *
 *   Render half (markdown text -> HTML):
 *     - splitFrontmatter()    YAML frontmatter parse
 *     - renderHtml()          ParsedownExtra render with frozen security
 *                             settings (setMarkupEscaped + setSafeMode).
 *                             Future callers must NOT bypass these.
 *     - splitHtmlSections()   split rendered HTML on <h1> boundaries
 *     - parseDocument()       splitFrontmatter + renderHtml + optional
 *                             splitHtmlSections pipeline
 *
 *   Stream half (filesystem -> raw .md bytes over HTTP):
 *     - serveRawMarkdown(string $basedir, string $relpath): bool
 *                             Generic realpath-based basedir containment
 *                             + .md-only + is_file; emits
 *                             `Content-Type: text/plain; charset=utf-8`
 *                             and readfile()s the body on hit. Used by
 *                             router_handleRawMarkdown (engine/router.php)
 *                             for all vhosts (handbook and non-handbook)
 *                             via env("TEOSDIR"). On the handbook vhost
 *                             htaccess-prod's SetEnv TEOSDIR points at
 *                             /srv/www/vhosts/www.bbsengine.org/html/handbook/<v>/
 *                             so <TEOSDIR>/<uri>.md resolves to the right
 *                             file; the htaccess RewriteRule forwards
 *                             /handbook/<v>/<uri>.md to engine/router.php
 *                             which dispatches via the rawmarkdown handler
 *                             matching /\.md$/.
 *
 * Previously these were split across:
 *   - php/markdown.php       (render half)
 *   - php/serve-md.php       (stream half; library-only since 2026-09-29;
 *                             merged here on 2026-10-XX)
 *   - engine/serve-md.php    (handbook-vhost entry-point wrapper; deleted
 *                             when the htaccess rewrite target moved to
 *                             engine/router.php, since the router's
 *                             rawmarkdown handler is vhost-agnostic and
 *                             covers the handbook case via TEOSDIR)
 *
 * Side-effect-free on require_once: no namespace {} entry-point guard.
 * The merged refactor on 2026-10-XX dropped the engine/serve-md.php
 * shim, so there is no SCRIPT_NAME-driven entry-point to guard against;
 * callers explicitly invoke \bbsengine6\markdown\serveRawMarkdown()
 * (e.g. router_handleRawMarkdown in engine/router.php).
 */

namespace bbsengine6\markdown {

// Parsedown / ParsedownExtra are lazy-loaded inside renderHtml() so
// require_once'ing this file from contexts where include_path may
// not yet be primed for vendor/ does not fatal.

/**
 * Parse YAML frontmatter ("---\nkey: value\n---\n") at the start of a
 * Markdown document.
 *
 * Returns [$metadata, $body] where $metadata is an array of (key => string)
 * pairs and $body is the post-frontmatter content.
 *
 * @since 2026-09-27 — closing delimiter accepts trailing
 * whitespace + EOF as well as whitespace + newline. Prior regex
 * (`\n---\s*\n`) required a literal newline after the closing
 * `---`, which rejected files where the frontmatter block ends
 * the file without a trailing newline (`---\ntitle: foo\n---`).
 * The new alternation `(?:\s*\n|\s*$)` accepts that case while
 * remaining backwards-compatible with every input the previous
 * regex accepted. Also strip `\r` from per-line values so CRLF
 * input (`---\r\ntitle: foo\r\n---\r\nbody`) does not leak a
 * trailing carriage return into rendered titles.
 */
function splitFrontmatter(string $markdown): array
{
    $metadata = [];
    $body = $markdown;

    if (preg_match('/^---\s*\n(.*?)\n---(?:\s*\n|\s*$)/s', $markdown, $m)) {
        foreach (explode("\n", $m[1]) as $line) {
            if (preg_match('/^(\w+):\s*(.*)$/', $line, $kv)) {
                $metadata[trim($kv[1])] = trim($kv[2], "\"' \r");
            }
        }
        $body = substr($markdown, strlen($m[0]));
    }

    return [$metadata, $body];
}

/**
 * Render Markdown to HTML with the shared ParsedownExtra parser.
 *
 * @param string $body   Post-frontmatter Markdown body.
 * @param bool   $breaks Whether single line breaks translate to <br>
 *                       (router.php historically enabled this; blurb.php
 *                       and modifier.parsedown.php did not).
 */
function renderHtml(string $body, bool $breaks = false): string
{
    static $parser = null;
    if ($parser === null) {
        if (!class_exists('ParsedownExtra', false)) {
            require_once("Parsedown.php");
            require_once("ParsedownExtra.php");
        }
        $parser = new \ParsedownExtra();
        $parser->setMarkupEscaped(true);
        $parser->setSafeMode(true);
    }
    $parser->setBreaksEnabled($breaks);
    return $parser->text($body);
}

/**
 * Split rendered HTML on <h1>...</h1> boundaries into sections.
 * Text before the first <h1> becomes its own section.
 *
 * Returns ['title' => string, 'sections' => [['header','content'], ...]].
 */
function splitHtmlSections(string $html, string $fallbackTitle = ""): array
{
    $title = $fallbackTitle;
    $sections = [];

    $parts = preg_split('/(<h1>.*?<\/h1>)/i', $html, -1, PREG_SPLIT_DELIM_CAPTURE);

    $firstPart = true;
    foreach ($parts as $part) {
        if (preg_match('/<h1>(.*?)<\/h1>/i', $part, $m)) {
            $headerText = strip_tags($m[1]);
            if ($firstPart && $title === "") {
                $title = $headerText;
            }
            $sections[] = ["header" => $headerText, "content" => ""];
            $firstPart = false;
        } elseif (!empty($part) && !empty($sections)) {
            $sections[count($sections) - 1]["content"] .= $part;
        }
    }

    if (empty($sections)) {
        $sections[] = ["header" => $title, "content" => $html];
    }

    return ["title" => $title, "sections" => $sections];
}

/**
 * Full-pipeline convenience: split frontmatter, render Markdown, and
 * optionally split into h1 sections.
 *
 * @param bool $split  When true, returns ['sections' => ...] and derives
 *                     'title' from the first h1 unless frontmatter set it.
 *                     When false, returns ['sections' => null] and the
 *                     rendered HTML in 'doc.html'.
 *
 * @return array{doc: array<int|string,string>, sections: ?array}
 */
function parseDocument(string $markdown, bool $split = false, bool $breaks = false): array
{
    [$doc, $body] = splitFrontmatter($markdown);
    $html = renderHtml($body, $breaks);

    if ($split) {
        $sections = splitHtmlSections($html, $doc["title"] ?? "");
        $doc["title"] = $sections["title"];
        return ["doc" => $doc, "sections" => $sections["sections"]];
    }

    $doc["html"] = $html;
    return ["doc" => $doc, "sections" => null];
}

/**
 * Stream a .md file under $basedir as text/plain markdown.
 *
 * @param string $basedir Absolute base directory (e.g.
 *                        \bbsengine6\util\env("TEOSDIR") for the teos
 *                        vhost).
 * @param string $relpath  Path relative to $basedir; must end in .md
 *                        and resolve to a regular file inside $basedir.
 * @return bool true on success (headers + body sent), false on any
 *              validation failure (caller emits the 404).
 */
function serveRawMarkdown(string $basedir, string $relpath): bool
{
    $realbasedir = realpath($basedir);
    if ($realbasedir === false) {
        return false;
    }
    $realbasedir = rtrim($realbasedir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR;

    $candidate = $realbasedir . $relpath;
    $realfile  = realpath($candidate);

    if ($realfile === false
        || strpos($realfile, $realbasedir) !== 0
        || !is_file($realfile)
        || pathinfo($realfile, PATHINFO_EXTENSION) !== 'md') {
        return false;
    }

    header('Content-Type: text/plain; charset=utf-8');
    readfile($realfile);
    return true;
}

}
?>