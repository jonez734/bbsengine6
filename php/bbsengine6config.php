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

// @since 2026-09-24 — SMARTYTEMPLATESDIR defaults. We do NOT
// define a default here: getsmarty() throws a clear
// RuntimeException when the vhost didn't define it. Defining
// a default would silently hide the misconfiguration.
// Normalization (flattening, dedup, slash-normalization, hook
// consultation, engine-fallback append) happens in
// \bbsengine6\templatedirs\normalize() at first getsmarty() call.
// Mirror bare -> namespaced for vhosts that defined the legacy
// bare form.
if (defined("SMARTYTEMPLATESDIR") && !defined("\config\SMARTYTEMPLATESDIR")) {
    define("config\SMARTYTEMPLATESDIR", SMARTYTEMPLATESDIR);
}

// @since 2026-09-24 — SMARTYPLUGINSDIR default. Unlike
// SMARTYTEMPLATESDIR (which has no default and triggers a
// getsmarty() RuntimeException), SMARTYPLUGINSDIR has an
// engine-owned default: a single-element array pointing at
// bbsengine6/smarty/. getsmarty() appends its own engine plugin
// dir if not present, so vhosts that don't override get a
// working {teos} plugin out of the box.
if (!defined("\config\SMARTYPLUGINSDIR") && !defined("SMARTYPLUGINSDIR")) {
    $enginePlugDir = rtrim(dirname(__DIR__), '/') . '/smarty/';
    define("config\SMARTYPLUGINSDIR", [$enginePlugDir]);
} elseif (defined("SMARTYPLUGINSDIR") && !defined("\config\SMARTYPLUGINSDIR")) {
    define("config\SMARTYPLUGINSDIR", SMARTYPLUGINSDIR);
}

if (!defined("\config\SMARTYCOMPILEDTEMPLATESDIR")) {
    define("config\SMARTYCOMPILEDTEMPLATESDIR", "/srv/www/bbsengine6/templates_c/");
}

// Shared URL/path constants — same shape as zoid6config.php.
if (!defined("ENGINEURL")) define("ENGINEURL", "/engine/");
if (!defined("ENGINESKINURL")) define("ENGINESKINURL", "/engine/skin/");
if (!defined("SHAREDSKINURL")) define("SHAREDSKINURL", "/shared/skin/");
if (!defined("STATICSKINURL")) define("STATICSKINURL", SHAREDSKINURL);

// @since 2026-09-24 — single source of truth for the cross-app
// shared tmpl path. Mirrors config\SHAREDSKINURL (URL side) and
// config\SKINDIR (per-vhost path) patterns. Default works for
// the zoidtechnologies.com vhost layout; vhosts with a
// different shared-dir layout override before requiring this file.
if (!defined("\config\SHAREDTMPLDIR")) {
    define("config\SHAREDTMPLDIR",
        "/srv/www/vhosts/zoidtechnologies.com/html/shared/skin/tmpl/");
}

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

namespace bbsengine6\templatedirs {

/**
 * @since 2026-09-24 — extension point for consumer apps that
 * need to contribute extra template directories to the search
 * path. Default: returns []. Consumer apps define
 * \bbsengine6\templatedirs\hook_extra_dirs() in their config.php
 * (or any file required before bbsengine6config.php runs).
 *
 * Mirrors the bbsengine6\menu\hook_buildchoices pattern above.
 *
 * @return array<int, string> Absolute template dirs ending in "/".
 */
function extra_dirs(): array {
    if (function_exists('\bbsengine6\templatedirs\hook_extra_dirs')) {
        return \bbsengine6\templatedirs\hook_extra_dirs();
    }
    return [];
}

// @since 2026-09-24 — zoid6 hook shim (parallel to the menu
// shim at line 121-126 above). When zoid6 is loaded, it gets a
// chance to add its template dir to the search path.
if (function_exists('\zoid6\templatedirs_extra')) {
    function hook_extra_dirs(): array {
        return \zoid6\templatedirs_extra();
    }
}

/**
 * @since 2026-09-24 — normalize a SMARTYTEMPLATESDIR value:
 *   - accept array or scalar string
 *   - flatten accidental array-of-array wrapping (legacy bug:
 *     array(SMARTYTEMPLATESDIR) in old shims)
 *   - validate each entry is a string (throw otherwise)
 *   - ensure trailing "/" on each entry
 *   - dedup (case-sensitive, assumes Linux ext4)
 *   - run hook_extra_dirs() if defined, append hook entries
 *   - append engine fallback (bbsengine6/skin/tmpl/) last
 *
 * Called by \bbsengine6\getsmarty() on every invocation.
 * Idempotent: calling on an already-normalized list is a no-op.
 *
 * @param mixed $raw  The raw SMARTYTEMPLATESDIR value (array or string).
 * @return array<int, string> Flat numeric-keyed array of absolute paths ending in "/".
 * @throws \RuntimeException on invalid input or hook errors.
 */
function normalize($raw): array {
    if (!is_array($raw) && !is_string($raw)) {
        throw new \RuntimeException(
            "bbsengine6\\templatedirs\\normalize: SMARTYTEMPLATESDIR must be array or string; "
          . "got " . gettype($raw) . "."
        );
    }

    $flat = [];
    foreach ((array) $raw as $d) {
        foreach ((array) $d as $dd) $flat[] = $dd;
    }

    foreach ($flat as $i => $d) {
        if (!is_string($d)) {
            throw new \RuntimeException(
                "bbsengine6\\templatedirs\\normalize: SMARTYTEMPLATESDIR[$i] must be a string; "
              . "got " . gettype($d) . "."
            );
        }
    }

    // array_unique uses string comparison; case-sensitivity assumes
    // a case-sensitive filesystem (Linux ext4 — true on all our
    // deploys).
    $flat = array_values(array_unique(array_map(
        fn($d) => rtrim($d, "/") . "/", $flat)));

    if (function_exists('\bbsengine6\templatedirs\hook_extra_dirs')) {
        $extras = \bbsengine6\templatedirs\hook_extra_dirs();
        if (!is_array($extras)) {
            throw new \RuntimeException(
                "bbsengine6\\templatedirs\\normalize: hook_extra_dirs() "
              . "must return an array; got " . gettype($extras) . "."
            );
        }
        foreach ($extras as $d) {
            if (!is_string($d)) {
                throw new \RuntimeException(
                    "bbsengine6\\templatedirs\\normalize: hook_extra_dirs() returned a non-string."
                );
            }
            $d = rtrim($d, "/") . "/";
            if (!in_array($d, $flat, true)) $flat[] = $d;
        }
    }

    // Engine fallback always last so vhost overrides win.
    // bbsengine6config.php lives at <engine_root>/php/, so the
    // engine's skin/tmpl/ is one level up.
    $engineTmpl = dirname(__DIR__) . "/skin/tmpl/";
    if (!in_array($engineTmpl, $flat, true)) $flat[] = $engineTmpl;

    return $flat;
}

}
?>
