<?php
/**
 * handbook.php - Handbook handler for bbsengine.org /handbook/<v>/<path>
 *
 * Routes requests like https://bbsengine.org/handbook/<v>/<path> to:
 *   - a single chapter's rendered HTML, when <path>.md exists;
 *   - a directory-style chapter list scoped to <path>/, when
 *     HANDBOOKDIR/<v>/<path>/ exists as a subdirectory;
 *   - the root chapter list, when <path> is empty or just "/";
 *   - the raw .md source as text/plain, when the .htaccess rewrites
 *     /handbook/<v>/<path>.md to ?rawpath=<path>.md (see commit
 *     feat(handbook): collapse .htaccess rules).
 *
 * Mirrors the teos engine router's pattern (engine/router.php):
 * one entry point, a dispatcher that classifies the URI, and a
 * per-classification render path. Replaces the prior `?mode=`
 * switch and the "always append .md" assumption that broke
 * directory URLs (e.g. /handbook/6/specs/).
 *
 * No DB blurb row is required: the filesystem is the source of
 * truth (matches the per-decision "filesystem fallback" mode for
 * this sub-target).
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

    /**
     * Classify the request URI into a render mode.
     *
     * Returns one of:
     *   - 'index'    : root chapter list (URI is empty or trailing-slash).
     *   - 'chapter'  : URI maps to a regular .md file inside the handbook tree.
     *   - 'directory': URI maps to a subdirectory of the handbook tree (chapter list scoped to it).
     *   - 'error'    : URI maps to neither a .md file nor a directory inside the tree.
     *
     * Path-traversal guard: both 'chapter' and 'directory' resolutions
     * require realpath($candidate) to live under realpath(handbookDir).
     */
    private function dispatch(string $version, string $uri): string
    {
        $handbookdir = $this->handbookDir($version);
        $realdir     = realpath($handbookdir);

        // Empty URI or trailing-slash URI -> index.
        if ($uri === "" || substr($uri, -1) === "/") {
            return "index";
        }

        // Restrict URI characters to the safe alphabet. Mirrors the
        // legacy guard from displaychapter (commit cfb9b76).
        if (!preg_match('#^[a-zA-Z0-9_./-]+$#', $uri)) {
            return "error";
        }

        $realbasedir = ($realdir === false) ? false : (rtrim($realdir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR);

        // Try as a .md file first.
        $candidatemd = $handbookdir . $uri . ".md";
        $realfilemd  = realpath($candidatemd);
        if ($realfilemd !== false
            && $realbasedir !== false
            && strpos($realfilemd, $realbasedir) === 0
            && is_file($realfilemd)) {
            return "chapter";
        }

        // Then as a directory.
        $candidatedir = $handbookdir . $uri . "/";
        $realdircheck = realpath($candidatedir);
        if ($realdircheck !== false
            && $realbasedir !== false
            && strpos($realdircheck, $realbasedir) === 0
            && is_dir($realdircheck)) {
            return "directory";
        }

        return "error";
    }

    /**
     * Render the chapter list. When $scope is non-empty, list
     * *.md files inside HANDBOOKDIR/<v>/<scope>/ instead of the
     * root. Used by both 'index' (root) and 'directory' (scoped)
     * dispatch outcomes -- same template, different glob.
     */
    public function displayindex(string $scope = ""): void
    {
        $version     = $_REQUEST["version"] ?? "6";
        $handbookdir = $this->handbookDir($version);
        $scoped      = $handbookdir . $scope;
        $files       = glob($scoped . "*.md");

        $chapters = [];
        if (is_array($files)) {
            foreach ($files as $f) {
                $chapters[] = [
                    "file"              => $f,
                    "datemodifiedepoch" => filemtime($f),
                ];
            }
        }

        $data = [
            "chapters"     => $chapters,
            "version"      => $version,
            "scope"        => $scope,
            "title"        => "bbsengine " . $version . " handbook",
            "pagetemplate" => "handbook-index.tmpl",
        ];
        \bbsengine6\displaypage($data, "handbook-index.tmpl", false);
    }

    public function displaychapter(string $relpath): void
    {
        $version     = $_REQUEST["version"] ?? "6";
        $handbookdir = $this->handbookDir($version);
        $realdir     = realpath($handbookdir);
        $realbasedir = ($realdir === false) ? false : (rtrim($realdir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR);

        $filepath = realpath($handbookdir . $relpath . ".md");
        if ($filepath === false
            || $realbasedir === false
            || strpos($filepath, $realbasedir) !== 0
            || !is_file($filepath)) {
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
        $version = $_REQUEST["version"] ?? "6";

        // Raw .md URL: stream the file as text/plain. Runs before the
        // dispatch so .md requests never accidentally land in the HTML
        // rendering path.
        if (isset($_REQUEST["rawpath"])) {
            $basedir = \config\HANDBOOKDIR . $version . "/";
            if (\bbsengine6\serveRawMarkdown($basedir, $_REQUEST["rawpath"])) {
                return;
            }
            http_response_code(404);
            echo "File not found\n";
            return;
        }

        $uri = $_REQUEST["uri"] ?? "";
        switch ($this->dispatch($version, $uri)) {
            case "chapter":
                $this->displaychapter($uri);
                break;
            case "directory":
                $this->displayindex($uri . "/");
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
