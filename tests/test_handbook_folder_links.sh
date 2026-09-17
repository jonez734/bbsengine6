#!/usr/bin/env bash
# test_handbook_folder_links.sh
# Regression test for the /handbook/6/specs/ -> /teos/specs/...
# href drift. After the 2026-09-17 fix (zoid6/php/zoid6config.php
# honors TEOSURL env var; bbsengine6/www/org/htaccess-prod
# SetEnv TEOSURL /handbook/6/; bbsengine6/php/folder.php:231
# switched from bare \TEOSURL to \bbsengine6\util\teos_url()),
# every internal link in the rendered /handbook/6/<dir>/ body
# must start with /handbook/6/, never /teos/.
#
# What this test does:
#   [0]  preconditions: curl, python3+bs4+lxml
#   [1]  HTTP probe https://www.bbsengine.org/handbook/6/specs/
#        returns 200 with a non-empty body
#   [2]  body parses as well-formed HTML (catches the
#        pre-fix inline-list-fallback signature: a half-rendered
#        body that starts with "Error: folder visibility check
#        failed" then a bare <html><head><title>specs</title>...
#        <ul><li><a href="...md">...</a></li></ul></body></html>)
#   [3]  breadcrumb top-crumb href is /handbook/6/ (the
#        TEOS_LABEL "bbsengine6 handbook" crumb that
#        engine/router.php putenv()'s for /handbook/<v>/...)
#   [4]  breadcrumb spec-crumb href is /handbook/6/specs/
#        (NOT /teos/specs/)
#   [5]  every per-item <a href> in the directory listing
#        points at /handbook/6/specs/<chapter>, never
#        /teos/specs/<chapter>
#   [6]  every per-item href resolves to a 200 on this vhost
#        (catches future deploy drift where the link target
#        moves but the route doesn't catch up)
#   [7]  build-host plumbing invariant: local
#        www/org/htaccess-prod has a `SetEnv TEOSURL /handbook/6/`
#        line. Without it the env-var seed is gone and the
#        live fix regresses silently.
#   [8]  build-host plumbing invariant: local
#        zoid6/php/zoid6config.php defines TEOSURL
#        env-aware (the env override must precede the
#        `/teos/` literal). Without this guard, the
#        zoid6config default silently re-wins on every
#        request.
#   [9]  build-host plumbing invariant: local
#        bbsengine6/php/folder.php uses
#        \bbsengine6\util\teos_url() (not bare \TEOSURL)
#        for item URI assembly. A future refactor that
#        reverts this line silently re-introduces the bug.
#
# Why per-link resolution (vs substring grep alone):
#   A naive grep for `href="/handbook/6/specs/` is necessary
#   but not sufficient -- a future regression could land a
#   body that emits a single correct-looking href among many
#   broken ones (partial deploy, template error in a single
#   branch). Per-link 200 resolution surfaces that.

set -u

URL_BASE="https://www.bbsengine.org/handbook/6"
SPECS_URL="$URL_BASE/specs/"
LOCAL_BBSENGINE6="/home/opencode/data/work/bbsengine6"
LOCAL_SPECS_DIR="$LOCAL_BBSENGINE6/handbook/specs"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

probe() {
  # $1 = URL, $2 = output file
  curl -sS -o "$2" -w '%{http_code}' "$1" 2>/dev/null || echo "000"
}

TMPDIR_TEST=$(mktemp -d /tmp/handbook-folder-links.XXXXXX)
trap 'rm -rf "$TMPDIR_TEST"' EXIT
BODY="$TMPDIR_TEST/specs.html"

# --- 0. preconditions ---------------------------------------------------
echo "[0] preconditions"
if ! command -v curl >/dev/null 2>&1; then
  bad "curl not available on PATH"
  echo "    cannot continue"
  exit 1
fi
ok "curl available"
if ! command -v python3 >/dev/null 2>&1; then
  bad "python3 not available on PATH"
  echo "    cannot continue"
  exit 1
fi
ok "python3 available"
if ! python3 -c "import bs4, lxml" >/dev/null 2>&1; then
  bad "python3 bs4+lxml not available (need 'pip install beautifulsoup4 lxml' or distro equivalent)"
  echo "    cannot continue"
  exit 1
fi
ok "python3 bs4+lxml available"
if [ ! -d "$LOCAL_SPECS_DIR" ]; then
  bad "local source $LOCAL_SPECS_DIR does not exist -- the test has nothing to anchor against"
  echo "    cannot continue"
  exit 1
