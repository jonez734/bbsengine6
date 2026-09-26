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

// @since 2026-09-26 — moved \\config\\SHAREDTMPLDIR default
// above the vhost auto-load below. The previous order (default
// defined at line 77+ *after* the auto-load at line 30-33) meant
// any vhost config.php that referenced \\config\\SHAREDTMPLDIR
// during its own SMARTYTEMPLATESDIR define (e.g. teos/www/config
// -prod.php:67, handbook vhost config.php:51) hit an "Undefined
// constant" fatal — the constant was being defined AFTER the
// vhost config had already tried to read it.
//
// Defining SHAREDTMPLDIR first also makes the auto-load below
// work for vhosts that don't explicitly require bbsengine6
// config.php (e.g. CLI test harnesses, partial deploys).
//
// Vhosts with a different shared-dir layout still override
// before requiring this file (the `if (!defined(...))` guard
// below remains in place).
if (!defined("\\config\\SHAREDTMPLDIR")) {
    define("config\\SHAREDTMPLDIR",
        "/srv/www/vhosts/zoidtechnologies.com/html/shared/skin/tmpl/");
}

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

// @since 2026-09-26 — no default for SMARTYCOMPILEDTEMPLATESDIR.
// Mirrors the no-default policy for SMARTYTEMPLATESDIR (above):
// getsmarty() throws a clear RuntimeException when the vhost
// didn't define it. A default here would silently commit a path
// the web user may not be able to write to, AND would race any
// vhost that defines the constant after requiring this file —
// PHP's re-define of an existing constant emits E_NOTICE without
// changing the value, so the vhost's later define would be
// dropped on the floor. The teos/www/config-prod.php incident
// on 2026-09-26 was exactly that: an explicit require of this
// file (added for SHAREDTMPLDIR) ran before the vhost's own
// SMARTYCOMPILEDTEMPLATESDIR define, and the default took over.
// Removing the default closes the trap; vhost configs must now
// set the constant (either before or after requiring this file;
// both orders are safe because this file no longer touches it).

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

/**
 * \bbsengine6\template — canonical template-dir registry and resolver.
 *
 * Public API:
 *   - PRIORITY_APP / PRIORITY_APP_INTEGRATION / PRIORITY_ENGINE
 *       priority tags for register().
 *   - register(string $priority, callable $hook): void
 *       hook is called by normalize() in priority order; must return
 *       an array of absolute paths ending in "/". Idempotent.
 *       Throws RuntimeException on unknown priority (typo guard).
 *   - extra(): array
 *       canonical engine-level contribution:
 *       [<bbsengine6 root>/skin/tmpl/]. Self-registered at
 *       PRIORITY_ENGINE below.
 *   - normalize(mixed $raw, array $registry, string $engineFallback,
 *               string $nsLabel): array
 *       canonical normalize. Two public wrappers (plugin\normalize,
 *       zoid6\template\normalize) delegate here with their own
 *       registry and engine-fallback path.
 *
 * Auto-wiring (in this file, below the namespace):
 *   - \bbsengine6\template\extra is self-registered at
 *     PRIORITY_ENGINE.
 *   - \bbsengine6\template\hook_extra_dirs (legacy v0 single-slot
 *     hook) is auto-registered at PRIORITY_APP_INTEGRATION if it
 *     exists.
 *   - \zoid6\template\extra is auto-registered at
 *     PRIORITY_APP_INTEGRATION if it exists. zoid6 must be loaded
 *     BEFORE this file for that hook to fire. There is no hard
 *     dependency: bbsengine6 stays zoid6-agnostic.
 *
 * PRIORITY_ENGINE is reserved for the engine's own canonical
 * extra(). Apps and vhosts register at APP or APP_INTEGRATION.
 */
