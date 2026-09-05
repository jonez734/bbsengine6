<?php
/**
 * blurb.php - Blurb handler functions
 *
 * Provides functions to check if a URI is a blurb and render blurbs
 * with database metadata and markdown content
 */

namespace bbsengine6\blurb {

require_once(__DIR__ . "/../../zoid6/php/bootstrap.php");
\zoid6\bootstrap();

require_once("zoid6config.php");
require_once("zoid6.php");

require_once("engine.php");
// require_once("database.php");

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

        // Prepend "teos" crumb
        $teosurl = defined('TEOSURL') ? TEOSURL : '';
        array_unshift($crumbs, [
            'title' => 'teos',
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
    $teospath = defined('TEOSDIR') ? TEOSDIR : '/srv/www/vhosts/zoidtechnologies.com/html/teos/';
    $mdfile = $teospath . str_replace(".", "/", $blurbid) . '.md';
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

    $blurbdir = defined('TEOSDIR') ? TEOSDIR : "/srv/www/vhosts/zoidtechnologies.com/html/teos/";
    $blurbfile = $blurbdir . $uri . ".md";

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

    // Fall back to router's path-segment breadcrumbs if DB returned empty
    if (empty($breadcrumbs) && function_exists('router_buildBreadcrumbs')) {
        $breadcrumbs = router_buildBreadcrumbs(str_replace(".", "/", $sigpath));
    }

    \bbsengine6\setcurrentpage("teos/" . $uri);

    $data = [];
    $data["content"] = $content;
    $data["blurb"] = $blurb ?? [];
    $data["breadcrumbs"] = $breadcrumbs ?? [];
    $data["uri"] = $uri;

    $parsed = parseMarkdownSections($content);

    $data["title"] = $parsed["title"];
    $data["sections"] = $parsed["sections"];

    \bbsengine6\util\logentry("bbsengine6.blurb.100: data.title=".var_export($data["title"], true));

    $choices = [];
    $data["choices"] = \zoid6\buildchoices($choices);

    return \bbsengine6\displaypage($data, "page-markdown-sections.tmpl", false);
}
function parseMarkdownSections(string $markdown): array
{
    require_once(__DIR__ . "/markdown.php");
    return \bbsengine6\markdown\parseDocument($markdown, split: true);
}

}
