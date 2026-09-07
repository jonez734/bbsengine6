<?php
/**
 * handbook.php - Handbook handler for bbsengine.org /handbook/<v>/<path>
 *
 * Delegates URI classification and rendering to engine/router.php so
 * the handbook vhost shares a single dispatcher with teos/www. The only
 * handbook-specific behavior kept here is:
 *   - resolving HANDBOOKDIR/<v>/ to a real base directory (the router
 *     already reads TEOSDIR via getenv());
 *   - exposing the ?rawpath= stream-as-text/plain branch, which the
 *     router's chapter handler doesn't (routing is to render, not
 *     raw dump);
 *   - the chapter/directory path-traversal guard (defence in depth on
 *     top of bbsengine6\util\safe_path_web inside the router).
 *
 * Routes requests like https://bbsengine.org/handbook/<v>/<path> to:
 *   - a single chapter's rendered HTML, when <path>.md exists;
 *   - a directory-style chapter list scoped to <path>/, when
 *     HANDBOOKDIR/<v>/<path>/ exists as a subdirectory;
 *   - the root chapter list, when <path> is empty or just "/";
 *   - the raw .md source as text/plain, when the .htaccess rewrites
 *     /handbook/<v>/<path>.md to ?rawpath=<path>.md.
 *
 * TEOSDIR is set to the handbook root (containing all versions), and
 * the URI prefix /handbook/ is stripped before forwarding to the
 * router, so the router's handlers can resolve relative paths the
 * same way they do under the teos vhost. TEOSURL is set to
 * /handbook/ -- the router uses it only for breadcrumb/URI display,
 * not for filesystem resolution.
 *
 * No DB blurb row is required: the filesystem is the source of
 * truth (matches the per-decision "filesystem fallback" mode for
 * this sub-target).
 */

require_once("/srv/www/bbsengine6/php/bootstrap.php");
\bbsengine6\bootstrap();
require_once("config.php");
require_once("engine.php");
require_once("session.php");
require_once("markdown.php");
// @since 2026-09-07 — load serveRawMarkdown for the ?rawpath=
// branch. The function is defined in /srv/www/bbsengine6/php/
// (on include_path), so the bare name resolves. Without this
// the rawpath branch (handbook.php:184) raises a fatal
// "Call to undefined function" and produces an empty 500.
require_once("serve-md.php");

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
     * Map a handbook URI to a router-shaped URI and dispatch through
     * engine/router.php. The router's handlers run on URIs whose
     * filesystem join is TEOSDIR + leading-slash URI -- matching the
     * teos vhost where TEOSDIR is the document root and the URI is
     * the public path under it.
     *
     * For the handbook, TEOSDIR is the handbook root (containing all
     * versions) and the URI passed to the router is "/<version>/<rest>"
     * with a trailing slash for directory requests so router_handleFolder
     * keys off is_dir() on safe_path_web.
     */
    private function dispatchViaRouter(string $version, string $uri, string $mode): void
    {
        $handler_uri = "/" . $version . "/" . ltrim($uri, "/");
        if ($mode === "index") {
            $handler_uri = "/" . $version . "/";
        }

        // TEOSDIR points at the handbook root (one level above <v>/).
        // realpath defends against a missing HANDBOOKDIR deployment.
        $handbook_root = \config\HANDBOOKDIR;
        $real_root = realpath($handbook_root);
        $base_dir = ($real_root === false)
            ? rtrim($handbook_root, "/") . "/"
            : rtrim($real_root, "/") . "/";

        // Export base directory and public URL for the router.
        // putenv wins over constants inside router_get_teosurl/dir.
        putenv("TEOSDIR=" . $base_dir);
        putenv("TEOSURL=/handbook/");
        // Per-vhost top-breadcrumb label; consumed by blurb::getlabel().
        // Default for unconfigured environments is "teos".
        putenv("TEOS_LABEL=bbsengine6 handbook");
        if (!defined("TEOSURL")) define("TEOSURL", "/handbook/");
        if (!defined("TEOSDIR"))  define("TEOSDIR",  $base_dir);

        // @since 2026-09-07 — relative require to the vhost's own
        // engine/ sibling. engine/Makefile deploy-engine /
        // deploy ssh-pushes the engine tree straight to
        // $(WWWENGINEPRODDOCROOT) =
        // merlin:/srv/www/vhosts/www.bbsengine.org/html/engine/,
        // so __DIR__ . "/engine/router.php" resolves to that file
        // once `make engine-deploy-prod` has run. The previous
        // bare-name require_once("router.php") depended on the
        // include_path default set by php/bootstrap.php, which
        // pointed at /srv/www/bbsengine6/engine/ — a directory on
        // the prod source tree that the engine deploy never
        // populates (it only ships the tree to the docroots, not
        // to the source tree). When the engine deploy hadn't yet
        // run on a fresh .org html/, the bare-name require raised
        // "Failed opening required 'router.php'" at request time.
        // The relative require makes the data dependency explicit
        // and matches the engine/Makefile deploy target's
        // canonical destination path.
        require_once __DIR__ . "/engine/router.php";

        $result = \router($handler_uri);
        if ($result === null || $result === false) {
            http_response_code(500);
            echo "Router Error";
        } else {
            echo $result;
        }
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

        $uri  = $_REQUEST["uri"] ?? "";
        $mode = $this->dispatch($version, $uri);

        switch ($mode) {
            case "chapter":
            case "directory":
            case "index":
                $this->dispatchViaRouter($version, $uri, $mode);
                break;
            case "error":
            default:
                \bbsengine6\displayerrorpage("File Not Found (handbook)", 404);
                break;
        }
    }
}

$h = new handbook();
$h->main();
