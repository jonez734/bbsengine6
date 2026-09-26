<?php
/**
 * vhostconfig.php — VHOSTCONFIG resolution for the bbsengine6 router.
 *
 * @since 2026-09-24 — extracted from engine/router.php so it can be
 * required and tested in isolation, without dragging in engine.php,
 * util.php, and the rest of the router's bootstrap chain.
 *
 * Resolution contract (in order):
 *   1. VHOSTCONFIG env var (absolute path) — recommended; set by
 *      each vhost's htaccess-prod via `SetEnv VHOSTCONFIG <abs-path>`.
 *      Honors Apache mod_env + AllowOverride FileInfo prerequisites,
 *      same as VHOSTDOCROOT (see htaccess-prod for rationale).
 *   2. SCRIPT_FILENAME fallback — walk up from the handler's location
 *      (.../html/engine/router.php) to .../html/ and probe known vhost
 *      subdirs (config.php at the root, teos/, org/, com/,
 *      bbsengine.org/). Useful for setups that can't or don't export
 *      VHOSTCONFIG (CLI tests, partial deploys).
 *   3. Nothing resolvable — return false. The caller logs a warning
 *      and lets engine.php's getsmarty() throw the existing "not
 *      configured" RuntimeException. No regression; the failure mode
 *      matches the pre-fix behavior.
 *
 * The resolved config is loaded with require_once (so calling this
 * twice with the same path is a no-op) and the absolute path is
 * returned for caller logging.
 *
 * The function lives in the bbsengine6\router namespace to match
 * the rest of engine/router.php's symbols.
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

    \bbsengine6\util\logentry("engine.router.router_resolve_vhost_config.100: envconfig=".var_export($envconfig, true));

    if (is_string($envConfig) && $envConfig !== '' && is_file($envConfig)) {
        require_once($envConfig);
        return $envConfig;
    }

    // 2. SCRIPT_FILENAME fallback. .../html/engine/router.php walks
    // up to .../html/, then probes known vhost subdirs for config.php.
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
