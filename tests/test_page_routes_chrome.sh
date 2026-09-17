#!/usr/bin/env bash
# test_page_routes_chrome.sh
# Verifies that the page-namespace URIs routed through
# engine/router.php on the wwworg vhost return HTTP 200
# AND a response body that includes both the bbsengine.org
# chrome (pageheader + topbar + pagefooter) AND the
# page-specific body content.
#
# Pre-fix symptom: the request was 200 + text/html, but the
# body chrome (pageheader h1 "bbsengine.org", topbar div,
# pagefooter div) was followed by the literal
# "NEEDINFO:content" placeholder (page.tmpl's default block
# content) instead of the contact-us / credits body. For
# /about-us the response was a 404 because no template
# existed for the URI.
#
# Root cause had two parts:
#
#   1. The legacy templates (contact-us.tmpl in particular)
#      defined {block name="main"} but wwworg's page.tmpl
#      only defines {block name="content"}. A child block
#      whose name does not match any parent block is
#      silently ignored by Smarty, so the parent's default
#      placeholder ("NEEDINFO:content") rendered in the
#      body slot. The block-name flatness was introduced
#      in 2c818d8 ("Assign ENGINEURL in getsmarty") which
#      flattened the prior nested {content > main}
#      structure without updating the children.
#
#   2. engine/serve-tmpl.php::servePage() called
#      displaypage(["content" => $smarty->fetch($basename),
#      ...], "page.tmpl") -- but displaypage() ignores the
#      "pagetemplate" data key and renders the literal
#      $pagetemplate argument, which was "page.tmpl". So
#      page.tmpl rendered directly (showing its own
#      NEEDINFO:content placeholder); the rendered
#      $data.content was unreachable.
#
# The fix:
#
#   - contact-us.tmpl: {block name="main"} -> {block name="content"}.
#   - credits.tmpl: add {extends file="page.tmpl"} and
#     wrap the body in {block name="content"}...{/block}.
#   - about-us.tmpl: created (did not exist before).
#   - serve-tmpl.php::servePage(): call
#     displaypage($data, $basename) so Smarty's {extends} /
#     {block} machinery merges the child's content block
#     with page.tmpl's chrome. Mirrors the flow that
#     router_displayMarkdownFile() uses for
#     page-markdown.tmpl.
#
# The test verifies all three URIs end-to-end via the
# public endpoint, plus two build-host plumbing invariants
# that catch a partial-deploy regression where the template
# edit lands but serve-tmpl.php does not (or vice versa).

set -u

URL_BASE="https://www.bbsengine.org"
LOCAL_BBSENGINE6="/home/opencode/data/work/bbsengine6"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

probe() {
  # $1 = URL, $2 = output file
  curl -sS -o "$2" -w '%{http_code}' "$1" 2>/dev/null || echo "000"
}

# --- per-page checks ----------------------------------------------------
# Each URI must:
#   [a] return HTTP 200 (not 404 -- the pre-fix about-us case)
#   [b] include the bbsengine.org chrome (pageheader h1,
#       topbar div, pagefooter div) -- in the right order
#   [c] include the page-specific heading text in the body
#   [d] NOT include the NEEDINFO:content placeholder or the
#       chrome-shell signature of the pre-fix bug
#
# The pre-fix body for /contact-us was structurally:
#   <header id="pageheader">...</header>
#   <div id="topbar">...</div>
#   NEEDINFO:content
#   <footer id="pagefooter">...</footer>
# (one chrome shell around an empty placeholder). The
# regression check asserts NEEDINFO:content is absent AND
# the page heading is present.
#
echo "[1] /contact-us chrome"
TMPDIR_TEST=$(mktemp -d /tmp/page-routes-chrome.XXXXXX)
trap 'rm -rf "$TMPDIR_TEST"' EXIT
BODY_CONTACT="$TMPDIR_TEST/contact-us.html"
code=$(probe "$URL_BASE/contact-us" "$BODY_CONTACT")
bytes=$(wc -c < "$BODY_CONTACT" 2>/dev/null | tr -d ' ' || echo 0)
echo "    status: $code"
echo "    body:   $bytes bytes"

