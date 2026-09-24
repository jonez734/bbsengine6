<?php
/**
 * bbsengine6config.php — bbsengine6-owned config defaults.
 *
 * Mirrors zoid6/php/zoid6config.php's shape: defines namespaced
 * config\SMARTY* defaults, shared URL/path constants, and a few
 * system defaults that bbsengine6's helpers (getsmarty(),
 * displaypage(), logentry()) read via `defined('\config\X') ? ... : default`.
 *
 * Vhost config.php (defined by each vhost — teos/wwworg/wwwcom/...)
 * overrides win because they're `require_once`d FIRST at the top of
 * this file via the include_path (which bbsengine6\bootstrap() has
 * prepended with VHOSTDOCROOT). If no vhost config is on the
 * include_path (CLI tests, partial deploys), the bbsengine6 defaults
 * below take over.
 *
 * @since 2026-09-24
 */

namespace bbsengine6 {

// Vhost-specific overrides win. Bare-name resolution via include_path
// matches the convention used by php/blurb.php's old
// `require_once("zoid6config.php")` and the older
// `require_once("config.php")` that engine/router.php used to carry
// (commits 45b0b71 + 27435ea dropped it; this file restores vhost
// config wiring without putting a fragile bare-name require in the
// router). Use stream_resolve_include_path() because @require_once
// still throws on failure under PHP 8.
$bbsengine6_vhostconfig = stream_resolve_include_path("config.php");
if ($bbsengine6_vhostconfig !== false) {
    require_once($bbsengine6_vhostconfig);
}

// SMARTY* defaults — only used if vhost config.php didn't define them.
if (!defined("\config\SMARTYTEMPLATESDIR")) {
    define("config\SMARTYTEMPLATESDIR", [
        "/srv/www/bbsengine6/skin/tmpl/",
    ]);
}
if (!defined("\config\SMARTYPLUGINSDIR")) {
    define("config\SMARTYPLUGINSDIR", [
        "/srv/www/bbsengine6/smarty/",
    ]);
}
if (!defined("\config\SMARTYCOMPILEDTEMPLATESDIR")) {
    define("config\SMARTYCOMPILEDTEMPLATESDIR", "/srv/www/bbsengine6/templates_c/");
}

// Global aliases for vhost templates that use {$SMARTYTEMPLATESDIR}
// etc. without the smarty.const. prefix. Mirrors zoid6config.php's
// global-alias pattern.
if (!defined("SMARTYTEMPLATESDIR")) define("SMARTYTEMPLATESDIR", \config\SMARTYTEMPLATESDIR);
if (!defined("SMARTYPLUGINSDIR")) define("SMARTYPLUGINSDIR", \config\SMARTYPLUGINSDIR);
if (!defined("SMARTYCOMPILEDTEMPLATESDIR")) define("SMARTYCOMPILEDTEMPLATESDIR", \config\SMARTYCOMPILEDTEMPLATESDIR);

// Shared URL/path constants — same shape as zoid6config.php.
if (!defined("ENGINEURL")) define("ENGINEURL", "/engine/");
if (!defined("ENGINESKINURL")) define("ENGINESKINURL", "/engine/skin/");
if (!defined("SHAREDSKINURL")) define("SHAREDSKINURL", "/shared/skin/");
if (!defined("STATICSKINURL")) define("STATICSKINURL", SHAREDSKINURL);

// Database/system defaults (vhost config can override).
if (!defined("\config\SYSTEMDSN")) {
    define("config\SYSTEMDSN", "pgsql:host=127.0.0.1;port=5432;dbname=zoid6");
}
if (!defined("SYSTEMDSN")) define("SYSTEMDSN", \config\SYSTEMDSN);

// Log prefix default; vhost config can override to disambiguate logs
// across multiple vhosts sharing the same engine deployment.
if (!defined("\config\LOGENTRYPREFIX")) {
    define("config\LOGENTRYPREFIX", "bbsengine6");
}
if (!defined("LOGENTRYPREFIX")) define("LOGENTRYPREFIX", \config\LOGENTRYPREFIX);

}

namespace bbsengine6\menu {

/**
 * @since 2026-09-24 — canonical menu extension point.
 *
 * Called by bbsengine6 source code (engine/router.php,
 * php/blurb.php, etc.) to populate the topbar-choices.tmpl menu.
 * Default behaviour: returns $choices unchanged (no menu).
 *
 * Vhosts that want a cross-site menu define their own
 * bbsengine6\menu\hook_buildchoices() function in their config.php
 * (or any file required before engine.php loads). bbsengine6config.php
 * itself installs a zoid6 hook shim below — when zoid6 is loaded,
 * \zoid6\buildchoices() is wired in automatically.
 *
 * The two-tier design (canonical buildchoices + opt-in hook) lets
 * bbsengine6 source code stay zoid6-agnostic while vhosts that
 * already use zoid6 keep their existing cross-site menu without
 * any vhost-side changes.
 *
 * @param array $choices  Menu items already accumulated by upstream callers.
 * @return array          Menu items with the vhost-supplied hook's additions.
 */
function buildchoices($choices=[])
{
    if (function_exists('\bbsengine6\menu\hook_buildchoices')) {
        return \bbsengine6\menu\hook_buildchoices($choices);
    }
    return $choices;
}

// @since 2026-09-24 — zoid6 hook shim. bbsengine6 source code calls
// \bbsengine6\menu\buildchoices() (defined above) to populate the
// topbar menu. That function delegates to a hook of the same
// namespace. This block installs a hook that wraps zoid6's
// buildchoices() — but ONLY if zoid6 has already been loaded by the
// vhost (e.g. via the vhost's require_once("zoid6config.php")).
//
// bbsengine6 itself never requires or includes zoid6 files; the shim
// only activates when the vhost opts in to zoid6 by loading it
// first. Vhosts that want a different menu define their own
// bbsengine6\menu\hook_buildchoices() function and skip zoid6
// entirely.
if (function_exists('\zoid6\buildchoices')) {
    function hook_buildchoices($choices=[])
    {
        return \zoid6\buildchoices($choices);
    }
}

}
?>
