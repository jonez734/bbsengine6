<?php
/**
 * folder.php - Folder/directory handler functions
 *
 * Provides functions to check if a URI is a directory and render
 * directory listings with markdown files. Optionally integrates with
 * database for folder metadata and sig relationships.
 */

namespace bbsengine6\folder {

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
        return null;
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
        return [];
    }
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
        return [];
    }
}

/**
 * Get the base teos path for folder lookups
 *
 * @return string The filesystem path to teos content
 */
function getteospath(): string
{
    return defined('TEOSFILEPATH') ? TEOSFILEPATH : '/srv/www/zoid6/teos/';
}

/**
 * Check if a URI corresponds to an existing directory
 *
 * @param string $uri The request URI (e.g., "ec/john-edward")
 * @return bool True if directory exists, false otherwise
 */
function isFolder($uri)
{
    $teospath = getteospath();
    $filepath = $teospath . $uri;
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
        if (!$result) {
            return true;
        }
        return (bool) $result['visible'];
    } catch (\Throwable $e) {
        return true;
    }
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

        $filecontent = file_get_contents($filepath);
        if (preg_match('/^---\s*\n(.*?)\n---/s', $filecontent, $matches)) {
            $metadata = parseYamlFrontmatter($matches[1]);
            if (isset($metadata['title'])) {
                $displayTitle = htmlspecialchars($metadata['title']);
            }
        }

        $items[] = [
            'title' => $displayTitle,
            'uri' => "/teos/" . $fileuri,
            'filename' => $filename,
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
    $teospath = getteospath();
    $filepath = $teospath . $uri;

    if (!is_dir($filepath)) {
        return null;
    }

    if (!isFolderVisible($uri) && !isSysop()) {
        return null;
    }

    $items = getDirectoryItems($filepath, $uri);
    $title = getDirectoryTitle($uri);

    if (function_exists('\bbsengine6\setcurrentpage')) {
        \bbsengine6\setcurrentpage("teos/" . $uri);
    }

    $data = [];
    $data["title"] = $title;
    $data["items"] = $items;
    $data["uri"] = $uri;
    $data["hidden"] = !isFolderVisible($uri) && isSysop();

    if (function_exists('\bbsengine6\displaypage')) {
        return \bbsengine6\displaypage($data, "directory-listing.tmpl");
    }

    $lockIcon = $data["hidden"] ? " 🔒" : "";
    return "<html><head><title>$title</title></head><body><h1>$title$lockIcon</h1><ul>" .
        implode("", array_map(fn($i) => "<li><a href=\"{$i['uri']}\">{$i['title']}</a></li>", $items)) .
        "</ul></body></html>";
}

}
