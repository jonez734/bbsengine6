<?php
/**
 * blurb.php - Blurb handler functions
 *
 * Provides functions to check if a URI is a blurb and render blurbs
 * with database metadata and markdown content
 */

namespace bbsengine6\blurb {

require_once("engine.php");
// require_once("database.php");

/**
 * Get the display label for the top-level "root" breadcrumb.
 *
 * @since 2026-09-30 — switched from the legacy TEOS_LABEL
 * (underscore) env name to the canonical TEOSLABEL env name.
 * The two were renamed in commit 45b0b71 ("chore(bbsengine6):
 * router/util/htaccess-prod tweaks") along with engine/router.php
 * and bbsengine6\util\vhost_label(); blurb.php's getlabel() was
 * missed in that rename and the vhost_label() delegation added
 * by c11acff was later reverted in 22bd02ba. The result: blurb
 * pages on the .org vhost rendered the literal "teos" for the
 * root crumb because the live htaccess-prod publishes
 * `SetEnv TEOSLABEL bbsengine` (bbsengine6/www/org/htaccess-prod:5)
 * and `getenv(TEOS_LABEL)` returned false (note: the legacy name
 * used an underscore; the canonical contract is the no-underscore
 * form). engine/router.php already reads TEOSLABEL via
 * \bbsengine6\util\env() (line 192), so the routers's
 * filesystem-fallback path was correct; only the DB-driven path
 * through bbsengine6\blurb\buildbreadcrumbs() (line 73) was broken.
 *
 * Resolution is now routed through \bbsengine6\util\env() with
 * the same NEEDINFO sentinel default used by engine/router.php
 * and bbsengine6\util\vhost_label(), so a missing env var is
 * greppable in production logs instead of silently rendering
 * the literal "teos". Each vhost's htaccess-prod declares its
 * own TEOSLABEL via SetEnv (the .org handbook vhost sets
 * "bbsengine"), mirroring the TEOSDIR/TEOSURL pattern.
 *
 * @return string The label to render for the top breadcrumb.
 */
function getlabel(): string
{
    $v = \bbsengine6\util\env('TEOSLABEL', 'NEEDINFO:getlabel.100');
    if (is_string($v) && $v !== '') {
        return $v;
    }
    return 'NEEDINFO:getlabel.100';
}

/**
 * Build breadcrumbs from a sig path
 *
 * @param string $sigpath The sig path (e.g., "ec_john-edward")
 * @param bool $skiptop Skip the "top" sig in breadcrumbs
 * @param string|null $hidepath Optional path to hide from breadcrumbs
 * @return array Array of breadcrumb sig records
 */
function buildbreadcrumbs($sigpath, $skiptop = true, $hidepath = null)
{
    try {
        $sigpath = \bbsengine6\util\pathToLtree($sigpath);
        $dbh = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = \bbsengine6\database\query($dbh, 'SELECT title, path, uri FROM $engine.sig WHERE path @> :sigpath ORDER BY path ASC', [":sigpath" => $sigpath]);
        if ($stmt === false || $stmt->rowCount() == 0) {
            return [];
        }
        $res = $stmt->fetchAll();

        $crumbs = [];
        foreach ($res as $sig) {
            if ($skiptop === true && $sig["path"] === "top") {
                continue;
            }
            if (is_string($hidepath) === true && $sig["path"] === $hidepath) {
                continue;
            }

            $crumbs[] = $sig;
        }

        // Prepend "root" crumb. Title is per-vhost via TEOSLABEL
        // (see getlabel() above); path stays "teos" as the internal
        // identifier; uri follows TEOSURL so it points at the
        // correct vhost root.
        $teosurl = defined('TEOSURL') ? TEOSURL : '';
        array_unshift($crumbs, [
            'title' => getlabel(),
            'path' => 'teos',
            'uri' => rtrim($teosurl, '/') . '/',
        ]);

        return $crumbs;
    } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("blurb.buildbreadcrumbs.100: " . $e->getMessage());
        return [];
    }
}

/**
 * Build breadcrumb list from a blurb ID
 *
 * @param int $blurbid The blurb ID
 * @return array Array of breadcrumb arrays
 */
function buildbreadcrumblist($blurbid)
{
    try {
        $dbh = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = \bbsengine6\database\query($dbh, 'SELECT unnest(sigs) as path, title FROM $engine.blurb WHERE id = :blurbid', [":blurbid" => $blurbid]);
        if ($stmt === false || $stmt->rowCount() == 0) {
            return [];
        }
        $res = $stmt->fetchAll();
        $breadcrumbs = [];
        foreach ($res as $rec) {
            $siglabelpath = $rec["path"];

            $breadcrumbs[] = buildbreadcrumbs($siglabelpath);
        }
        return $breadcrumbs;
    } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("blurb.buildbreadcrumblist.100: " . $e->getMessage());
        return [];
    }
}

/**
 * Get the content directory for blurbs
 *
 * @return string The content directory path
 */