if [ "$code" = "200" ] && [ "$bytes" -gt 0 ]; then
  ok "/contact-us returned 200 with non-empty body"
else
  bad "/contact-us expected 200 with body, got $code ($bytes bytes) -- page route did not reach engine/router.php or the underlying serve-tmpl.php threw"
fi

if [ "$bytes" -gt 0 ] && [ -s "$BODY_CONTACT" ]; then
  # chrome components: pageheader h1, topbar div, pagefooter div
  pageheader_pos=$(grep -n -F '<header id="pageheader">' "$BODY_CONTACT" 2>/dev/null | head -1 | cut -d: -f1)
  topbar_pos=$(grep -n -F '<div id="topbar"' "$BODY_CONTACT" 2>/dev/null | head -1 | cut -d: -f1)
  pagefooter_pos=$(grep -n -F '<footer id="pagefooter"' "$BODY_CONTACT" 2>/dev/null | head -1 | cut -d: -f1)
  brand_pos=$(grep -n -F '<h1>bbsengine.org</h1>' "$BODY_CONTACT" 2>/dev/null | head -1 | cut -d: -f1)
  if [ -n "$pageheader_pos" ] && [ -n "$topbar_pos" ] && [ -n "$pagefooter_pos" ] \
     && [ -n "$brand_pos" ] \
     && [ "$pageheader_pos" -lt "$topbar_pos" ] \
     && [ "$topbar_pos" -lt "$pagefooter_pos" ]; then
    ok "/contact-us chrome is present and ordered (pageheader -> topbar -> pagefooter) with site brand h1"
  else
    bad "/contact-us chrome components missing or out of order (pageheader=$pageheader_pos topbar=$topbar_pos pagefooter=$pagefooter_pos brand=$brand_pos) -- Smarty did not merge page.tmpl with contact-us.tmpl"
  fi

  # page-specific body heading (NOT the chrome's site-brand h1)
  if grep -q -F '<h1>Contact Us</h1>' "$BODY_CONTACT" 2>/dev/null; then
    ok "/contact-us body contains <h1>Contact Us</h1> (page content merged into content block)"
  else
    bad "/contact-us body missing <h1>Contact Us</h1> -- the child template's content block did not replace the parent's NEEDINFO:content placeholder"
  fi

  # anti-placeholder sentinel
  if grep -q -F 'NEEDINFO:content' "$BODY_CONTACT" 2>/dev/null; then
    bad "/contact-us body still contains NEEDINFO:content placeholder -- the parent's default block content rendered instead of the child's body"
  else
    ok "/contact-us body does not contain NEEDINFO:content placeholder (child block replaced parent's default)"
  fi

  # anti-error sentinels
  err_markers=""
  for m in 'Page Not Found' 'router error' 'Unable to load template' 'Failed opening required' 'Fatal error'; do
    if grep -q -F "$m" "$BODY_CONTACT" 2>/dev/null; then
      err_markers="$err_markers '$m'"
    fi
  done
  if [ -z "$err_markers" ]; then
    ok "/contact-us body has no Smarty/PHP/router error markers"
  else
    bad "/contact-us body contains error marker(s):$err_markers -- the response is an error fallback, not a clean render"
  fi
fi
echo

echo "[2] /about-us chrome (template did not exist pre-fix; this MUST 200 now)"
BODY_ABOUT="$TMPDIR_TEST/about-us.html"
code=$(probe "$URL_BASE/about-us" "$BODY_ABOUT")
bytes=$(wc -c < "$BODY_ABOUT" 2>/dev/null | tr -d ' ' || echo 0)
echo "    status: $code"
echo "    body:   $bytes bytes"

if [ "$code" = "200" ] && [ "$bytes" -gt 0 ]; then
  ok "/about-us returned 200 with non-empty body (about-us.tmpl now exists)"
