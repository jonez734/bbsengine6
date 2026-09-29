<?php

// @since 2026-09-29 — config-less load.
//
// Previous behavior required config.php / database.php / engine.php
// via include_path, which broke silently under mod_env +
// mod_rewrite + mod_proxy_fcgi combos where VHOSTDOCROOT /
// VHOSTCONFIG did not propagate to FPM. The journal for the
// failing /rec/... requests showed include_path without any
// /srv/www/vhosts/.../html entry, and the bare require_once()
// surfaced as `Failed to open stream: No such file or directory`
// in /var/log.
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
  $root = getenv('BBSENGINEROOT');
  if (!is_string($root) || $root === '' || !is_dir($root)) {
    throw new \RuntimeException(
      'bbsengine6/smarty/function.teos: BBSENGINEROOT env var is required '
      . 'and must point to the bbsengine6 install directory (e.g. '
      . '"/srv/www/bbsengine6"). Set it in the vhost htaccess-prod via '
      . '`SetEnv BBSENGINEROOT <abs-path>`. Got: '
      . var_export($root, true)
    );
  }
  return rtrim($root, '/');
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

  // Path is a dot-separated label: "rec.arts.tv.the-a-team"
  $segments = array_values(array_filter(explode(".", $path)));
  $uriSegments = array_map(function($s) { return str_replace("_", "-", $s); }, $segments);

  $uri = implode("/", $uriSegments) . "/";

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

  return $tmpl->fetch("function.teos.tmpl");
}
?>
