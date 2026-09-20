<?php
/**
 * serve-tmpl.php - Render Smarty .tmpl content pages.
 *
 * Procedural module: top-level functions, no class. The
 * router (engine/router.php) is the single HTTP dispatch
 * surface for this vhost. serve-tmpl.php adds
 * router_handlePage() and a servePage() library function.
 *
 * htaccess-prod rewrites /contact-us, /about-us, /credits
 * to /engine/router.php?uri=$1, which the router passes to
 * router_handlePage() as a URI string. The handler matches
 * by trying <filename>.tmpl then <filename> as-is against
 * DOCUMENTROOT/skin/tmpl/, mirroring how router_handleMarkdown
 * probes .md.
 *
 * Path-traversal guard: realpath() containment + is_file() +
 * .tmpl extension check, same defense as engine/serve-md.php.
 *
 * @since 2026-09-16
 */

namespace bbsengine6\servepage {

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once("engine.php");
require_once("session.php");

// @since 2026-09-19 — ROUTER_RENDERED sentinel (see
// engine/router.php for rationale). serve-tmpl.php is loaded
// before router.php defines the constant, so define it here
// too if missing. Same define-guard pattern router.php uses.
if (!defined('ROUTER_RENDERED')) {
  define('ROUTER_RENDERED', 'ROUTER_RENDERED');
}

/**
 * Render $relpath under $basedir as a Smarty .tmpl page.
 * Library form. Also called internally by router_handlePage().
 *
 * @param string $basedir  Absolute base directory.
 * @param string $relpath  File path relative to $basedir
 *                         (e.g. "contact-us.tmpl").
 * @return string|false    "" on successful render (displaypage
 *                         echoes the HTML), false on validation
 *                         failure (caller emits 404).
 */
function servePage(string $basedir, string $relpath): string|false
{
  $realbasedir = realpath($basedir);
  if ($realbasedir === false)
  {
    return false;
  }
  $realbasedir = rtrim($realbasedir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR;

  $candidate = $realbasedir . $relpath;
  $realfile  = realpath($candidate);

  if ($realfile === false
      || strpos($realfile, $realbasedir) !== 0
      || !is_file($realfile)
      || pathinfo($realfile, PATHINFO_EXTENSION) !== 'tmpl')
  {
    return false;
  }

  $smarty   = \bbsengine6\getsmarty();
  $basename = basename($realfile);
  if (!$smarty->templateExists($basename))
  {
    return false;
  }

  // @since 2026-09-17 — display the CHILD template, not
  // page.tmpl. The previous implementation fetched $basename
  // into a string and stuffed it into $data.content, then
  // called displaypage(..., "page.tmpl") -- but page.tmpl
  // (www/org/skin/tmpl/page.tmpl) defines
  // {block name="content"}NEEDINFO:content{/block} and never
  // references $data.content, so the result was a chrome
  // shell with the literal "NEEDINFO:content" in the body.
  //
  // The fix: pass $basename as the $pagetemplate argument
  // so Smarty treats the child template as the entry point.
  // Smarty's {extends} / {block} machinery then merges the
  // child's content block with page.tmpl's chrome, which
  // is the same flow router_displayMarkdownFile uses for
  // page-markdown.tmpl.
  $data = ["pagetemplate" => $basename];
  \bbsengine6\displaypage($data, $basename);
  // @since 2026-09-19 — return ROUTER_RENDERED sentinel; see
  // engine/router.php for the rationale (replaces implicit
  // empty-string-as-success contract). Leading-backslash
  // because servePage() is in `namespace bbsengine6\servepage;`,
  // so a bare ROUTER_RENDERED would resolve to
  // bbsengine6\servepage\ROUTER_RENDERED (which doesn't exist).
  return \ROUTER_RENDERED;
}

/**
 * Router handler for page-namespace URIs (bare URIs that
 * resolve to a Smarty template under DOCUMENTROOT/skin/tmpl/).
 *
 * Two-pass extension probe (try <uri>.tmpl first, then
 * <uri> as-is). Unlike router_handleMarkdown -- which used
 * to do the same shape but no longer does, because the
 * HTTP entry-point strips ".md" once and the markdown
 * handler therefore only needs the bare probe -- the
 * ".tmpl" probe here is still required: htaccess rewrites
 * bare slugs (e.g. /contact-us) into the router with no
 * extension, so the handler has to append ".tmpl" itself.
 *
 * Returns ROUTER_NEXT to defer to the next handler,
 * anything else short-circuits the chain.
 *
 * Defensive `..` and NUL-byte check on the URI before any
 * filesystem work; the realpath() containment check inside
 * servePage() is the authoritative guard against traversal.
 *
 * @param string $uri  URI path component (e.g. "/contact-us"
 *                     when htaccess rewrites /contact-us to
 *                     /engine/router.php?uri=contact-us).
 * @return string|false|ROUTER_NEXT  "" on render (displaypage
 *                                   already echoed the body);
 *                                   ROUTER_NEXT to fall through.
 */
function router_handlePage(string $uri)
{
  \bbsengine6\util\logentry("servepage.handlePage: uri=" . var_export($uri, true));

  $reluri = ltrim($uri, '/');
  if ($reluri === ''
      || str_contains($reluri, '..')
      || str_contains($reluri, "\0"))
  {
    return ROUTER_NEXT;
  }

  $docroot = defined('\config\DOCUMENTROOT') ? \config\DOCUMENTROOT : '';
  if ($docroot === '')
  {
    \bbsengine6\util\logentry("servepage.handlePage: DOCUMENTROOT not configured", "warning");
    return ROUTER_NEXT;
  }

  $skin = rtrim($docroot, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . 'skin/tmpl/';

  // two-pass extension probe:
  //   pass 1: append .tmpl (canonical "URI has no extension" case)
  //   pass 2: try the URI as-is (URI already carries an extension)
  //
  // @since 2026-09-19 — this is the ONLY handler in the
  // registry that still does a two-pass extension probe.
  // router_handleMarkdown dropped its "$uri . '.md'" branch
  // (dead code) because the HTTP entry-point strips ".md"
  // once at the top of the script (see engine/router.php
  // line ~724). ".tmpl" is NOT stripped at the entry-point,
  // so the handler still has to append it itself.
  foreach ([$reluri . '.tmpl', $reluri] as $rel)
  {
    $realbase = realpath($skin);
    if ($realbase === false)
    {
      continue;
    }
    $realbase = rtrim($realbase, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR;
    $realfile = realpath($realbase . $rel);

    if ($realfile !== false
        && strpos($realfile, $realbase) === 0
        && is_file($realfile)
        && pathinfo($realfile, PATHINFO_EXTENSION) === 'tmpl')
    {
      try
      {
        $rendered = servePage($skin, $rel);
        return ($rendered === false) ? ROUTER_NEXT : $rendered;
      }
      catch (\Throwable $e)
      {
        \bbsengine6\util\logentry('servepage.handlePage: render failed: ' . $e->getMessage(), 'error');
        return ROUTER_NEXT;
      }
    }
  }

  return ROUTER_NEXT;
}

} /* namespace bbsengine6\servepage */
