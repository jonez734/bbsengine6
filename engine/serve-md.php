<?php
/**
 * serve-md.php - Serve .md files as plain text
 * 
 * Outputs markdown files with Content-Type: text/plain
 */

if (php_sapi_name() === 'cli' && basename($_SERVER['PHP_SELF']) === 'serve-md.php') {
    echo "serve-md.php - serves .md files as text/plain\n";
    exit(0);
}

// Get the requested path
$path = $_GET['path'] ?? $_GET['uri'] ?? '';

// Define TEOSDIR if not defined
if (!defined('TEOSDIR')) {
    define('TEOSDIR', '/srv/www/vhosts/zoidtechnologies.com/html/teos/');
}

// Security: validate path
$teospath = TEOSDIR;
$filepath = realpath($teospath . $path);

// Ensure the resolved path is within TEOSDIR (prevent directory traversal)
if ($filepath === false || strpos($filepath, $teospath) !== 0) {
    http_response_code(404);
    echo "File not found";
    exit;
}

// Check file exists and has .md extension
if (!file_exists($filepath) || !is_file($filepath) || pathinfo($filepath, PATHINFO_EXTENSION) !== 'md') {
    http_response_code(404);
    echo "File not found";
    exit;
}

// Set content type to plain text
header('Content-Type: text/plain; charset=utf-8');

// Output the raw file
readfile($filepath);
