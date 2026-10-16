<?php
/**
 * folder.php - Folder/directory handler functions
 *
 * Provides functions to check if a URI is a directory and render
 * directory listings with markdown files. Optionally integrates with
 * database for folder metadata and sig relationships.
 */

namespace bbsengine6\folder {
    require_once("bootstrap.php");
    require_once("util.php");

/**
 * Root sig path prefix.
 * Set to empty string "" to disable 'top.' prefix.
 * Set to "top" to use 'top.' prefix (legacy behavior).
 */
const ROOT_SIG_PREFIX = '';

/**
 * Get folder metadata from database
 *
 * @param string $uri The folder URI path
 * @return array|null Folder metadata or null if not found
 */
function getFolderMeta(string $uri): ?array
{
    $prefix = ROOT_SIG_PREFIX;
    $path = $prefix ? $prefix . '.' . $uri : $uri;

    $sql = "SELECT path, title, uri, attrs as attributes
            FROM engine.sig
            WHERE path = :path::ltree
            LIMIT 1";

    try {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = $pdo->prepare($sql);
        $stmt->execute(["path" => $path]);
        $result = $stmt->fetch();
        return $result ?: null;
    } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("getfoldermeta.100");
        return [];
    }
}

/**
 * Get folder sigs from database (folders that are sigs)
 *
 * @param string $uri The folder URI path
 * @return array Array of sig records
 */
function getFolderSigs(string $uri): array
{
    $prefix = ROOT_SIG_PREFIX;
    $path = $prefix ? $prefix . '.' . $uri : $uri;

    $sql = "SELECT s.path, s.title, s.uri, s.attrs as attributes
            FROM engine.sig s
            WHERE s.path ~ :pattern
            ORDER BY s.path";

    try {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $pattern = $path . '.*';
        $stmt = $pdo->prepare($sql);
        $stmt->execute(["pattern" => $pattern]);
        return $stmt->fetchAll();
    } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("getfoldersigs.100");
        return [];
    }
}

/**
 * Get folder breadcrumb trail from database
 *
 * @param string $uri The folder URI path (e.g., "ec_john-edward")
 * @return array Array of breadcrumb sig records
 */
function getFolderBreadcrumbs(string $uri): array
{
    $prefix = ROOT_SIG_PREFIX;
    $path = $prefix ? $prefix . '.' . $uri : $uri;

    $sql = "SELECT title, path, uri
            FROM engine.sig
            WHERE path @> :sigpath
            ORDER BY path ASC";

    try {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = $pdo->prepare($sql);
        $stmt->execute(["sigpath" => $path]);
        return $stmt->fetchAll();
    } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("getfolderbreadcrumbs.100: uri=".var_export($uri, true));
    }
    return [];
}

/**
 * List all top-level folders from database (sigs directly under 'top')
 *
 * @return array Array of top-level sigs
 */
function getTopLevelFolders(): array
{
    $sql = "SELECT path, title, uri, attrs as attributes
            FROM engine.sig
            WHERE nlevel(path) = 1
            ORDER BY title";

    try {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = $pdo->query($sql);
        return $stmt->fetchAll();
    } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("gettoplevelfolders.100");
        return [];
    }
}

/**
 * Get the base teos path for folder lookups
 *
 * @return string The filesystem path to teos content
 */
//function getteospath(): string
//{
//    return defined('TEOSDIR') ? TEOSDIR : '/srv/www/vhosts/zoidtechnologies.com/html/teos/';
//}

/**
 * Check if a URI corresponds to an existing directory
 *
 * @param string $uri The request URI (e.g., "ec/john-edward")
 * @return bool True if directory exists, false otherwise
 */
function isFolder($uri)
{
    $teosdir = \bbsengine6\util\env("TEOSDIR");
    $filepath = \bbsengine6\util\safe_path_web([$uri], ['base_dir' => $teosdir, 'must_exist' => false]);
    if ($filepath === false) {
        return false;
    }
    return is_dir($filepath);
}

/**
 * Check if a folder is visible in public listings
 *
 * @param string $uri The folder URI path (e.g., "comp/lang")
 * @return bool True if visible or folder doesn't exist in DB, false if not visible
 */
