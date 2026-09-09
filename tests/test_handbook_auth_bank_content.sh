#!/usr/bin/env bash
# test_handbook_auth_bank_content.sh
# Verifies that
#   https://www.bbsengine.org/handbook/6/specs/auth-bank.md
# serves the *exact* bytes of the local source file
#   bbsengine6/handbook/specs/auth-bank.md
#
# @since 2026-09-09
#
# Why byte-level equality is the right assertion:
#
#   The /handbook/<v>/<uri>.md route is handled by
#   engine/serve-md.php, whose terminal action is
#       readfile($filepath);
#   (see engine/serve-md.php:43). The handler sets
#   Content-Type: text/plain; charset=utf-8 and emits
#   the raw file bytes with no transformation. So a
#   200 response from this URL is, by construction,
#   the .md source. Any byte drift between the live
#   response and the local working tree is a real
#   "prod is out of sync" condition, and any
#   non-text/plain response means serve-md.php did
#   not run (likely a router/htaccess regression or
#   a 500/404 fallback). The test asserts both.
#
# What the test does NOT do (and why):
#
#   - It does not ssh to merlin. The build host is a
#     separate machine; merlin's prod tree is not
#     bind-mounted here. The HTTP probe is the only
#     ground-truth signal of merlin's state, and the
#     test leans on it.
#
#   - It does not check the build host's
#     /srv/www/vhosts/www.bbsengine.org/html/handbook/
#     tree for the spec. That path is the local
#     stage, not the prod tree the engine/Makefile
#     ssh-pushes to. Its presence here does not
#     imply presence on merlin, and its absence
#     here does not imply absence on merlin.
#
# What the test DOES check:
#
#   [1]  HTTP probe of
#        https://www.bbsengine.org/handbook/6/specs/auth-bank.md
#        returns 200 with a non-empty body.
#   [2]  Response Content-Type is text/plain
#        (rules out an HTML-wrapped 200 from a
#        router error fallback).
#   [3]  Local source file
#        bbsengine6/handbook/specs/auth-bank.md
#        exists and is non-empty.
#   [4]  Live body byte-equals local source
#        (`diff -u`); on mismatch, print the diff
#        and a diagnosis pointing at the prod tree
#        on merlin being out of sync.
#   [5]  Live body contains sentinel substrings
#        from the local source (defense in depth:
#        catches a `text/plain` 200 with an
#        unrelated body, e.g. an error page that
#        happens to be plain text).
#   [6]  Build-host plumbing invariant: the
#        htaccess-prod rewrite rule that routes
#        /handbook/<v>/<uri>.md to /serve-md.php
#        is present and uses the flattened
#        docroot-root target (no /engine/ prefix).
#        Without this rule, the test's URL would
#        not reach serve-md.php at all.
#
# Each check's "bad" message points at the specific
# failure mode and the operator action that resolves
# it.

set -u

URL="https://www.bbsengine.org/handbook/6/specs/auth-bank.md"
LOCAL_BBSENGINE6="/home/opencode/data/work/bbsengine6"
LOCAL_SRC="$LOCAL_BBSENGINE6/handbook/specs/auth-bank.md"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

probe() {
  # $1 = URL, $2 = output file
  curl -sS -o "$2" -w '%{http_code}' "$1" 2>/dev/null || echo "000"
}

probe_headers() {
  # $1 = URL, $2 = output file for headers
  curl -sS -D "$2" -o /dev/null "$1" 2>/dev/null || true
}

# --- 1. HTTP probe -------------------------------------------------------
http_code=$(probe "$URL" /tmp/auth-bank.body)
body_bytes=$(wc -c < /tmp/auth-bank.body 2>/dev/null | tr -d ' ' || echo 0)
echo "[1] HTTP probe of $URL"
echo "    status: $http_code"
echo "    body:   $body_bytes bytes"
if [ "$http_code" = "200" ] && [ "$body_bytes" -gt 0 ]; then
  ok "HTTP 200 with non-empty body"
