<?php
/**
 * engine/serve-md.php - Handbook vhost entry-point (thin wrapper).
 *
 * htaccess-prod (www/org/htaccess-prod:78) rewrites
 *   /handbook/<v>/<uri>.md -> /engine/serve-md.php?path=$2
 * The substantive code (entry-point function + library) lives at
 * php/markdown.php under namespace \bbsengine6\markdown and is loaded
 * via require_once below. The merged file's namespace {} entry-point
 * guard fires once on direct invocation, calls serveRawMarkdownForHandbook()
 * which exits on every path. See php/markdown.php's file header for the
 * full charter and 404 body IDs.
 *
 * Staged by engine/Makefile's ENGINE_PHP wildcard
 * ($(wildcard *.php)) to $(ENGINESTAGEDOCROOT) on $(ENGINEHOST).
 */
require_once __DIR__ . '/../php/markdown.php';
\bbsengine6\markdown\serveRawMarkdownForHandbook();
