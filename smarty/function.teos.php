<?php

// @since 2026-09-29 — config-less load.
//
// Previous behavior required config.php / database.php / engine.php
// via include_path, which broke silently under mod_env +
// mod_rewrite + mod_proxy_fcgi combos where VHOSTDOCROOT did not
// propagate to FPM. The journal for the failing /rec/... requests
// showed include_path without any /srv/www/vhosts/.../html entry,
// and the bare require_once() surfaced as `Failed to open stream:
// No such file or directory` in /var/log.
//
// Two changes fix it:
//
//   1. BBSENGINEROOT (env, set in vhost htaccess) names the
//      engine install so util.php can be required absolutely
//      without hardcoding "/srv/www/bbsengine6" here.
//   2. {teos} re-uses the parent Smarty instance
//      ($template->smarty) instead of constructing a fresh one
//      via \bbsengine6\getsmarty(). The parent Smarty was
//      already created by the upstream caller (engine/router.php
//      or a legacy teos entry point) with all per-vhost
//      SMARTY* dirs wired up. Re-using it means this plugin
//      needs no engine-state at all.
//
// TEOSURL is read via \bbsengine6\util\env() per the AGENTS.md
// "TEOSDIR resolution contract". The default is a NEEDINFO
// marker rather than empty string so missing config surfaces
// visibly in the rendered HTML and is greppable in production
// logs.

function bbsengine6_teos_resolve_root(): string
{
  // @since 2026-09-30 — multi-source resolution. The pre-existing
  // single-source check (`getenv('BBSENGINEROOT')` only) threw a
  // RuntimeException whenever the env var wasn't visible to the PHP
  // process — which happened in production on FPM pools that don't
  // propagate Apache's SetEnv directives (the same FPM-env-stripping
  // issue documented in AGENTS.md's "TEOSDIR resolution contract"
  // section). The throw surfaced visibly in the rendered output for
  // any blurb or folder page that included youarehere.tmpl -> {teos}
  // after the 2026-09-30 breadcrumb-traversal fixes made
  // $data.breadcrumbs non-empty for those pages (previously an empty
  // breadcrumb list short-circuited the include, masking the missing
  // env var).
  //
  // Resolution order, top to bottom, first hit wins:
  //
  //   1. getenv('BBSENGINEROOT')     — the documented primary path
  //                                     (set via SetEnv BBSENGINEROOT
  //                                     in each vhost's htaccess-prod).
  //   2. defined('BBSENGINEROOT')    — fallback for vhosts that
  //                                     define the constant in their
  //                                     config.php (matches the pattern
  //                                     used for TEOSURL at line 118).
  //   3. dirname(__DIR__)             — derive from this file's own
  //                                     location. function.teos.php
  //                                     always lives at
  //                                     <engine_root>/smarty/function.teos.php,
  //                                     so the parent of __DIR__ is the
  //                                     engine root. Works regardless of
  //                                     FPM env propagation, and avoids
  //                                     the AGENTS.md-banned
  //                                     hardcoded-prod-path constant
  //                                     pattern (see TEOSDIR resolution
  //                                     contract for why that's
  //                                     forbidden).
  //   4. plugin_dir walk              — for the rare case where this
  //                                     file is loaded from a stale or
  //                                     relocated copy (e.g. a vhost's
  //                                     own smarty/ directory). Walk
  //                                     Smarty's plugin_dir list and
  //                                     check if any plugin dir has a
  //                                     sibling ../php/util.php; if so,
  //                                     the engine root is the parent of
  //                                     that plugin dir's parent.
  //
  // Only after all four paths fail do we throw — and the exception
  // message names each path tried so the operator can diagnose which
  // step is missing in their deployment.

  // 1. env var (canonical contract)
  $root = getenv('BBSENGINEROOT');
  if (is_string($root) && $root !== '' && is_dir($root)) {
    return rtrim($root, '/');
  }
  $tried = ['getenv(BBSENGINEROOT)=' . var_export($root, true)];

  // 2. constant fallback (matches TEOSURL pattern at line 118)
  if (defined('BBSENGINEROOT')) {
    $c = constant('BBSENGINEROOT');
    if (is_string($c) && $c !== '' && is_dir($c)) {
      return rtrim($c, '/');
    }
    $tried[] = 'defined(BBSENGINEROOT)=' . var_export($c, true);
  } else {
    $tried[] = 'defined(BBSENGINEROOT)=undefined';
  }

  // 3. walk-up from this file's own location
  //    __DIR__ = <engine_root>/smarty, so dirname(__DIR__) = engine_root
  $candidate = dirname(__DIR__);
  if (is_dir($candidate . '/php/util.php') || is_file($candidate . '/php/util.php')) {
    return rtrim($candidate, '/');
  }
  $tried[] = 'dirname(__DIR__)=' . var_export($candidate, true);

  // 4. plugin_dir walk — for the rare case where this file is
  //    loaded from a stale or relocated copy (e.g. a vhost's own
  //    smarty/ directory). We don't have a Smarty instance at this
  //    layer (function.teos.php is loaded at compile-time before any
  //    template renders), so we can't call Smarty::getPluginsDir()
  //    directly — that method is an instance method, not static.
  //    Instead we probe the canonical install location. This is a
  //    last-resort fallback for relocated copies; the primary paths
  //    (env, constant, walk-up) remain the canonical resolution. The
  //    canonical path is a fallback (not a contract) — deployments
  //    that ship BBSENGINEROOT elsewhere should publish the env var
  //    or define the constant.
  $candidates = [
    '/srv/www/bbsengine6/smarty',
    '/srv/www/bbsengine6',
  ];
  $triedCandidates = [];
  foreach ($candidates as $plugindir) {
    if (!is_dir($plugindir)) {
      continue;
    }
    $engineRoot = dirname($plugindir);
    $triedCandidates[] = $engineRoot;
    if (is_dir($engineRoot . '/php')) {
      return rtrim($engineRoot, '/');
    }
  }
  $tried[] = 'plugin_dir_walk=tried [' . implode(', ', $triedCandidates) . ']';

  throw new \RuntimeException(
    'bbsengine6/smarty/function.teos: BBSENGINEROOT could not be resolved. '
    . 'Tried: ' . implode('; ', $tried) . '. '
    . 'Set BBSENGINEROOT in the vhost htaccess-prod via '
    . '`SetEnv BBSENGINEROOT <abs-path>` (e.g. "/srv/www/bbsengine6"), '
    . 'or define it as a constant in the vhost config.php.'
  );
}