function getcontentdir(): string
{
    $contentdir = getenv("BBSENGINE6_BLURB_CONTENT_DIR");
    if ($contentdir === false || $contentdir === "") {
        $contentdir = "/var/bbsengine6/blurb_content";
    }
    return $contentdir;
}

/**
 * Get blurb content from file
 *
 * @param int $blurbid The blurb ID
 * @return string|null The content or null if not found
 */
function getcontent(int $blurbid): ?string
{
    if ($blurbid <= 0) {
        return null;
    }

    $contentdir = getcontentdir();
    $filepath = $contentdir . "/" . $blurbid . ".txt";

    // Ensure the resolved path is within the content directory (prevent path traversal)
    $realpath = realpath($filepath);
    $realdir = realpath($contentdir);
    if ($realpath === false || $realdir === false || strpos($realpath, $realdir) !== 0) {
        return null;
    }

    if (!file_exists($filepath)) {
        return null;
    }

    return file_get_contents($filepath);
}

/**
 * Get list of blurbs with pagination
 *
 * @param int $offset Offset for pagination
 * @param int $limit Number of results
 * @return array Array of blurb records
 */
function getlist(int $offset = 0, int $limit = 20): array
{
    try {
        $dbh = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = \bbsengine6\database\query($dbh, 'SELECT * FROM $engine.blurb ORDER BY datecreated DESC OFFSET :offset LIMIT :limit', [":offset" => $offset, ":limit" => $limit]);
        if ($stmt === false) {
            return [];
        }
        return $stmt->fetchAll();
    } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("blurb.getlist.100: " . $e->getMessage());
        return [];
    }
}

/**
 * Get a blurb by ID
 *
 * @param int $id The blurb ID
 * @return array|null The blurb record or null if not found
 */
function getbyid(int $id): ?array
{
    try {
        $dbh = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = \bbsengine6\database\query($dbh, 'SELECT * FROM $engine.blurb WHERE id = :id', [":id" => $id]);
        if ($stmt === false || $stmt->rowCount() == 0) {
            return null;
        }
        $blurb = $stmt->fetch();

        $attrs = $blurb["attributes"];
        if (is_array($attrs) && isset($attrs["contentpath"])) {
            $contentpath = $attrs["contentpath"];
            if (file_exists($contentpath)) {
                $blurb["content"] = file_get_contents($contentpath);
            } else {
                $blurb["content"] = getcontent($id);
            }
        } else {
            $blurb["content"] = getcontent($id);
        }

        return $blurb;
    } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("blurb.getbyid.100: " . $e->getMessage());
        return null;
    }
}

/**
 * Get count of blurbs
 *
 * @return int Total number of blurbs
 */
function getcount(): int
{
    try {
        $dbh = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = \bbsengine6\database\query($dbh, 'SELECT COUNT(*) as cnt FROM $engine.blurb');
        if ($stmt === false) {
            return 0;
        }
        $row = $stmt->fetch();
        return (int)$row["cnt"];
    } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("blurb.getcount.100: " . $e->getMessage());
        return 0;
    }
}

/**
 * Check if a blurb exists in the database for the given URI
 *
 * @param string $uri The URI path (e.g., "ec/filename")
 * @return bool True if blurb exists in database, false otherwise
 */
function isBlurb($uri)
{
    $uri = preg_replace('/\.(md|html)$/', '', $uri);
    $uri = preg_replace('/^teos\//', '', $uri);
    $blurbid = str_replace("/", ".", $uri);

    // 1. Check database first
    $sql = "SELECT 1
            FROM engine.__blurb b
            WHERE b.id = :blurbid
            LIMIT 1";

    try {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = $pdo->prepare($sql);
        $stmt->execute(["blurbid" => $blurbid]);
        $result = $stmt->fetch();
        if ($result !== false) {
            return true;
        }
    } catch (\Throwable $e) {
        // Fall through to filesystem check
    }

    // 2. Fallback: check if .md file exists on disk
    // @since 2026-09-28 — route TEOSDIR through \bbsengine6\util\env()
    // so the per-vhost htaccess SetEnv (or any putenv override) wins
    // over the constant, and so we have no implicit prod-path fallback
    // when neither is set. When TEOSDIR is unconfigured the helper
    // returns false and the dispatch loop falls through to the next
    // handler, matching router_handleFolder / router_handleMarkdown.
    $teospath = \bbsengine6\util\env('TEOSDIR');
    if (!is_string($teospath) || $teospath === '') {
        return false;
    }
    $mdfile = rtrim($teospath, '/') . '/' . str_replace(".", "/", $blurbid) . '.md';
    return file_exists($mdfile);
}

/**
 * Render a blurb with database metadata and markdown content
 *
 * @param string $uri The URI path
 * @param string $filepath The filesystem path (unused, for signature consistency)
 * @return void Outputs the rendered blurb
 */
