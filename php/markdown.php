<?php
/**
 * markdown.php - Shared Markdown rendering primitives
 *
 * Single home for the ParsedownExtra parser configuration and the
 * frontmatter/heading-section parsing that used to be duplicated
 * across:
 *   - php/blurb.php::parseMarkdownSections()
 *   - engine/router.php::router_displayMarkdownFile()
 *   - smarty/modifier.parsedown.php
 *
 * Security settings (setMarkupEscaped + setSafeMode) are frozen in
 * the one place so future callers don't accidentally render with a
 * laxer configuration.
 */

namespace bbsengine6\markdown {

require_once("Parsedown.php");
require_once("ParsedownExtra.php");

/**
 * Parse YAML frontmatter ("---\nkey: value\n---\n") at the start of a
 * Markdown document.
 *
 * Returns [$metadata, $body] where $metadata is an array of (key => string)
 * pairs and $body is the post-frontmatter content.
 */
function splitFrontmatter(string $markdown): array
{
    $metadata = [];
    $body = $markdown;

    if (preg_match('/^---\s*\n(.*?)\n---\s*\n/s', $markdown, $m)) {
        foreach (explode("\n", $m[1]) as $line) {
            if (preg_match('/^(\w+):\s*(.*)$/', $line, $kv)) {
                $metadata[trim($kv[1])] = trim($kv[2], "\"' ");
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

}