function isFolderVisible(string $uri): bool
{
    $prefix = ROOT_SIG_PREFIX;
    $path = $prefix ? $prefix . '.' . str_replace('/', '.', $uri) : str_replace('/', '.', $uri);

    $sql = "SELECT visible FROM engine.folder WHERE path = :path::ltree LIMIT 1";

    try {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
        $stmt = $pdo->prepare($sql);
        $stmt->execute(["path" => $path]);
        $result = $stmt->fetch();
        if ($result) {
            return (bool) $result['visible'];
        }
    } catch (\Throwable $e) {
        // Fall through to .folder.json fallback
    }

    // Fallback: check .folder.json in filesystem
    $teosdir = \bbsengine6\util\env("TEOSDIR");
    $folderJsonPath = \bbsengine6\util\safe_path_web([$uri, '.folder.json'], ['base_dir' => $teosdir]);
    if ($folderJsonPath !== false && file_exists($folderJsonPath)) {
        $json = json_decode(file_get_contents($folderJsonPath), true);
        if (isset($json['visible'])) {
            return (bool) $json['visible'];
        }
    }

    // Default: visible if no config found
    return true;
}

/**
 * Check if current user is sysop
 *
 * @return bool True if user is sysop
 */
function isSysop(): bool
{
    if (!function_exists('\bbsengine6\member\lib\checkflag')) {
        return false;
    }
    return \bbsengine6\member\lib\checkflag("SYSOP") === true;
}

/**
 * Get directory listing items for a folder
 *
 * @param string $dirpath Full filesystem path to directory
 * @param string $uri The request URI
 * @return array Array of items with title, uri, filename
 */
