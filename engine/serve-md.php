<?php

require_once("/srv/www/bbsengine6/php/bootstrap.php");
require_once("util.php");

\bbsengine6\util\logentry("serve-md.100: start");

$uri = $_GET['path'] ?? '';

if ($uri === '' || $uri[0] !== '/') {
    $uri = '/' . $uri;
}

$relpath = ltrim($uri, '/');

if ($relpath === '' || !preg_match('#^/handbook/(\d+)/#', $_SERVER['REQUEST_URI'] ?? '', $m)) {
    \bbsengine6\util\logentry("serve-md.210: validate failed relpath=" . var_export($relpath, true) . " request_uri=" . var_export($_SERVER['REQUEST_URI'] ?? '', true));
    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'engine.serve-md.validate-handbook-prefix.220: File not found';
    exit;
}

$prefix = 'handbook/' . $m[1];
$file = \bbsengine6\util\handbook_resolve($prefix, $relpath);

if ($file === false) {
    \bbsengine6\util\logentry("serve-md.200: resolve failed for prefix=$prefix path=$relpath");
    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'engine.serve-md.resolve-handbook-md.240: File not found';
    exit;
}

header('Content-Type: text/plain; charset=utf-8');
readfile($file);