fi
spec_count=$(find "$LOCAL_SPECS_DIR" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
if [ "$spec_count" -lt 1 ]; then
  bad "local $LOCAL_SPECS_DIR has no .md files; the live listing should have at least one"
  echo "    cannot continue"
  exit 1
fi
ok "local $LOCAL_SPECS_DIR has $spec_count .md files"
echo

# --- 1. HTTP probe ------------------------------------------------------
echo "[1] HTTP probe of $SPECS_URL"
code=$(probe "$SPECS_URL" "$BODY")
bytes=$(wc -c < "$BODY" 2>/dev/null | tr -d ' ' || echo 0)
echo "    status: $code"
echo "    body:   $bytes bytes"
if [ "$code" = "200" ] && [ "$bytes" -gt 0 ]; then
  ok "specs/ returned 200 with non-empty body"
else
  bad "specs/ expected 200 with body, got $code ($bytes bytes)"
  echo
  echo "=== summary ==="
  echo "passed: $pass"
  echo "failed: $fail"
  [ "$fail" -gt 0 ] && { echo; echo "diagnosis:"; printf "%b\n" "$diagnosis"; }
  exit 1
fi
echo

# --- 2. HTML well-formedness --------------------------------------------
echo "[2] HTML well-formedness"
if ! python3 -c "
from bs4 import BeautifulSoup
import sys
try:
    soup = BeautifulSoup(open('$BODY').read(), 'lxml')
    if soup.find('html') is None:
        sys.exit(2)
    if soup.find('body') is None:
        sys.exit(3)
    if soup.find('a') is None:
        sys.exit(4)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
  bad "specs/ body is not well-formed HTML or has no <html>/<body>/<a> -- inspect manually (body excerpt: $(head -c 200 "$BODY"))"
else
  ok "specs/ body parses as well-formed HTML with at least one <a>"
fi
echo

# --- 3-4. breadcrumb hrefs ----------------------------------------------
echo "[3] breadcrumb top crumb"
if grep -qE 'href="/handbook/6/"' "$BODY" 2>/dev/null; then
  ok "body contains href=\"/handbook/6/\" (handbook top crumb)"
else
  bad "body does NOT contain href=\"/handbook/6/\" -- TEOS_BASEURI /handbook/6/ top crumb missing or routed to /teos/"
fi
echo

echo "[4] breadcrumb specs crumb"
if grep -qE 'href="/handbook/6/specs/"' "$BODY" 2>/dev/null; then
  ok "body contains href=\"/handbook/6/specs/\" (handbook specs crumb)"
else
  bad "body does NOT contain href=\"/handbook/6/specs/\" -- breadcrumb href drift, likely TEOSURL=/teos/ leak"
fi
if grep -qE 'href="/teos/specs/"' "$BODY" 2>/dev/null; then
  bad "body contains href=\"/teos/specs/\" -- breadcrumb href drift; check www/org/htaccess-prod SetEnv TEOSURL, zoid6/php/zoid6config.php env-aware define, and skin/tmpl/function.teos.tmpl smarty.const.TEOSURL usage"
else
  ok "body has no href=\"/teos/specs/\""
fi
echo

# --- 5. per-item href prefix --------------------------------------------
echo "[5] every per-item href points at /handbook/6/specs/"
# Extract all <a href> values from the body that look like a
# spec-chapter link (no leading "..", no scheme, no javascript:,
# no #anchor). python3+bs4 is the cleanest way to handle the
# edge cases (entities, attribute order, self-closing tags).
href_data=$(python3 <<PYEOF
from bs4 import BeautifulSoup
import json
soup = BeautifulSoup(open("$BODY").read(), "lxml")
hrefs = []
for a in soup.find_all("a"):
    href = a.get("href")
    if href is None:
        continue
    if href.startswith("/handbook/6/specs/"):
        hrefs.append(("ok", href))
    elif href.startswith("/teos/specs/"):
        hrefs.append(("bad", href))
    else:
        # ignore breadcrumb top, login, login/out, etc.
        pass
print(json.dumps(hrefs))
PYEOF
)
ok_hrefs=$(printf '%s' "$href_data" | python3 -c "import sys, json; d=json.load(sys.stdin); print(sum(1 for k,_ in d if k=='ok'))")
bad_hrefs=$(printf '%s' "$href_data" | python3 -c "import sys, json; d=json.load(sys.stdin); print(sum(1 for k,_ in d if k=='bad'))")
total_hrefs=$((ok_hrefs + bad_hrefs))
echo "    /handbook/6/specs/* hrefs: $ok_hrefs"
echo "    /teos/specs/*     hrefs: $bad_hrefs"
if [ "$bad_hrefs" -gt 0 ]; then
  bad "found $bad_hrefs /teos/specs/* href(s) -- folder.php:231 / function.teos.tmpl leaking TEOSURL=/teos/ default"
elif [ "$ok_hrefs" -lt 1 ]; then
  bad "no /handbook/6/specs/<chapter> hrefs in body -- directory listing rendered no per-item links (or all are filtered by the strict /handbook/6/specs/ prefix match)"
else
  ok "all $ok_hrefs per-item href(s) start with /handbook/6/specs/"
fi
echo

# --- 6. every per-item href resolves to 200 -----------------------------
echo "[6] per-item href resolution (sampled)"
# Pick up to 5 hrefs and confirm each is a 200 on this vhost.
# Avoid spending too long on a 22-item listing; sampling
# catches the common regression where the URL prefix flips
# back to /teos/.
sample=$(printf '%s' "$href_data" | python3 -c "
import sys, json
d = json.load(sys.stdin)
oks = [h for k,h in d if k == 'ok']
for h in oks[:5]:
    print(h)
")
sampled=0
sampled_pass=0
for href in $sample; do
  sampled=$((sampled+1))
  full="https://www.bbsengine.org${href}"
  code=$(curl -sS -o /dev/null -w '%{http_code}' "$full" 2>/dev/null || echo "000")
  echo "    $full -> $code"
  if [ "$code" = "200" ]; then
    sampled_pass=$((sampled_pass+1))
  else
    bad "sample href $full returned $code (expected 200)"
  fi
done
if [ "$sampled" -gt 0 ] && [ "$sampled_pass" -eq "$sampled" ]; then
  ok "all $sampled sampled href(s) returned 200"
fi
echo

# --- 7. local htaccess-prod has SetEnv TEOSURL --------------------------
echo "[7] local www/org/htaccess-prod publishes SetEnv TEOSURL /handbook/6/"
HTACCESS="$LOCAL_BBSENGINE6/www/org/htaccess-prod"
if [ ! -f "$HTACCESS" ]; then
  bad "local $HTACCESS missing"
else
  if grep -qE '^[[:space:]]*SetEnv[[:space:]]+TEOSURL[[:space:]]+/handbook/6/' "$HTACCESS" 2>/dev/null; then
    ok "local htaccess-prod publishes SetEnv TEOSURL /handbook/6/"
  else
    bad "local htaccess-prod is MISSING 'SetEnv TEOSURL /handbook/6/' -- the env-var seed is gone; on next deploy the /handbook/6/specs/ link drift will return"
  fi
fi
echo

# --- 8. zoid6config.php defines TEOSURL env-aware ----------------------
echo "[8] local zoid6/php/zoid6config.php defines TEOSURL env-aware"
Z6CONFIG="$LOCAL_BBSENGINE6/../zoid6/php/zoid6config.php"
# Resolve relative to LOCAL_BBSENGINE6 in case the test is run
# from somewhere other than the meta-repo root.
Z6CONFIG_ABS=$(realpath "$Z6CONFIG" 2>/dev/null || echo "$Z6CONFIG")
if [ ! -f "$Z6CONFIG_ABS" ]; then
  bad "local $Z6CONFIG_ABS missing (zoid6 submodule not checked out?)"
else
  if grep -qE "getenv\\(.TEOSURL.\\)" "$Z6CONFIG_ABS" 2>/dev/null; then
    ok "local zoid6config.php reads TEOSURL from getenv() before defining the constant"
  else
    bad "local zoid6config.php does NOT read TEOSURL from getenv() -- the env override will not flow through and TEOSURL will silently default to /teos/"
  fi
fi
echo

# --- 9. folder.php uses teos_url() helper -------------------------------
echo "[9] local bbsengine6/php/folder.php uses \\bbsengine6\\util\\teos_url() for item URI assembly"
FOLDER_PHP="$LOCAL_BBSENGINE6/php/folder.php"
if [ ! -f "$FOLDER_PHP" ]; then
  bad "local $FOLDER_PHP missing"
else
  # Bare \TEOSURL in the item URI line is the regression shape.
  # The teos_url() helper is what we want.
  if grep -E "'uri'[[:space:]]*=>" "$FOLDER_PHP" 2>/dev/null | grep -qE "\\\\bbsengine6\\\\util\\\\teos_url\\(\\)"; then
    ok "local folder.php assembles item URIs via \\bbsengine6\\util\\teos_url() (env-first)"
  else
    bad "local folder.php item URI assembly does NOT use \\bbsengine6\\util\\teos_url() -- folder.php:231 has been reverted to bare \\TEOSURL"
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
  exit 1
fi
echo
echo "all checks passed; /handbook/6/specs/ renders links under /handbook/6/specs/ and the local plumbing (htaccess SetEnv + zoid6config env-aware define + folder.php teos_url()) is in place."
exit 0