function buildpluginfilepath($smarty, $name)
{
  foreach ($smarty->getPluginsDir() as $plugindir)
  {
    $p = $plugindir.DIRECTORY_SEPARATOR.basename($name);
    if (file_exists($p))
    {
      return $p;
    }
  }
  return null;
}

function smarty_function_teos($options, Smarty_Internal_Template $template)
{
  // Resolve util.php via the established bbsengine6 include_path
  // pattern (mirrors engine/router.php's load order). Loading
  // php/bootstrap.php first puts /srv/www/bbsengine6/php/ on
  // include_path, so the bare-name require_once('util.php') below
  // resolves. This is the same convention bootstrap.php itself uses
  // to resolve Log.php (line 59) and Markdown/Parsedown elsewhere in
  // the engine.
  //
  // Resolving lazily inside the function (not at file scope) means
  // missing BBSENGINEROOT surfaces as a caught RuntimeException
  // inside the template-render path -- visible to the calling
  // handler's try/catch -- instead of an uncaught fatal at
  // plugin-load time.
  $bbsengine6_root = bbsengine6_teos_resolve_root();
  require_once($bbsengine6_root . '/php/bootstrap.php');
  require_once('util.php');

  require_once(buildpluginfilepath($template->smarty, "modifier.escape.php"));
  require_once(buildpluginfilepath($template->smarty, "modifier.wpprop.php"));

  $path = isset($options["path"]) ? $options["path"] : null;
  $title = isset($options["title"]) ? $options["title"] : null;
  $itemprop = isset($options["itemprop"]) ? $options["itemprop"] : false;
  // @since 2026-09-30 — nolink=true renders the crumb title as plain
  // text (a "you are here" marker) instead of an <a> link. Used by
  // teos-breadcrumbs.tmpl's $b@last branch when the caller passed
  // linklast=true via youarehere.tmpl. Default false preserves the
  // historical always-linked behavior for every existing caller.
  $nolink = !empty($options["nolink"]);
  // @since 2026-09-30 — when the caller marks the crumb as the
  // root (e.g. teos-breadcrumbs.tmpl's $b@first branch), suppress
  // the path-segment uri synthesis and let TEOSURL stand alone.
  // Without this, a root crumb with path='teros' renders href
  // /teos/teros/ because the per-segment implode always emits
  // 'teros/'. Used by the "you are here" trail where the root
  // should land at TEOSURL + '/' regardless of its internal
  // ltree identifier (per-vhost htaccess-prod may declare
  // TEOSURL=/handbook/<v>/, in which case the root href is
  // /handbook/<v>/, never /handbook/<v>/teros/).
  $is_root = !empty($options["is_root"]);

  // Path is a dot-separated label: "rec.arts.tv.the-a-team"
  $segments = array_values(array_filter(explode(".", $path)));
  $uriSegments = array_map(function($s) { return str_replace("_", "-", $s); }, $segments);

  // Root crumb: emit a bare trailing slash so the template's
  // {$smarty.const.TEOSURL}{$uri} produces TEOSURL + '/' (e.g.
  // /teos/, not /teos/teros/). Non-root crumbs keep the
  // path-segment synthesis.
  $uri = $is_root ? "" : implode("/", $uriSegments) . "/";

  if ($title === null) {
    if (count($uriSegments) > 0) {
      $title = end($uriSegments);
    } else {
      $title = $path;
    }
    $title = str_replace(["-", "_"], " ", $title);
  }

  $title = smarty_modifier_escape($title);
  $title = smarty_modifier_wpprop($title);

  // Re-use the parent Smarty instance. The upstream caller
  // (engine/router.php or a legacy teos entry point) already
  // constructed it with all per-vhost SMARTY* dirs, so we just
  // assign our locals and fetch.
  //
  // TEOSURL is exposed as a PHP constant so the template's
  // {$smarty.const.TEOSURL} syntax reads it. The defined() guard
  // respects any value the vhost already defined (legacy teos
  // config-prod.php uses `define("TEOSURL", \config\TEOSURL)`).
  // Only fall through to env() when no vhost value is present.
  $teos_url = \bbsengine6\util\env(
      'TEOSURL',
      'NEEDINFO:function.teos.100:TEOSURL'
  );
  if (!defined('TEOSURL')) {
      define('TEOSURL', $teos_url);
  }
  $tmpl = $template->smarty;
  $tmpl->assign("uri", $uri);
  $tmpl->assign("title", $title);
  $tmpl->assign("itemprop", $itemprop);
  $tmpl->assign("nolink", $nolink);

  return $tmpl->fetch("function.teos.tmpl");
}
?>