else
  bad "expected HTTP 200 with non-empty body, got $http_code ($body_bytes bytes) -- first line of body: $(head -1 /tmp/auth-bank.body 2>/dev/null | head -c 200)"
fi
echo

# --- 2. Content-Type is text/plain --------------------------------------
# serve-md.php emits text/plain; charset=utf-8. If the
# response is text/html, the router served an HTML page
# (a 200 masquerading as content) and the byte-match
# check below would be meaningless. Fail this check first
# so the diagnosis is actionable.
echo "[2] Content-Type check"
probe_headers "$URL" /tmp/auth-bank.headers
ct=$(grep -i -E '^content-type:' /tmp/auth-bank.headers 2>/dev/null | head -1 | tr -d '\r' || true)
echo "    $ct"
if [ -z "$ct" ]; then
  bad "no Content-Type header in response -- serve-md.php did not run (or the .md route fell through to a different handler)"
elif echo "$ct" | grep -qi '^content-type: *text/plain'; then
  ok "Content-Type is text/plain (serve-md.php ran and readfile()'d the source)"
else
  bad "Content-Type is not text/plain: '$ct' -- serve-md.php did not run; the router served an HTML error page or a different handler. Likely htaccess-prod is missing the /serve-md.php .md rewrite, or the symlink at html/serve-md.php is dangling"
fi
echo

# --- 3. Local source present --------------------------------------------
echo "[3] local source check"
if [ ! -f "$LOCAL_SRC" ]; then
  bad "local source $LOCAL_SRC does not exist -- the test has nothing to compare against"
elif [ ! -s "$LOCAL_SRC" ]; then
  bad "local source $LOCAL_SRC is empty"
else
  src_bytes=$(wc -c < "$LOCAL_SRC" | tr -d ' ')
  echo "    local: $LOCAL_SRC ($src_bytes bytes)"
  ok "local source $LOCAL_SRC exists and is non-empty ($src_bytes bytes)"
fi
echo

# --- 4. byte-level equality (diff -u) -----------------------------------
echo "[4] byte-level equality: live body vs local source"
if [ -f "$LOCAL_SRC" ] && [ "$body_bytes" -gt 0 ]; then
  if diff -u /tmp/auth-bank.body "$LOCAL_SRC" > /tmp/auth-bank.diff 2>&1; then
    ok "live body byte-equals local source (diff -u clean)"
  else
    diff_lines=$(wc -l < /tmp/auth-bank.diff | tr -d ' ')
    diff_first=$(head -40 /tmp/auth-bank.diff 2>/dev/null)
    bad "live body differs from local source ($diff_lines diff lines). First 40 lines of diff: $(printf '\n      %s' "$diff_first" | tr '\n' ' ' | head -c 600). Most likely: merlin's prod tree at /srv/www/vhosts/www.bbsengine.org/html/handbook/specs/auth-bank.md is out of sync with this build host's working tree. Operator action: run 'make wwworg' to push the canonical handbook to the .org docroot"
  fi
else
  bad "skipped -- check [1] or [3] failed"
fi
echo

# --- 5. sentinel substring check ----------------------------------------
# Defense in depth on top of [4]. If [4] is somehow
# bypassed (e.g. a text/plain 200 with a totally
# different body that happens to byte-match some
# other local file -- vanishingly unlikely but not
# impossible), these sentinels anchor the test to
# the actual auth-bank spec content.
echo "[5] sentinel substring check"
sentinels=(
  "bbsengine6.auth to bbsengine6.bank authorization flow"
  "SessionManager"
  "bank_transfer_approve"
  "register_session"
)
sent_ok=true
for s in "${sentinels[@]}"; do
  if grep -qF "$s" /tmp/auth-bank.body 2>/dev/null; then
    echo "    ok: '$s' present"
  else
    bad "sentinel '$s' not present in live body -- the response is not the auth-bank spec"
    sent_ok=false
  fi
done
if $sent_ok; then
  ok "all ${#sentinels[@]} sentinel substrings present in live body"
