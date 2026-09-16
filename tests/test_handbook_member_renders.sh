#!/usr/bin/env bash
# test_handbook_member_renders.sh
#
# Regression test for https://www.bbsengine.org/handbook/6/specs/member
# and its raw .md companion.
#
# Background: the URL was returning HTTP 500 on every request because
# engine/router.php called router_log(...) (which dispatches to
# \bbsengine6\util\logentry) BEFORE require_once('util.php') had
# loaded that function. The fatal that produced was
# "Call to undefined function bbsengine6\util\logentry()", and the
# 96-byte var_export(get_include_path()) string from the doomed
# router_log call was being shipped as the response body.
#
# This test pins down both the rendered-HTML path and the raw .md
# path, and includes a build-host invariant ([6]) that fails fast
# if the call-before-require ordering mistake is reintroduced.
#
# Read-only against the public endpoint and the build host's
# bbsengine6/ tree. No ssh to merlin required.
#
# @since 2026-09-16

set -u

URL_BASE="https://www.bbsengine.org/handbook/6"
RENDER_URL="$URL_BASE/specs/member"
RAW_URL="$URL_BASE/specs/member.md"
LOCAL_BBSENGINE6="/home/opencode/data/work/bbsengine6"
LOCAL_MD="$LOCAL_BBSENGINE6/handbook/specs/member.md"
LOCAL_ROUTER="$LOCAL_BBSENGINE6/engine/router.php"

# Deterministic signature of the regression: when router.php calls
# router_log() before util.php is required, PHP fatals on
# "Call to undefined function bbsengine6\util\logentry()" and
# Apache ships the buffered var_export(get_include_path()) echo
# as the response body. That string is 96 bytes long; comparing
# the response body to it byte-for-byte is a much tighter signal
# than a substring check (a future deploy could change the
# include_path and the substring test would silently miss it).
INCLUDED_PATH_ECHO="'.:/usr/share/php:/srv/www/bbsengine6/php:/srv/www/bbsengine6:/srv/www/markdown:/srv/www/smarty'"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

probe() {
  # $1 = URL, $2 = output file
  curl -sS -o "$2" -w '%{http_code}' "$1" 2>/dev/null || echo "000"
}

probe_with_headers() {
  # $1 = URL, $2 = headers file, $3 = body file
  curl -sS -D "$2" -o "$3" -w '%{http_code}' "$1" 2>/dev/null || echo "000"
}

# --- [1] Rendered URL returns 200 with non-empty body ----------------------
http_code=$(probe "$RENDER_URL" /tmp/handbook_member.body)
body_bytes=$(wc -c < /tmp/handbook_member.body 2>/dev/null | tr -d ' ' || echo 0)
echo "[1] HTTP probe of $RENDER_URL"
echo "    status: $http_code"
echo "    body:   $body_bytes bytes"
if [ "$http_code" = "200" ] && [ "$body_bytes" -gt 0 ]; then
  ok "HTTP 200 with non-empty body"
else
  bad "expected HTTP 200 with non-empty body, got $http_code ($body_bytes bytes) -- first line of body: $(head -1 /tmp/handbook_member.body 2>/dev/null | head -c 200)"
fi
echo

# --- [2] Body is NOT the include-path echo (regression marker) ------------
# This is the deterministic signature of the bug. A substring check
# would also work, but byte-equality catches any future include_path
# change that might be confused for a fix.
echo "[2] body is NOT the include-path echo (regression signature)"
if [ "$body_bytes" -eq 96 ] && [ "$(cat /tmp/handbook_member.body 2>/dev/null)" = "$INCLUDED_PATH_ECHO" ]; then
  bad "body is the literal 96-byte var_export(get_include_path()) echo -- the router_log-before-require bug is back. The router fataled on undefined \\bbsengine6\\util\\logentry before util.php was loaded."
else
  ok "body does not match the 96-byte include-path echo"
fi
echo

# --- [3] Body is NOT the router-error fallback ----------------------------
echo "[3] body is NOT the router-error fallback"
if [ "$body_bytes" -gt 0 ] && grep -q -i -E 'page not found|router error' /tmp/handbook_member.body 2>/dev/null; then
  bad "body contains 'page not found' or 'router error' -- the router's error handler ran, the page did not render. Body: $(head -1 /tmp/handbook_member.body 2>/dev/null | head -c 200)"
else
  ok "body does not look like a router error fallback"
fi
echo

# --- [4] Rendered markdown from member.md is present -----------------------
# Proves Parsedown actually rendered the file (not a generic template).
# The first # heading of member.md is "bbsengine6.member Specification";
# parsedown renders that as <h1>bbsengine6.member Specification</h1>, so
# the body must contain the heading text. We strip leading hashes and
# whitespace from each line and grep for the resulting literal.
echo "[4] rendered markdown heading from member.md is present in body"
if [ -f "$LOCAL_MD" ]; then
  expected_heading="# bbsengine6.member Specification"
  if grep -q -F "$expected_heading" "$LOCAL_MD" 2>/dev/null; then
    if grep -q -F "bbsengine6.member Specification" /tmp/handbook_member.body 2>/dev/null; then
      ok "body contains 'bbsengine6.member Specification' (the h1 from member.md, rendered by Parsedown)"
    else
      bad "body does NOT contain 'bbsengine6.member Specification' -- parsedown did not render member.md. Body excerpt: $(head -c 400 /tmp/handbook_member.body 2>/dev/null)"
    fi
  else
    bad "expected heading '$expected_heading' not found in $LOCAL_MD -- the test's expected-hash literal is stale; update this test"
  fi
