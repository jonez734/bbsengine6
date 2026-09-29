#!/bin/bash
# test_teos_md_url_text_plain.sh
#
# Live HTTP integration test for the teos vhost's .md dispatch path.
# Asserts that https://zoidtechnologies.com/teos/ec/<slug>.md
# returns Content-Type: text/plain with body byte-equal to the
# on-disk TEOSDIR source.
#
# Parallel to test_serve_md_entry_point.sh, which covers the
# handbook vhost's engine/serve-md.php path. The teos vhost
# uses the universal engine/router.php path through
# router_handleRawMarkdown instead.
#
# Regression guard for the 2026-09-29 incident on
# https://zoidtechnologies.com/teos/ec/investigated-psychics-
# fraud-pigasus.md returning text/html chrome instead of
# text/plain raw. Complements php/test_router.php Test 6i
# (in-process dispatch on a fixture) by exercising the full
# production stack: Apache -> htaccess rewrite ->
# engine/router.php -> \bbsengine6\serveRawMarkdown() ->
# Content-Type header + body.

set -u

URL="https://zoidtechnologies.com/teos/ec/investigated-psychics-fraud-pigasus.md"
TEOSDIR="/srv/www/vhosts/zoidtechnologies.com/html/teos/"
SOURCE="$TEOSDIR/ec/investigated-psychics-fraud-pigasus.md"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

# --- 0. preconditions ---------------------------------------------------
echo "[0] preconditions"
if ! command -v curl >/dev/null 2>&1; then
    bad "curl not available on PATH"
    echo "    cannot continue"
    exit 1
fi
ok "curl available"

if [ ! -f "$SOURCE" ]; then
    echo "SKIP: source file not found at $SOURCE"
    echo "    (test only meaningful when TEOSDIR is deployed to that path)"
    exit 0
fi
ok "source file present at $SOURCE"
echo

# --- 1. Content-Type ----------------------------------------------------
echo "[1] Content-Type assertion"
ctype=$(curl -sI "$URL" 2>/dev/null | tr -d '\r' \
        | awk -F': ' 'tolower($1)=="content-type"{print $2; exit}')
if [[ "$ctype" != text/plain* ]]; then
    bad "Content-Type expected text/plain*, got '$ctype'"
else
    ok "Content-Type is '$ctype'"
fi
echo

# --- 2. Body byte-equality ----------------------------------------------
echo "[2] Body byte-equality with on-disk source"
tmp=$(mktemp)
trap "rm -f $tmp" EXIT
if ! curl -sf "$URL" -o "$tmp" 2>/dev/null; then
    bad "curl failed fetching $URL"
else
    if ! diff -q "$SOURCE" "$tmp" >/dev/null 2>&1; then
        bad "body does not byte-equal source"
        diff "$SOURCE" "$tmp" | head -20 | sed 's/^/    /'
    else
        ok "body byte-equals source ($(wc -c < "$SOURCE") bytes)"
    fi
fi
echo

# --- 3. Status code -----------------------------------------------------
echo "[3] Status code assertion"
status=$(curl -sI "$URL" 2>/dev/null | head -1 | awk '{print $2}')
if [ "$status" != "200" ]; then
    bad "expected status 200, got '$status'"
else
    ok "status is 200"
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
    echo "to re-run: $0"
    exit 1
fi
echo
echo "all checks passed; teos /<uri>.md returns raw text/plain markdown."
exit 0