else
  bad "/about-us expected 200 with body, got $code ($bytes bytes) -- www/org/skin/tmpl/about-us.tmpl did not deploy to merlin, or the router_handlePage URI probe did not match"
fi

if [ "$bytes" -gt 0 ] && [ -s "$BODY_ABOUT" ]; then
  pageheader_pos=$(grep -n -F '<header id="pageheader">' "$BODY_ABOUT" 2>/dev/null | head -1 | cut -d: -f1)
  topbar_pos=$(grep -n -F '<div id="topbar"' "$BODY_ABOUT" 2>/dev/null | head -1 | cut -d: -f1)
  pagefooter_pos=$(grep -n -F '<footer id="pagefooter"' "$BODY_ABOUT" 2>/dev/null | head -1 | cut -d: -f1)
  if [ -n "$pageheader_pos" ] && [ -n "$topbar_pos" ] && [ -n "$pagefooter_pos" ] \
     && [ "$pageheader_pos" -lt "$topbar_pos" ] \
     && [ "$topbar_pos" -lt "$pagefooter_pos" ]; then
    ok "/about-us chrome is present and ordered"
  else
    bad "/about-us chrome components missing or out of order (pageheader=$pageheader_pos topbar=$topbar_pos pagefooter=$pagefooter_pos) -- Smarty did not merge page.tmpl with about-us.tmpl"
  fi
  if grep -q -F '<h1>About bbsengine</h1>' "$BODY_ABOUT" 2>/dev/null; then
    ok "/about-us body contains <h1>About bbsengine</h1>"
  else
    bad "/about-us body missing <h1>About bbsengine</h1> -- the child template's content block did not render"
  fi
  if grep -q -F 'NEEDINFO:content' "$BODY_ABOUT" 2>/dev/null; then
    bad "/about-us body contains NEEDINFO:content -- block-name alignment still broken for about-us.tmpl"
  else
    ok "/about-us body has no NEEDINFO:content placeholder"
  fi
fi
echo

echo "[3] /credits chrome (credits.tmpl did not extend page.tmpl pre-fix)"
BODY_CREDITS="$TMPDIR_TEST/credits.html"
code=$(probe "$URL_BASE/credits" "$BODY_CREDITS")
bytes=$(wc -c < "$BODY_CREDITS" 2>/dev/null | tr -d ' ' || echo 0)
echo "    status: $code"
echo "    body:   $bytes bytes"

if [ "$code" = "200" ] && [ "$bytes" -gt 0 ]; then
  ok "/credits returned 200 with non-empty body"
else
  bad "/credits expected 200 with body, got $code ($bytes bytes)"
fi

if [ "$bytes" -gt 0 ] && [ -s "$BODY_CREDITS" ]; then
  pageheader_pos=$(grep -n -F '<header id="pageheader">' "$BODY_CREDITS" 2>/dev/null | head -1 | cut -d: -f1)
  topbar_pos=$(grep -n -F '<div id="topbar"' "$BODY_CREDITS" 2>/dev/null | head -1 | cut -d: -f1)
  pagefooter_pos=$(grep -n -F '<footer id="pagefooter"' "$BODY_CREDITS" 2>/dev/null | head -1 | cut -d: -f1)
  if [ -n "$pageheader_pos" ] && [ -n "$topbar_pos" ] && [ -n "$pagefooter_pos" ] \
     && [ "$pageheader_pos" -lt "$topbar_pos" ] \
     && [ "$topbar_pos" -lt "$pagefooter_pos" ]; then
    ok "/credits chrome is present and ordered"
  else
    bad "/credits chrome components missing or out of order (pageheader=$pageheader_pos topbar=$topbar_pos pagefooter=$pagefooter_pos) -- credits.tmpl is not extending page.tmpl"
  fi
  if grep -q -F '<h1>Site Credits</h1>' "$BODY_CREDITS" 2>/dev/null; then
    ok "/credits body contains <h1>Site Credits</h1> (credits.tmpl now extends page.tmpl)"
  else
    bad "/credits body missing <h1>Site Credits</h1>"
  fi
  if grep -q -F 'NEEDINFO:content' "$BODY_CREDITS" 2>/dev/null; then
    bad "/credits body contains NEEDINFO:content -- credits.tmpl not extending page.tmpl with {block name=\"content\"}"
  else
    ok "/credits body has no NEEDINFO:content placeholder"
  fi