fi
echo

# --- 6. build-host plumbing invariant -----------------------------------
# The /handbook/<v>/<uri>.md rewrite in
# www/org/htaccess-prod must target /serve-md.php
# (not /engine/serve-md.php) and must be present.
# If this rule is missing, the test's URL would
# not reach serve-md.php at all and [1] would
# fail with a 404/500. We check it explicitly
# so a missing rule is diagnosed as "plumbing",
# not as a content-sync issue.
echo "[6] build-host plumbing invariant (htaccess-prod /serve-md.php .md rule)"
if [ ! -f "$LOCAL_BBSENGINE6/www/org/htaccess-prod" ]; then
  bad "local www/org/htaccess-prod missing"
else
  md_rule_ok=false
  if grep -E '^[[:space:]]*RewriteRule[[:space:]]+\^handbook/' "$LOCAL_BBSENGINE6/www/org/htaccess-prod" 2>/dev/null | grep -qF '/serve-md.php'; then
    md_rule_ok=true
  fi
  if $md_rule_ok; then
    ok "local www/org/htaccess-prod routes /handbook/<v>/<uri>.md to /serve-md.php"
  else
    bad "local www/org/htaccess-prod does NOT route /handbook/<v>/<uri>.md to /serve-md.php -- fix(www/htaccess-prod) routing rule missing or uses /engine/ prefix"
  fi
  # @since 2026-09-09 — single-install refactor. The
  # rewrite target should be /serve-md.php at the
  # docroot root (a symlink), not /engine/serve-md.php.
  # An active rewrite line that still uses /engine/
  # would mean the rule was missed in the refactor and
  # would 404 on merlin (no /engine/ subdir at the
  # docroot).
  active_engine_md_refs=$(grep -E '^[[:space:]]*Rewrite(Rule|Cond)' "$LOCAL_BBSENGINE6/www/org/htaccess-prod" 2>/dev/null | grep -c '/engine/serve-md\.php' || true)
  if [ "$active_engine_md_refs" -eq 0 ]; then
    ok "local www/org/htaccess-prod has no /engine/serve-md.php references in active rewrite lines (single-install refactor applied)"
  else
    bad "local www/org/htaccess-prod has $active_engine_md_refs active rewrite line(s) referencing /engine/serve-md.php -- single-install refactor not fully applied to the .md route"
  fi
fi
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
  echo "  if [1] returns 404:"
  echo "    -- the /handbook/<v>/<uri>.md route is not reaching"
  echo "       /serve-md.php. Check htaccess-prod has the active"
  echo "       RewriteRule for ^handbook/ ... /serve-md.php,"
  echo "       and that the symlink at html/serve-md.php on"
  echo "       merlin points at /srv/www/bbsengine6/serve-md.php"
  echo "       (created by 'make -C www org' via prod-symlinks)."
  echo
  echo "  if [1] returns 200 but [2] is not text/plain:"
  echo "    -- serve-md.php did not run. The router served an"
  echo "       HTML error page (or a different handler) with a"
  echo "       200 status. Same plumbing check as the 404 case."
  echo
  echo "  if [1] returns 200, [2] is text/plain, but [4] fails:"
  echo "    -- merlin's prod tree at /srv/www/vhosts/"
  echo "       www.bbsengine.org/html/handbook/specs/"
  echo "       auth-bank.md is out of sync with the local"
  echo "       working tree. Run 'make wwworg' to push the"
  echo "       canonical handbook to the .org docroot."
  echo
  echo "  if [6] fails:"
  echo "    -- the local www/org/htaccess-prod is missing the"
  echo "       /serve-md.php rewrite (or still uses the old"
  echo "       /engine/serve-md.php target). Restore the rule"
  echo "       before running this test -- without it, the test"
  echo "       is meaningless."
  echo
  echo "to re-run: $0"
  exit 1
fi
echo
echo "all checks passed; $URL serves the exact bytes of $LOCAL_SRC."
exit 0