function getDirectoryItems(string $dirpath, string $uri): array
{
    $files = glob($dirpath . "/*.md");
    sort($files);

    $items = [];

    foreach ($files as $filepath) {
        $filename = basename($filepath, '.md');
        $fileuri = $uri . "/" . $filename;

        $metadata = [];
        $displayTitle = $filename;
        $updated = false;

        $filecontent = @file_get_contents($filepath);
        if (is_string($filecontent) && $filecontent !== "") {
            // Lazy-load markdown.php here (rather than at the
            // top of folder.php) so the file's require graph
            // stays narrow for callers that don't read .md
            // content. splitFrontmatter() is the same call
            // engine/router.php::router_collectDirectoryItems:652
            // uses for its file-branch title/updated reads.
            require_once("markdown.php");
            // @since 2026-10-15 — switch the frontmatter read in
            // getDirectoryItems() from parseYamlFrontmatter() to
            // \bbsengine6\markdown\splitFrontmatter(). Reasons:
            //   1. The engine path
            //      (engine/router.php::router_collectDirectoryItems:652)
            //      already uses splitFrontmatter() for the same
            //      read, so the two paths now agree on the parser
            //      (previously the legacy path used a private
            //      regex-only parser that did not accept
            //      hyphenated keys like `folder-path`).
            //   2. We need `lastmodified:` and `date:` to compute
            //      the new per-item `updated` field below; reading
            //      them out of splitFrontmatter's metadata array
            //      avoids a second frontmatter parse.
            //   3. parseYamlFrontmatter() remains in this file as
            //      a public API (used by php/test_folder.php
            //      Tests 6-9 and documented in
            //      handbook/specs/folder.md:97) — this swap is
            //      about which function *getDirectoryItems()* uses
            //      internally, not removing the API.
            $split = \bbsengine6\markdown\splitFrontmatter($filecontent);
            $metadata = $split[0] ?? [];
            // Mirror the title-escape logic at
            // engine/router.php:661-664: trim first so an empty
            // or whitespace-only title falls back to the filename
            // instead of rendering a blank link; htmlspecialchars
            // to neutralize stored-XSS in the YAML-derived title
            // (folder.tmpl prints {$item.title} raw).
            $rawTitle = isset($metadata['title']) ? trim($metadata['title']) : '';
            if ($rawTitle !== '') {
                $displayTitle = htmlspecialchars($rawTitle, ENT_QUOTES | ENT_HTML5, 'UTF-8');
            }

            // Per-item `updated` field, sourced from the same
            // frontmatter keys `blurb.php::display()` reads for
            // the page-level `.metadata .lastmodified` block
            // (php/blurb.php:427-443), so the per-item stamp in
            // the listing matches the stamp shown on the blurb
            // itself. Priority:
            //   1. Frontmatter `lastmodified:` (managed by
            //      blurbs/Makefile on `make prod`; refreshed from
            //      the file's mtime on every deploy).
            //   2. Frontmatter `date:` (legacy contract; the
            //      pre-2026-10-15 single-field timestamp).
            //   3. `filemtime($filepath)` — ultimate fallback
            //      for blurbs without frontmatter, matching
            //      achilles's pattern.
            //   4. `false` if all three fail, so folder.tmpl
            //      can suppress the stamp via
            //      `{if $item.updated !== false}`.
            //
            // The frontmatter timestamp format is
            // `YYYY-MM-DD HH:MM:SS GMT (HH:MM:NN TZ)`. The
            // parenthetical TZ suffix is informational only; we
            // strip it before strtotime (mirror of blurb.php:433).
            $updated = false;
            $stamp = null;
            if (isset($metadata['lastmodified']) && is_string($metadata['lastmodified']) && $metadata['lastmodified'] !== "") {
                $stamp = $metadata['lastmodified'];
            } elseif (isset($metadata['date']) && is_string($metadata['date']) && $metadata['date'] !== "") {
                $stamp = $metadata['date'];
            }
            if (is_string($stamp)) {
                $gmStamp = preg_replace('/\s*\(.*\)\s*$/', '', $stamp);
                $updated = strtotime($gmStamp);
                if (!is_int($updated) || $updated <= 0) {
                    $updated = false;
                }
            }
            if ($updated === false) {
                $fm = @filemtime($filepath);
                if (is_int($fm) && $fm > 0) {
                    $updated = $fm;
                }
            }
        }

        $items[] = [
            'title' => $displayTitle,
            'uri' => \bbsengine6\util\env("TEOSURL"). $fileuri, 'filename' => $filename, //\bbsengine6\util\teos_url() . $fileuri,
            // @since 2026-10-15 — populate `is_folder` and `ext`
            // for parity with engine/router.php::router_collectDirectoryItems().
            // Legacy getDirectoryItems() only handles `.md` files
            // (no subdirectories), so both fields are constants:
            // `is_folder => false`, `ext => 'md'`. The presence of
            // these fields lets folder.tmpl render a consistent
            // shape regardless of which code path populated the
            // listing (legacy direct call vs engine-routed call).
            'is_folder' => false,
            'ext' => 'md',
            // @since 2026-10-15 — per-item `updated` datestamp,
            // rendered to the right of the blurb's title in
            // folder.tmpl. Int (epoch) when a timestamp is
            // resolvable from frontmatter or mtime, `false`
            // otherwise. Mirrors the page-level `lastmodified`
            // resolution in blurb.php::display() so the listing
            // stamp agrees with the stamp on the blurb page.
            // `modified` (raw filemtime) is intentionally NOT
            // added here: the legacy listing path never carried
            // a per-item timestamp before this commit, and the
            // engine path (`engine/router.php`) is the canonical
            // source of `modified`. Keeping the two paths'
            // field sets distinct avoids spurious diffs if a
            // consumer relies on field presence to identify
            // which code path populated the listing.
            'updated' => $updated,
        ];
    }

    return $items;
}

/**
 * Parse YAML frontmatter string into associative array
 *
 * @param string $yaml The YAML content
 * @return array Parsed key-value pairs
 */
function parseYamlFrontmatter(string $yaml): array
{
    $result = [];
    $lines = explode("\n", $yaml);

    foreach ($lines as $line) {
        if (preg_match('/^(\w+):\s*(.*)$/', $line, $matches)) {
            $key = $matches[1];
            $value = $matches[2];

            $value = trim($value, '"');
            $value = trim($value, "'");

            $result[$key] = $value;
        }
    }

    return $result;
}

/**
 * Get the title for a directory from its URI
 *
 * @param string $uri The request URI
 * @return string The directory title
 */
function getDirectoryTitle(string $uri): string
{
    return htmlspecialchars(basename($uri));
}

/**
 * Render a directory listing
 *
 * @param string $uri The request URI
 * @return string|null Rendered HTML or null if directory doesn't exist
 */