namespace bbsengine6\template {

const PRIORITY_APP             = 'app';
const PRIORITY_APP_INTEGRATION = 'app-integration';
const PRIORITY_ENGINE          = 'engine';

static $_template_registry = null;
function _registry(): array {
    global $_template_registry;
    if ($_template_registry === null) {
        $_template_registry = [
            PRIORITY_APP             => [],
            PRIORITY_APP_INTEGRATION => [],
            PRIORITY_ENGINE          => [],
        ];
    }
    return $_template_registry;
}

/**
 * Register a hook at the given priority. The hook is a callable
 * with no required arguments that returns an array of absolute
 * paths ending in "/". Idempotent against duplicate registration
 * of the same callable (=== comparison). Throws RuntimeException
 * on unknown priority.
 */
function register(string $priority, callable $hook): void {
    _registry();
    global $_template_registry;
    if (!isset($_template_registry[$priority])) {
        throw new \RuntimeException(
            "bbsengine6\\template\\register: unknown priority '$priority'. "
          . "Valid: app, app-integration, engine."
        );
    }
    if (!in_array($hook, $_template_registry[$priority], true)) {
        $_template_registry[$priority][] = $hook;
    }
}

/**
 * Canonical engine-level template-dir contribution.
 * Self-registered at PRIORITY_ENGINE in this file.
 */
function extra(): array {
    return [dirname(__DIR__) . "/skin/tmpl/"];
}

/**
 * Canonical normalize body. The 4-arg signature is internal; the
 * public-facing wrappers (\bbsengine6\template\plugin\normalize,
 * \zoid6\template\normalize) call this with their own registry
 * and engine-fallback path.
 *
 * Resolution order:
 *   1. Flatten + dedup + slash-normalize $raw.
 *   2. Iterate registry by priority [APP, APP_INTEGRATION, ENGINE].
 *      Each hook's returned dirs are validated, deduped, and
 *      appended.
 *   3. The supplied $engineFallback is injected as a synthetic
 *      hook at PRIORITY_ENGINE if not already present, so the
 *      engine fallback always appears last.
 */
function normalize(mixed $raw, array $registry, string $engineFallback, string $nsLabel): array {
    if (!is_array($raw) && !is_string($raw)) {
        throw new \RuntimeException(
            "$nsLabel\\normalize: input must be array or string; "
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
                "$nsLabel\\normalize: input[$i] must be a string; "
              . "got " . gettype($d) . "."
            );
        }
    }

    $flat = array_values(array_unique(array_map(
        fn($d) => rtrim($d, "/") . "/", $flat)));

    $effective = $registry;
    $engineHook = fn() => [$engineFallback];
    if (!isset($effective[PRIORITY_ENGINE])) {
        $effective[PRIORITY_ENGINE] = [];
    }
    if (!in_array($engineHook, $effective[PRIORITY_ENGINE], true)) {
        $effective[PRIORITY_ENGINE][] = $engineHook;
    }

    foreach ([PRIORITY_APP, PRIORITY_APP_INTEGRATION, PRIORITY_ENGINE] as $priority) {
        foreach ($effective[$priority] ?? [] as $hook) {
            $r = $hook();
            if (!is_array($r)) {
                throw new \RuntimeException(
                    "$nsLabel\\normalize: hook returned non-array."
                );
            }
            foreach ($r as $j => $d) {
                if (!is_string($d)) {
                    throw new \RuntimeException(
                        "$nsLabel\\normalize: hook returned non-string entry[$j]."
                    );
                }
                $d = rtrim($d, "/") . "/";
                if (!in_array($d, $flat, true)) $flat[] = $d;
            }
        }
    }

    return $flat;
}

// Self-bootstrap: engine registers its own canonical contribution.
\bbsengine6\template\register(
    \bbsengine6\template\PRIORITY_ENGINE,
    '\bbsengine6\template\extra'
);

// v0 back-compat: auto-register the legacy single-slot hook if a
// vhost defined it directly in this namespace. (e.g. teos/www/
// config-prod.php originally defined
// \bbsengine6\templatedirs\hook_extra_dirs(); after the rename to
// \bbsengine6\template, that definition still works.)
if (function_exists('\bbsengine6\template\hook_extra_dirs')) {
    \bbsengine6\template\register(
        \bbsengine6\template\PRIORITY_APP_INTEGRATION,
        '\bbsengine6\template\hook_extra_dirs'
    );
}