fi
echo

# --- build-host plumbing invariants -------------------------------------
# The /contact-us /about-us /credits rewrite rule in
# www/org/htaccess-prod must target /engine/router.php so
# these URIs dispatch into the router_handlePage handler
# chain. A missing/wrong rule would cause the URIs to 404
# (no other handler matches) or to be served by an
# unintended handler. The check is a precondition: a
# green [1]/[2]/[3] without this rule means the rule
# exists in merlin's running config but not in the
# source-of-truth (a future deploy would re-break these
# pages).
echo "[4] htaccess-prod routes /contact-us, /about-us, /credits to /engine/router.php"
HTACCESS="$LOCAL_BBSENGINE6/www/org/htaccess-prod"
if [ ! -f "$HTACCESS" ]; then
  bad "local $HTACCESS missing"
else
  # Three patterns are acceptable: one consolidated rule
  # with all three slugs in an alternation group
  # (^(contact-us|about-us|credits)[/]?$), or three
  # individual rules with the same redirect target. The
  # check extracts all RewriteRules targeting
  # /engine/router.php and asserts that the union of
  # their pattern slugs covers {contact-us, about-us,
  # credits}.
  page_slugs=$(grep -E '^[[:space:]]*RewriteRule' "$HTACCESS" 2>/dev/null \
               | awk '/\/engine\/router\.php/ {print}' \
               | grep -oE '\^(contact-us\|about-us\|credits|contact-us|about-us|credits)[^[:space:]]*' \
               | tr -d '^' \
               | sed -E 's/\[/\\[/g')
  # Simpler approach: check that a single rule exists
  # whose pattern covers all three slugs, OR that three
  # separate rules exist each matching one slug.
  consolidated_ok=false
  # Use grep -F (literal substring) for the alternation
  # pattern; the ERE-escaped parens are brittle when grep
  # is invoked from inside an $(...) substitution and the
  # backslashes have already been processed by the shell.
  if grep -E '^[[:space:]]*RewriteRule' "$HTACCESS" 2>/dev/null \
     | grep -qF '(contact-us|about-us|credits)' 2>/dev/null \
     && grep -E '^[[:space:]]*RewriteRule' "$HTACCESS" 2>/dev/null \
     | grep -qF '/engine/router.php?uri=' 2>/dev/null; then
    # Both patterns present somewhere in the RewriteRule
    # set; verify they appear on the same line.
    if grep -E '^[[:space:]]*RewriteRule' "$HTACCESS" 2>/dev/null \
       | grep -F '(contact-us|about-us|credits)' 2>/dev/null \
       | grep -qF '/engine/router.php?uri=' 2>/dev/null; then
      consolidated_ok=true
    fi
  fi
  contact_ok=false
  if grep -E '^[[:space:]]*RewriteRule' "$HTACCESS" 2>/dev/null \
     | grep -qF '^contact-us' 2>/dev/null; then
    contact_ok=true
  fi
  about_ok=false
  if grep -E '^[[:space:]]*RewriteRule' "$HTACCESS" 2>/dev/null \
     | grep -qF '^about-us' 2>/dev/null; then
    about_ok=true
  fi
  credits_ok=false
  if grep -E '^[[:space:]]*RewriteRule' "$HTACCESS" 2>/dev/null \
     | grep -qF '^credits' 2>/dev/null; then
    credits_ok=true
  fi
  if $consolidated_ok || ($contact_ok && $about_ok && $credits_ok); then
    ok "local htaccess-prod routes /contact-us, /about-us, /credits to /engine/router.php"
  else
    bad "local htaccess-prod rewrite for /contact-us, /about-us, /credits is missing or targets the wrong engine entry-point (consolidated=$consolidated_ok contact=$contact_ok about=$about_ok credits=$credits_ok)"
  fi