function display($uri)
{
    $teospath = \bbsengine6\util\env("TEOSDIR", "NEEDINFO:display"); //getteospath()
    $filepath = \bbsengine6\util\safe_path_web([$uri], ['base_dir' => $teospath, 'must_exist' => false]);
    if ($filepath === false || !is_dir($filepath)) {
        return [];
    }

    if (!isFolderVisible($uri) && !isSysop()) {
        return [];
    }

    $items = getDirectoryItems($filepath, $uri);
    $title = getDirectoryTitle($uri);

    if (function_exists('\bbsengine6\setcurrentpage')) {
        // @since YYYY-MM-DD — use the env-first teos_url() helper
        // instead of the hard-coded "teos/" prefix. The bare
        // constant \TEOSURL is defined by zoid6/php/zoid6config.php
        // to "/teos/" regardless of which vhost is serving, which
        // made handbook/<v>/<dir>/ breadcrumbs render the wrong
        // path on www.bbsengine.org (e.g. "teos/specs/auth-bank"
        // instead of "handbook/6/specs/auth-bank"). teos_url()
        // honors the per-vhost TEOSURL env var that each vhost
        // declares in its htaccess-prod (SetEnv TEOSURL /handbook/
        // <v>/ on .org, /teos/ on .com), matching the directory-
        // item URI fix on line 240.
        \bbsengine6\setcurrentpage(\bbsengine6\util\teos_url() . $uri);
    }

    $data = [];
    $data["title"] = $title;
    $data["items"] = $items;
    $data["uri"] = $uri;
    $data["hidden"] = !isFolderVisible($uri) && isSysop();

    // @since 2026-10-15 — populate $data["lastmodified"] for the
    // page-level `.metadata` block in folder.tmpl (mirroring
    // achilles/www/skin/tmpl/section.tmpl:3-7). Folders don't
    // carry frontmatter, so the timestamp is the directory's own
    // mtime. Falsy on any filesystem error so the template can
    // suppress the block via `{if $data.lastmodified !== false}`.
    // Mirrors the same field populated in
    // bbsengine6/engine/router.php::router_displayDirectoryListing()
    // for the engine-routed path; the legacy folder.php::display()
    // path (called directly by some teos entry points and CLI
    // tests) needs its own copy to stay consistent.
    $data["lastmodified"] = is_dir($filepath) ? @filemtime($filepath) : false;

    // @since 2026-09-30 — populate $data["breadcrumbs"] so folder.tmpl's
    // youarehere include has a trail to render. Mirrors the blurb.php
    // pattern (blurb.php::display): the filesystem-fallback
    // router_buildBreadcrumbs() builds the root + folder chain, and
    // the trailing segment (the current folder itself) is rendered as
    // plain text by youarehere.tmpl because folder.tmpl passes
    // linklast=true. Without this assignment folder.tmpl's youarehere
    // include sees an undefined $breadcrumbs variable and renders
    // nothing after "You are here: ".
    //
    // @since 2026-10-01 — qualify the function_exists() lookup with the
    // fully-qualified name. The bare-name check resolved against the
    // call-site namespace (\bbsengine6\folder) and returned false,
    // skipping the breadcrumb assignment. Folder pages hit this code
    // path only via legacy/standalone callers today (the live chrome
    // path goes through router_displayDirectoryListing() in
    // \bbsengine6\router\, where bare-name resolution works), but any
    // future caller of folder.php::display() would have rendered an
    // empty breadcrumb chain for the same reason the blurb page did.
    if (function_exists('bbsengine6\\router\\router_buildBreadcrumbs')) {
        $data["breadcrumbs"] = \bbsengine6\router\router_buildBreadcrumbs($uri);
    } else {
        $data["breadcrumbs"] = [];
    }

    if (function_exists('\bbsengine6\displaypage')) {
        return \bbsengine6\displaypage($data, "folder.tmpl");
    }

    $lockIcon = $data["hidden"] ? " 🔒" : "";
    return "<html><head><title>$title</title></head><body><h1>$title$lockIcon</h1><ul>" .
        implode("", array_map(fn($i) => "<li><a href=\"{$i['uri']}\">{$i['title']}</a></li>", $items)) .
        "</ul></body></html>";
}

}
