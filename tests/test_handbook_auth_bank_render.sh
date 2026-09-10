#!/usr/bin/env bash
# test_handbook_auth_bank_render.sh
# Verifies that
#   https://www.bbsengine.org/handbook/6/specs/auth-bank
# returns HTTP 200 and that the response body is a rendered
# HTML representation of the local source file
#   bbsengine6/handbook/specs/auth-bank.md
# (rendered through engine/router.php -> router_handleMarkdown
# -> bbsengine6\markdown\parseDocument -> page-markdown.tmpl).
#
# This is the HTML-render sibling of
# test_handbook_auth_bank_content.sh, which covers the
# .md raw-byte path (/handbook/6/specs/auth-bank.md served
# by engine/serve-md.php as text/plain). Both URLs resolve
# the same source spec, but the render path goes through
# the markdown parser and the page template, so the
# assertions are different.
#
# @since 2026-09-09
#
# Why strict HTML assertions (not just a substring grep):
#
#   The render path can 200 with HTML that is not the
#   auth-bank spec: a router fallback, a Smarty error
#   page, an empty template, a markdown parser
#   misconfiguration that strips headings or escapes
#   tables, etc. A bare 200 + 'auth-bank' substring
#   does not distinguish these from a correct render.
#   The structural checks (h1/h2/h3, table, code block,
#   td cells with the verb names) anchor the response
#   to the spec's actual content.
#
# What the test does NOT do (and why):
#
#   - It does not ssh to merlin. The build host is a
#     separate machine; merlin's prod tree is not
#     bind-mounted here. The HTTP probe is the only
#     ground-truth signal of merlin's state.
#
#   - It does not byte-compare the rendered HTML.
#     Rendered HTML can differ across runs in
#     whitespace, attribute order, and template
#     revision; byte-equality is fragile. Instead
#     the test asserts structural and content
#     invariants that are stable under those
#     perturbations.
#
#   - It does not check the build host's
#     /srv/www/vhosts/www.bbsengine.org/html/handbook/
#     tree. That path is the local stage, not the
#     prod tree.
#
# What the test DOES check:
#
#   [0]  preconditions: curl, python3 + bs4 + lxml,
#        local source file present and non-empty
#   [1]  HTTP probe of
#        https://www.bbsengine.org/handbook/6/specs/auth-bank
#        returns 200 with a non-empty body
#   [2]  Content-Type is text/html (rules out the
#        .md raw handler sneaking in, and rules out
#        a text/plain 200 from a non-render fallback)
#   [3]  strict HTML structural parse via python3+bs4:
#        well-formed <html>/<head>/<body>, non-empty
#        <title>, exactly one <h1> matching the spec
#        title, multiple <h2>/<h3>, at least one
#        <table>, at least one <pre> or <code> block
#   [4]  markdown-source content sentinels: key
#        substrings from the local .md appear in the
#        rendered body as text (not raw markdown),
#        and the verb names from the auth-op table
#        appear inside <td> cells
#   [5]  anti-error sentinels: body does NOT contain
#        the router's 404 fallback string, 'router
#        error', 'Unable to load template', or
#        'Failed opening required'
#   [6]  build-host plumbing invariant: local
#        www/org/htaccess-prod has a RewriteRule for
#        ^handbook/(\d+)/(.*) targeting /router.php
#        (the no-.md route); without this rule, the
#        test's URL would not reach router_handleMarkdown
#
# Each check's "bad" message points at the specific
# failure mode and the operator action that resolves it.

set -u

URL="https://www.bbsengine.org/handbook/6/specs/auth-bank"
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

TMPDIR_TEST=$(mktemp -d /tmp/handbook-auth-bank-render.XXXXXX)
trap 'rm -rf "$TMPDIR_TEST"' EXIT
BODY="$TMPDIR_TEST/body.html"
HEADERS="$TMPDIR_TEST/headers.txt"
PARSE_JSON="$TMPDIR_TEST/parse.json"

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
if [ ! -f "$LOCAL_SRC" ]; then
  bad "local source $LOCAL_SRC does not exist -- the test has nothing to anchor against"
  echo "    cannot continue"
  exit 1
fi
if [ ! -s "$LOCAL_SRC" ]; then
  bad "local source $LOCAL_SRC is empty"
  echo "    cannot continue"
  exit 1
fi
src_bytes=$(wc -c < "$LOCAL_SRC" | tr -d ' ')
ok "local source $LOCAL_SRC exists and is non-empty ($src_bytes bytes)"
echo

# --- 1. HTTP probe -------------------------------------------------------
# The no-.md URL routes through
#   www/org/htaccess-prod: RewriteRule ^handbook/(\d+)/(.*)$ /router.php?uri=$2
# which lands in router_handleMarkdown(), which renders the
# .md source through bbsengine6\markdown\parseDocument and
# emits it via page-markdown.tmpl. A 200 + non-empty body is
# the floor; the structural / sentinel checks below verify
# the body is *the spec* and not some other rendered page.
http_code=$(probe "$URL" "$BODY")
body_bytes=$(wc -c < "$BODY" 2>/dev/null | tr -d ' ' || echo 0)
echo "[1] HTTP probe of $URL"
echo "    status: $http_code"
echo "    body:   $body_bytes bytes"
if [ "$http_code" = "200" ] && [ "$body_bytes" -gt 0 ]; then
  ok "HTTP 200 with non-empty body"
else
  bad "expected HTTP 200 with non-empty body, got $http_code ($body_bytes bytes) -- first line of body: $(head -1 "$BODY" 2>/dev/null | head -c 200)"
fi
echo

# --- 2. Content-Type is text/html ---------------------------------------
# router_handleMarkdown wraps the parsed doc in page-markdown.tmpl
# and emits it as text/html. If Content-Type is text/plain the
# response is serve-md.php's raw .md output (the wrong handler
# ran) and the structural / sentinel checks below would be
# meaningless. Fail this check first so the diagnosis points
# at the routing layer.
echo "[2] Content-Type check"
probe_headers "$URL" "$HEADERS"
ct=$(grep -i -E '^content-type:' "$HEADERS" 2>/dev/null | head -1 | tr -d '\r' || true)
echo "    $ct"
if [ -z "$ct" ]; then
  bad "no Content-Type header in response -- router_handleMarkdown did not run (or the no-.md route fell through to a different handler)"
elif echo "$ct" | grep -qi '^content-type: *text/html'; then
  ok "Content-Type is text/html (page-markdown.tmpl rendered the spec)"
else
  bad "Content-Type is not text/html: '$ct' -- the no-.md route did not reach router_handleMarkdown; likely htaccess-prod is missing the /router.php chapter rule, or a symlink is dangling"
fi
echo
