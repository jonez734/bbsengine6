<?php
/**
 * vhostconfig.php — VHOSTCONFIG resolver for the bbsengine6 router.
 *
 * @since 2026-09-24 — extracted from engine/router.php so it can be
 * required and tested in isolation, without dragging in engine.php,
 * util.php, and the rest of the router's bootstrap chain.
 *
 * @since 2026-10-XX — RESTORED. The Sep 29 refactor (02eebac) removed
 * this resolver on the rationale that VHOSTDOCROOT + include_path was
 * sufficient. In production on merlin, the include_path-only chain
 * fails when Apache's SetEnv directives don't propagate to PHP-FPM
 * (mod_proxy_fcgi + FPM clear_env=yes, the FPM default since PHP 7+):
 * VHOSTDOCROOT never reaches the FPM pool, bootstrap.php's namespace
 * block at php/bootstrap.php:50-57 doesn't prepend the vhost root to
 * include_path, bbsengine6config.php:51's
 * stream_resolve_include_path("config.php") returns false, the vhost's
 * config.php is never loaded, and \config\SMARTYTEMPLATESDIR is
 * undefined — which makes getsmarty() throw on the first chrome render
 * or on the router_handleError fallback path.
 *
 * The fix is to restore this resolver as a robust fallback that does
 * NOT depend on FPM env propagation:
 *
 *   1. VHOSTCONFIG env var (preferred) — set by every htaccess-prod
 *      in the repo as `SetEnv VHOSTCONFIG <abs-path>`. Honors Apache
 *      mod_env + AllowOverride FileInfo prerequisites (same as
 *      VHOSTDOCROOT). When VHOSTCONFIG reaches FPM this is a single
 *      is_file() + require_once; no include_path involved.
 *   2. SCRIPT_FILENAME fallback — walk up from the handler's location
 *      (.../html/engine/router.php) to .../html/ and probe known vhost
 *      subdirs (config.php at the root, teos/, org/, com/,
 *      bbsengine.org/). Works without ANY env vars because
 *      $_SERVER['SCRIPT_FILENAME'] is set by Apache + FPM
 *      infrastructure regardless of clear_env config, and is_file()
 *      is a filesystem-only check.
 *   3. Both fail — return false. The caller logs a warning and lets
 *      engine.php's getsmarty() throw the existing "not configured"
 *      RuntimeException. No regression; the failure mode matches the
 *      pre-fix behavior on misconfigured vhosts.
 *
 * Resolution happens via bbsengine6\util\env() so the read order is
 * the canonical getenv() -> defined() -> default pipeline (see
 * AGENTS.md "TEOSDIR resolution contract"). The default sentinel
 * "NEEDINFO.VHOSTCONFIG.router_resolve_vhost_config" matches the
 * pre-removal log shape, so any existing logentry probes that grep for
 * "NEEDINFO.VHOSTCONFIG" keep working.
 *
 * The function lives in the bbsengine6\router namespace to match the
 * rest of engine/router.php's symbols.
 */

namespace bbsengine6\router;

require_once("util.php");

/**
 * Resolve and require the vhost's config.php.
 *
 * @return string|false Absolute path of the loaded vhost config, or
 *                      false if none was resolvable.
 */
function router_resolve_vhost_config(): string|false
{
    // 1. VHOSTCONFIG env var (preferred; set by htaccess-prod).
    $envConfig = \bbsengine6\util\env('VHOSTCONFIG', "NEEDINFO.VHOSTCONFIG.router_resolve_vhost_config");

    \bbsengine6\util\logentry("envconfig=".var_export($envConfig, true));

    if (is_string($envConfig)
        && $envConfig !== ''
        && $envConfig !== "NEEDINFO.VHOSTCONFIG.router_resolve_vhost_config"
        && is_file($envConfig)) {
        require_once($envConfig);
        return $envConfig;
    }

    // 2. SCRIPT_FILENAME fallback. .../html/engine/router.php walks
    // up to .../html/, then probes known vhost subdirs for config.php.
    // Doesn't depend on any FPM env vars — uses $_SERVER['SCRIPT_FILENAME']
    // (set by Apache+FPM infrastructure) and is_file() (filesystem-only).
    $script = $_SERVER['SCRIPT_FILENAME'] ?? '';
    if (is_string($script) && $script !== '') {
        // dirname() of /.../html/engine/router.php -> /.../html/engine
        // dirname() again -> /.../html
        $htmlDir = dirname(dirname($script));
        if (is_dir($htmlDir)) {
            // Known vhost config locations under html/. Order matters:
            // first match wins.
            $candidates = [
                $htmlDir . '/config.php',                  // flat vhost layout (handbook)
                $htmlDir . '/teos/config.php',             // teos
                $htmlDir . '/org/config.php',              // org vhost (legacy alias)
                $htmlDir . '/com/config.php',              // com vhost (legacy alias)
                $htmlDir . '/bbsengine.org/config.php',
            ];
            foreach ($candidates as $cand) {
                if (is_file($cand)) {
                    require_once($cand);
                    return $cand;
                }
            }
        }
    }

    return false;
}