fi
echo

# The three templates must exist in the build-host's
# www/org/skin/tmpl/ tree. Missing files break the
# two-pass URI probe inside router_handlePage. The check
# catches a partial deploy where the engine edit lands
# but the template edit does not (or vice versa).
echo "[5] page templates present in build-host's www/org/skin/tmpl/"
for tmpl in contact-us.tmpl about-us.tmpl credits.tmpl; do
  if [ -f "$LOCAL_BBSENGINE6/www/org/skin/tmpl/$tmpl" ]; then
    ok "local www/org/skin/tmpl/$tmpl exists"
  else
    bad "local www/org/skin/tmpl/$tmpl missing -- the template must ship alongside the engine/serve-tmpl.php edit"
  fi
done

# contact-us.tmpl and credits.tmpl must both extend
# page.tmpl with {block name="content"}. A regression to
# {block name="main"} (pre-fix contact-us) would re-broke
# the chrome. A regression to no {extends} at all (pre-fix
# credits) would also re-broke the chrome.
for tmpl in contact-us.tmpl credits.tmpl; do
  path="$LOCAL_BBSENGINE6/www/org/skin/tmpl/$tmpl"
  if [ -f "$path" ]; then
    if grep -qF '{extends file="page.tmpl"}' "$path" 2>/dev/null \
       && grep -qF '{block name="content"}' "$path" 2>/dev/null; then
      ok "$tmpl extends page.tmpl and defines {block name=\"content\"}"
    else
      bad "$tmpl does not match the required shape: {{extends file=\"page.tmpl\"}} and {{block name=\"content\"}} both required"
    fi
  fi
done
echo

# --- summary ------------------------------------------------------------
echo "=== summary ==="
echo "passed: $pass"
echo "failed: $fail"
if [ "$fail" -gt 0 ]; then
  echo
  echo "diagnosis:"
  printf "%b\n" "$diagnosis"
  echo
  echo "common remediation paths:"
  echo
  echo "  if [1]/[2]/[3] return 200 but body chrome is missing or"
  echo "  NEEDINFO:content is in the body:"
  echo "    -- the child template's block name does not match page.tmpl's"
  echo "       {block name=\"content\"}. Verify the template file on"
  echo "       merlin (or after 'make wwworg'): both must define"
  echo "       {{block name=\"content\"}} (NOT 'main')."
  echo
  echo "  if [1]/[2]/[3] return 200 with chrome but the page heading"
  echo "  (e.g. <h1>Contact Us</h1>) is missing:"
  echo "    -- the child template is not extending page.tmpl at all."
  echo "       credits.tmpl pre-fix had no {extends} line; the fix"
  echo "       adds one and wraps the body in {block name=\"content\"}."
  echo
  echo "  if [2] /about-us returns 404:"
  echo "    -- www/org/skin/tmpl/about-us.tmpl did not deploy. Run"
  echo "       'make wwworg' to push the org vhost's skin/tmpl/ tree."
  echo
  echo "  if [4] / htaccess check fails:"
  echo "    -- the /contact-us /about-us /credits rewrite is missing or"
  echo "       targets a different /engine/router.php install. The"
  echo "       target must be the vhost's per-vhost install at"
  echo "       /engine/router.php (not /router.php)."
  echo
  echo "  if [5] / template file checks fail:"
  echo "    -- run 'make wwworg' to push the local www/org/skin/tmpl/"
  echo "       tree to /srv/www/vhosts/www.bbsengine.org/html/skin/tmpl/."
  echo "       Each template must define {{block name=\"content\"}}."
  echo
  echo "to re-run: $0"
  exit 1
fi
echo
echo "all checks passed; /contact-us, /about-us, /credits return 200 with chrome + body."
exit 0