function display($uri, $filepath)
{
    $uri = preg_replace('/\.(md|html)$/', '', $uri);
    $uri = preg_replace('/^teos\//', '', $uri);
    $blurbid = str_replace("/", ".", $uri);

    // @since 2026-09-28 — same env() canonicalization as isBlurb().
    // When TEOSDIR is unconfigured we render a 404 via page\error()
    // (rather than silently returning ROUTER_NEXT, because the
    // router already determined isBlurb() found something and we're
    // committed to the blurb branch now). router_handleBlurb's
    // \Throwable catch wraps this so a render failure here still
    // falls through gracefully.
    $blurbdir = \bbsengine6\util\env('TEOSDIR');
    if (!is_string($blurbdir) || $blurbdir === '') {
        return \bbsengine6\page\error("Blurb not found: " . htmlspecialchars($uri), 404);
    }
    $blurbfile = rtrim($blurbdir, '/') . '/' . $uri . ".md";

    if (!file_exists($blurbfile)) {
        return \bbsengine6\page\error("Blurb not found: " . htmlspecialchars($blurbfile), 404);
    }

    $content = file_get_contents($blurbfile);

    $sql = "SELECT b.id, b.kind, b.attributes, b.datecreated, b.createdbymoniker
            FROM engine.__blurb b WHERE b.id = :blurbid LIMIT 1";

    try {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = $pdo->prepare($sql);
        $stmt->execute(["blurbid" => $blurbid]);
        $blurb = $stmt->fetch();
    } catch (\Throwable $e) {
        $blurb = null;
    }

    $parts = explode(".", $blurbid);
    array_pop($parts);
    $sigpath = implode(".", $parts);
    $breadcrumbs = function_exists('bbsengine6\blurb\buildbreadcrumbs')
        ? \bbsengine6\blurb\buildbreadcrumbs($sigpath)
        : [];

    // Fall back to router's path-segment breadcrumbs if DB returned empty.
    // @since 2026-10-01 — qualify the function_exists() lookup with the
    // fully-qualified name (\bbsengine6\router\router_buildBreadcrumbs).
    // The previous bare-name check `function_exists('router_buildBreadcrumbs')`
    // resolved against the call-site namespace (\bbsengine6\blurb) and
    // always returned false, silently skipping the fallback. The visible
    // symptom was a blurb "You are here" trail that rendered only the
    // trailing crumb appended at line ~378 — e.g. /teos/sci/archaeology/
    // archeoastronomy.md showed "You are here: archeoastronomy" with no
    // parent chain. Folder pages were unaffected because their render
    // path goes through router_displayDirectoryListing() in
    // \bbsengine6\router\, where the bare name resolves against the
    // router namespace.
    if (empty($breadcrumbs) && function_exists('bbsengine6\\router\\router_buildBreadcrumbs')) {
        $breadcrumbs = \bbsengine6\router\router_buildBreadcrumbs(str_replace(".", "/", $sigpath));
    }

    \bbsengine6\setcurrentpage("teos/" . $uri);

    $parsed = parseMarkdownSections($content);

    // @since 2026-09-30 — append the current blurb as the trailing
    // (unlinked, linklast=true) "you are here" crumb. The DB-driven
    // buildbreadcrumbs() and the filesystem-fallback
    // router_buildBreadcrumbs() both build parent-folder chains only;
    // neither includes the blurb itself. Without this append,
    // page-markdown-sections.tmpl renders "You are here: teos » ec"
    // for /teos/ec/<slug>/, with no entry for the slug — i.e. the
    // trail shows the folder but not where the user actually is.
    // Title is taken from the parsed markdown H1 so the trail
    // agrees with the visible <h1> on the page (option A from the
    // design discussion). When breadcrumbs is already non-empty
    // from the DB path, only append if the last entry isn't the
    // current blurb (defensive: DB-driven chains may already
    // include it).
    $currentTitle = $parsed["title"];
    $needsAppend = true;
    if (!empty($breadcrumbs)) {
        $last = end($breadcrumbs);
        if (is_array($last) && isset($last['path']) && $last['path'] === $blurbid) {
            $needsAppend = false;
        }
    }
    if ($needsAppend) {
        $breadcrumbs[] = [
            'title' => $currentTitle,
            'path'  => $blurbid,
            'uri'   => 'teos/' . $uri,
        ];
    }

    $data = [];
    $data["content"] = $content;
    $data["blurb"] = $blurb ?? [];
    $data["breadcrumbs"] = $breadcrumbs ?? [];
    $data["uri"] = $uri;

    $data["title"] = $parsed["title"];
    $data["sections"] = $parsed["sections"];

    \bbsengine6\util\logentry("bbsengine6.blurb.100: data.title=".var_export($data["title"], true));

    $choices = [];
    // @since 2026-09-24 — use the canonical bbsengine6 menu extension
    // point. Vhosts that load zoid6 get its cross-site menu via
    // bbsengine6config.php's zoid6 hook shim; vhosts that don't get
    // an empty menu (topbar-choices.tmpl hides empty sections).
    $data["choices"] = \bbsengine6\menu\buildchoices($choices);

    return \bbsengine6\displaypage($data, "page-markdown-sections.tmpl", false);
}
function parseMarkdownSections(string $markdown): array
{
    require_once("markdown.php");
    return \bbsengine6\markdown\parseDocument($markdown, split: true);
}

}
