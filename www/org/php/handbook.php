<?php
/**
 * handbook.php - Handbook handler for bbsengine.org /handbook/<v>/<path>
 *
 * Routes a request like https://bbsengine.org/handbook/<v>/specs/architecture
 * to the right `.md` file under HANDBOOKDIR/<v>/ and renders it with the
 * shared \bbsengine6\markdown primitive (ParsedownExtra, setMarkupEscaped,
 * setSafeMode). Replaces the legacy \Michaelf\Markdown-driven .txt reader.
 *
 * No DB blurb row is required: the filesystem is the source of truth
 * (matches the per-decision "filesystem fallback" mode for this sub-target).
 */

require_once("/srv/www/bbsengine6/php/bootstrap.php");
\bbsengine6\bootstrap();
require_once("config.php");
require_once("engine.php");
require_once("markdown.php");

class handbook
{
    private function handbookDir(string $version): string
    {
        $base = \config\HANDBOOKDIR . $version . "/";
        $resolved = realpath($base);
        if ($resolved === false) {
            return $base;
        }
        return rtrim($resolved, "/") . "/";
    }

    public function displayindex(): void
    {
        $version = $_REQUEST["version"] ?? "6";
        $handbookdir = $this->handbookDir($version);

        $files = glob($handbookdir . "*.md");
        $chapters = [];
        if (is_array($files)) {
            foreach ($files as $f) {
                $chapters[] = [
                    "file" => $f,
                    "datemodifiedepoch" => filemtime($f),
                ];
            }
        }

        $data = [
            "chapters"     => $chapters,
            "version"      => $version,
            "title"        => "bbsengine " . $version . " handbook",
            "pagetemplate" => "handbook-index.tmpl",
        ];
        \bbsengine6\displaypage($data, "handbook-index.tmpl", false);
    }

    public function displaychapter(): void
    {
        $version = $_REQUEST["version"] ?? "6";
        $uri     = $_REQUEST["uri"]     ?? "";
        $handbookdir = $this->handbookDir($version);

        $segments = array_values(array_filter(explode("/", trim($uri, "/"))));
        if (empty($segments)) {
            $this->displayindex();
            return;
        }
        $relpath = implode("/", $segments);

        // Path-traversal guard: ensure the requested .md file resolves
        // inside the handbook tree for this version.
        $candidate = $handbookdir . $relpath . ".md";
        if (!preg_match('#^[a-zA-Z0-9_./-]+$#', $relpath)) {
            \bbsengine6\displayerrorpage("Bad request (handbook)", 400);
            return;
        }
        $filepath = realpath($candidate);
        $realdir  = realpath($handbookdir);
        if ($filepath === false || $realdir === false
            || strpos($filepath, $realdir . DIRECTORY_SEPARATOR) !== 0) {
            \bbsengine6\displayerrorpage("File Not Found (handbook)", 404);
            return;
        }
        if (!is_file($filepath)) {
            \bbsengine6\displayerrorpage("File Not Found (handbook)", 404);
            return;
        }

        $content = file_get_contents($filepath);
        if ($content === false) {
            \bbsengine6\displayerrorpage("Read failure (handbook)", 500);
            return;
        }

        $parsed = \bbsengine6\markdown\parseDocument($content, split: false, breaks: false);
        $doc = $parsed["doc"];

        // Title priority: frontmatter `title:` > URI-segment-derived name.
        $title = $doc["title"] ?? str_replace(["-", "_"], " ", basename($relpath));

        $data = [
            "title"        => $title,
            "html"         => $doc["html"],
            "version"      => $version,
            "filename"     => basename($filepath),
            "pagetemplate" => "handbook-chapter.tmpl",
        ];
        \bbsengine6\displaypage($data, "handbook-chapter.tmpl", false);
    }

    public function main(): void
    {
        \bbsengine6\session\start();
        $mode = $_REQUEST["mode"] ?? null;
        switch ($mode) {
            case "chapter":
                $this->displaychapter();
                break;
            case "index":
            default:
                $this->displayindex();
                break;
        }
    }
}

$h = new handbook();
$h->main();