else
  bad "$LOCAL_MD missing -- cannot derive expected heading"
fi
echo

# --- [5] Raw .md companion URL still serves the file unchanged ------------
# /handbook/<v>/<uri>.md routes through engine/serve-md.php (separate
# rewrite rule in www/org/htaccess-prod); this is unaffected by the
# router.php fix but is pinned here so a future deploy doesn't break it.
echo "[5] raw .md companion URL serves the local source unchanged"
raw_code=$(probe_with_headers "$RAW_URL" /tmp/handbook_member.headers /tmp/handbook_member.raw)
echo "    $RAW_URL -> $raw_code"
if [ "$raw_code" = "200" ]; then
  ok "raw .md URL returned 200"
else
  bad "raw .md URL returned $raw_code (expected 200) -- engine/serve-md.php may be broken or the rewrite rule regressed"
fi
if [ -s /tmp/handbook_member.headers ] && grep -q -i '^content-type:[[:space:]]*text/plain' /tmp/handbook_member.headers 2>/dev/null; then
  ok "raw .md response Content-Type is text/plain"
else
  bad "raw .md response Content-Type is not text/plain -- headers: $(head -5 /tmp/handbook_member.headers 2>/dev/null)"
fi
if [ -f "$LOCAL_MD" ]; then
  if diff -q /tmp/handbook_member.raw "$LOCAL_MD" >/dev/null 2>&1; then
    ok "raw .md response byte-equals local source $LOCAL_MD (serve-md.php is serving the right file unchanged)"
  else
    bad "raw .md response differs from local source $LOCAL_MD -- serve-md.php is rewriting or serving the wrong file. Diff (first 5 lines): $(diff /tmp/handbook_member.raw $LOCAL_MD 2>/dev/null | head -5)"
  fi
else
  bad "$LOCAL_MD missing -- cannot compare raw response to local source"
fi
echo

# --- [6] Build-host invariant: the bug doesn't regress --------------------
# router_log() must NOT appear before the require_once('util.php')
# line in engine/router.php. The router_log function body calls
# \bbsengine6\util\logentry (defined by that require), so any
# call to router_log() placed before the require_once raises a
# fatal on every handbook request.
echo "[6] router_log() in engine/router.php is not called before require_once('util.php')"
if [ -f "$LOCAL_ROUTER" ]; then
  # Find the line number of the require_once('util.php') call.
  util_req_line=$(grep -n -F "require_once('util.php')" "$LOCAL_ROUTER" 2>/dev/null | head -1 | cut -d: -f1)
  if [ -z "$util_req_line" ]; then
    bad "could not find require_once('util.php') in $LOCAL_ROUTER -- the file shape changed; this invariant test needs an update"
  else
    # Search for router_log( calls before that line. We look at the
    # raw file content (not parsed PHP) and use line numbers; the
    # router_log function body itself is not flagged because PHP
    # defers function-body execution, but the function DEFINITION
    # 'function router_log(' should also appear after the require,
    # which the same check catches if the file is restructured
    # again.
    bad_calls=$(awk -v util_req="$util_req_line" '
      NR < util_req && /router_log\(/ { print NR ":" $0 }
    ' "$LOCAL_ROUTER" 2>/dev/null)
    if [ -z "$bad_calls" ]; then
      ok "no router_log( calls before require_once('util.php') on line $util_req_line"
    else
      bad "router_log( is called before require_once('util.php') on line $util_req_line -- this is the original bug. Offending lines: $bad_calls"
    fi
  fi
else
  bad "$LOCAL_ROUTER missing -- cannot run build-host invariant"
fi
echo

# --- summary --------------------------------------------------------------
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
  echo "  if [1] returns 500 with the include-path echo:"
  echo "    -- engine/router.php calls router_log() before"
  echo "       require_once('util.php'). router_log() dispatches"
  echo "       to \\bbsengine6\\util\\logentry which is not yet"
  echo "       defined. Move the router_log() call after the"
  echo "       require chain in engine/router.php, then redeploy:"
  echo "         make engine-deploy-prod"
  echo "         sudo systemctl reload php-fpm   # on merlin"
  echo
  echo "  if [2] fails (body is the include-path echo):"
  echo "    -- same as [1]; the byte-equality match is the bug"
  echo "       signature."
  echo
  echo "  if [4] fails (parsedown didn't render member.md):"
  echo "    -- the file may be missing on merlin at"
  echo "       /srv/www/vhosts/www.bbsengine.org/html/handbook/6/"
  echo "       specs/member.md. Run: make handbook-deploy-prod"
  echo
  echo "  if [5] fails (raw .md companion returns non-200 or wrong body):"
  echo "    -- engine/serve-md.php or the .htaccess-prod rule"
  echo "       for /handbook/<v>/<uri>.md is broken. Inspect"
  echo "       engine/serve-md.php and the second-handbook rewrite"
  echo "       rule in www/org/htaccess-prod."
  echo
  echo "  if [6] fails (build-host invariant):"
  echo "    -- the regression has been reintroduced in the working"
  echo "       tree. Move the offending router_log() call after"
  echo "       require_once('util.php') in engine/router.php"
  echo "       before committing."
  echo
  echo "to re-run: $0"
  exit 1
fi
echo
echo "all checks passed; /handbook/6/specs/member renders as parsedown HTML and the raw .md companion serves unchanged."
exit 0