// Cross-app: auto-register zoid6's contribution if zoid6 is loaded.
// bbsengine6 itself does NOT require zoid6; the function_exists
// check is a no-op when zoid6 is absent.
if (function_exists('\zoid6\template\extra')) {
    \bbsengine6\template\register(
        \bbsengine6\template\PRIORITY_APP_INTEGRATION,
        '\zoid6\template\extra'
    );
}

// Cross-app: auto-register teos's contribution if teos is loaded.
// bbsengine6 itself does NOT require teos; the function_exists
// check is a no-op when teos is absent. teos's www/config-prod.php
// loads www/php/teos_template.php (which defines \teos\template\extra)
// after zoid6config.php, so this block fires whenever the teos
// vhost config is on the load path. The hook gracefully returns []
// when TEOSDIR is unset or when <TEOSDIR>/skin/tmpl/ doesn't exist
// (e.g. the handbook vhost at www.bbsengine.org sets TEOSDIR to a
// markdown root with no skin/tmpl/ subdir).
if (function_exists('\teos\template\extra')) {
    \bbsengine6\template\register(
        \bbsengine6\template\PRIORITY_APP_INTEGRATION,
        '\teos\template\extra'
    );
}

} // namespace bbsengine6\template

/**
 * \bbsengine6\template\plugin — Smarty plugin-dir registry and
 * resolver. Mirrors \bbsengine6\template's shape; the namespace
 * nesting reflects that plugins and templates are different
 * things with different engine paths and different cross-app
 * contributions, but the resolution mechanics are identical.
 *
 * \zoid6\plugin_extra() (in the root \zoid6 namespace) is
 * auto-registered at PRIORITY_APP_INTEGRATION. \bbsengine6\
 * template\plugin\extra() is the canonical engine plugin
 * contribution, self-registered at PRIORITY_ENGINE.
 */
namespace bbsengine6\template\plugin {

const PRIORITY_APP             = 'app';
const PRIORITY_APP_INTEGRATION = 'app-integration';
const PRIORITY_ENGINE          = 'engine';

static $_plugin_registry = null;
function _registry(): array {
    global $_plugin_registry;
    if ($_plugin_registry === null) {
        $_plugin_registry = [
            PRIORITY_APP             => [],
            PRIORITY_APP_INTEGRATION => [],
            PRIORITY_ENGINE          => [],
        ];
    }
    return $_plugin_registry;
}

function register(string $priority, callable $hook): void {
    _registry();
    global $_plugin_registry;
    if (!isset($_plugin_registry[$priority])) {
        throw new \RuntimeException(
            "bbsengine6\\template\\plugin\\register: unknown priority '$priority'. "
          . "Valid: app, app-integration, engine."
        );
    }
    if (!in_array($hook, $_plugin_registry[$priority], true)) {
        $_plugin_registry[$priority][] = $hook;
    }
}

function extra(): array {
    return [dirname(__DIR__) . "/smarty/"];
}

/**
 * Public wrapper. Delegates to \bbsengine6\template\normalize
 * with this namespace's registry and engine-fallback path.
 */
function normalize(mixed $raw): array {
    return \bbsengine6\template\normalize(
        $raw,
        \bbsengine6\template\plugin\_registry(),
        \bbsengine6\template\plugin\extra()[0],
        "bbsengine6\\template\\plugin"
    );
}

\bbsengine6\template\plugin\register(
    \bbsengine6\template\plugin\PRIORITY_ENGINE,
    '\bbsengine6\template\plugin\extra'
);

if (function_exists('\zoid6\plugin_extra')) {
    \bbsengine6\template\plugin\register(
        \bbsengine6\template\plugin\PRIORITY_APP_INTEGRATION,
        '\zoid6\plugin_extra'
    );
}

} // namespace bbsengine6\template\plugin
?>
