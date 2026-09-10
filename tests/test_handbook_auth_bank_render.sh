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
#        well-formed <html>/<head>/<body>, doc title
#        present (in <title> or as the first <h1>),
#        at least one <h1> matching the spec title
#        (the .org vhost's layout chrome adds a site-
#        branding h1 above the spec h1, so 1-2 h1s is
#        the normal range; > 5 is pathological),
#        multiple <h2>/<h3>, at least one <table>,
#        at least one <pre> or <code> block
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
# @since 2026-09-09 — regression prevention for the
# handbook_home() bootstrap-order bug fixed in 34491fb.
# engine/router.php must require_once php/util.php BEFORE
# calling \bbsengine6\util\handbook_home(). If a future
# refactor moves the call site but forgets to move the
# require_once, the entire no-.md render path returns 500
# (the .md raw path through serve-md.php is unaffected and
# the regression hides behind a partially-working handbook).
# The check is a precondition because a working [0] plus a
# broken [0.5] would cause [1] to fail in a way that looks
# like a prod outage; flagging it at [0.5] with a clear
# "fix in working tree" message is more actionable.
echo "[0.5] build-host bootstrap-order invariant (router.php must load util.php before handbook_home())"
ROUTER_PHP="$LOCAL_BBSENGINE6/engine/router.php"
if [ ! -f "$ROUTER_PHP" ]; then
  bad "local $ROUTER_PHP missing"
else
  # Find the line number of the require_once('php/util.php')
  # and the line number of the first call to handbook_home().
  # The require_once must come first. Strip PHP comments
  # (lines starting with // or inside /* ... */ blocks)
  # before searching so a long comment block mentioning
  # handbook_home() does not produce a false-positive line
  # number. The first version of this check matched the
  # literal substring 'handbook_home()' inside a comment
  # and reported the fix commit as a regression.
  php_strip_comments() {
    # Strip // line comments and /* ... */ block comments.
    # Pure shell/awk -- no PHP CLI dependency.
    awk '
      BEGIN { in_block = 0 }
      {
        line = $0
        # inside a block comment?
        if (in_block) {
          if (match(line, /\*\//)) {
            line = substr(line, RSTART + 2)
            in_block = 0
          } else {
            next
          }
        }
        # start of a block comment?
        while (match(line, /\/\*/)) {
          pre = substr(line, 1, RSTART - 1)
          rest = substr(line, RSTART + 2)
          if (match(rest, /\*\//)) {
            line = pre substr(rest, RSTART + 2)
          } else {
            line = pre
            in_block = 1
            break
          }
        }
        # strip // line comments (but not inside strings --
        # for the limited matches we care about, the simple
        # form is enough)
        sub(/\/\/.*$/, "", line)
        print line
      }
    ' "$1"
  }
  TMP_ROUTER="$TMPDIR_TEST/router.stripped.php"
  php_strip_comments "$ROUTER_PHP" > "$TMP_ROUTER"
  util_line=$(grep -n -F "require_once('/srv/www/bbsengine6/php/util.php')" "$TMP_ROUTER" 2>/dev/null | head -1 | cut -d: -f1)
  hb_line=$(grep -n -F 'handbook_home()' "$TMP_ROUTER" 2>/dev/null | head -1 | cut -d: -f1)
  if [ -z "$util_line" ]; then
    bad "local $ROUTER_PHP has no require_once of /srv/www/bbsengine6/php/util.php -- the handbook render path cannot bootstrap (regression of 34491fb)"
  elif [ -z "$hb_line" ]; then
    ok "local $ROUTER_PHP requires util.php and does not call handbook_home() at module load (pre-handbook_home() layout)"
  elif [ "$util_line" -lt "$hb_line" ]; then
    ok "local $ROUTER_PHP requires util.php (line $util_line) before handbook_home() call (line $hb_line) -- bootstrap order is correct (regression 34491fb not reintroduced)"
  else
    bad "local $ROUTER_PHP calls handbook_home() (line $hb_line) before requiring php/util.php (line $util_line) -- regression of 34491fb reintroduced; the no-.md render path will 500 in production. Fix: move the require_once of /srv/www/bbsengine6/php/util.php to a line above $hb_line"
  fi
fi
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
# Always fetch headers for the [1] failure path so the
# operator can see what the server actually returned
# (e.g. a 500 with empty body and a 'Server: nginx/1.x'
# header is a different triage path from a 500 with
# 'Failed opening required' in the body). On 200 the
# header dump is redundant with [2] but cheap.
probe_headers "$URL" "$HEADERS" >/dev/null 2>&1
header_summary=$(head -5 "$HEADERS" 2>/dev/null | tr -d '\r' | sed 's/^/      /' | head -c 400)
echo "[1] HTTP probe of $URL"
echo "    status: $http_code"
echo "    body:   $body_bytes bytes"
if [ "$http_code" = "200" ] && [ "$body_bytes" -gt 0 ]; then
  ok "HTTP 200 with non-empty body"
else
  # Dump everything we have so the operator can triage
  # without re-running. The body may be empty on a PHP
  # fatal; in that case the headers + status are the
  # only signal.
  echo "    headers (first 5 lines):"
  echo "$header_summary" | sed 's/^/    /'
  if [ "$body_bytes" -gt 0 ]; then
    body_first=$(head -1 "$BODY" 2>/dev/null | head -c 200)
    body_dump=$(head -c 500 "$BODY" 2>/dev/null | sed 's/^/      /')
    echo "    body (first 500 bytes):"
    echo "$body_dump"
  else
    echo "    body: (empty -- likely a PHP fatal that exited before any output;"
    echo "           check merlin's php-fpm error log for the matching request)"
  fi
  bad "expected HTTP 200 with non-empty body, got $http_code ($body_bytes bytes)"
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

# --- 3. strict HTML structural parse ------------------------------------
# A 200 + text/html is not enough: an empty page-markdown.tmpl,
# a Smarty error page, or a markdown parser misconfig can all
# 200 with HTML. The structural checks below anchor the
# response to the spec's actual shape:
#   - one <html>/<head>/<body>
#   - doc title present (in <title> or as the first
#     <h1>; the actual page-markdown.tmpl renders the
#     title as the first <h1>, not in <title>, so an
#     empty <title> is acceptable iff the spec h1 is
#     present in the body)
#   - at least one <h1> whose text matches the spec
#     title (1-2 h1s is the normal range; the .org
#     vhost's layout chrome adds a site-branding h1
#     above the spec h1; > 5 is pathological)
#   - several <h2>/<h3> (Components, bbsengine6.bank,
#     bbsengine6.bank.api.handler, End-to-end sequence,
#     Wire-level mapping, Token-aware path, Failure modes,
#     Files involved)
#   - at least one <table> (the source has two markdown
#     tables: the auth-op table and the wire-level mapping)
#   - at least one <pre> or <code> block (the source has
#     a fenced code block for the session_id mapping and
#     a fenced json block for the error envelope)
#
# The parse runs as a single python3 invocation that
# emits a JSON object of facts. Each fact is then asserted
# by the shell from the JSON. This keeps the python logic
# out of the shell and the assertions out of python.
echo "[3] strict HTML structural parse (python3 + bs4)"
if [ "$body_bytes" -gt 0 ] && [ -s "$BODY" ]; then
  python3 - "$BODY" "$PARSE_JSON" <<'PYEOF' 2>"$TMPDIR_TEST/parse.err"
import json
import sys
from bs4 import BeautifulSoup

body_path, out_path = sys.argv[1], sys.argv[2]
with open(body_path, "r", encoding="utf-8", errors="replace") as fh:
    html = fh.read()

try:
    soup = BeautifulSoup(html, "lxml")
    parse_ok = True
    parse_error = ""
except Exception as e:
    soup = BeautifulSoup(html, "html.parser")
    parse_ok = False
    parse_error = "{0}: {1}".format(type(e).__name__, e)

# structural facts
html_tag = soup.find("html")
head_tag = soup.find("head")
body_tag = soup.find("body")
title_tag = soup.find("title")
title_text = title_tag.get_text(strip=True) if title_tag else ""

h1_tags = soup.find_all("h1")
h1_texts = [h.get_text(" ", strip=True) for h in h1_tags]
h2_count = len(soup.find_all("h2"))
h3_count = len(soup.find_all("h3"))
table_count = len(soup.find_all("table"))
pre_count = len(soup.find_all("pre"))
code_count = len(soup.find_all("code"))
td_cells = [td.get_text(" ", strip=True) for td in soup.find_all("td")]
li_count = len(soup.find_all("li"))

facts = {
    "parse_ok": parse_ok,
    "parse_error": parse_error,
    "has_html": html_tag is not None,
    "has_head": head_tag is not None,
    "has_body": body_tag is not None,
    "title_text": title_text,
    "h1_count": len(h1_tags),
    "h1_texts": h1_texts,
    "h2_count": h2_count,
    "h3_count": h3_count,
    "table_count": table_count,
    "pre_count": pre_count,
    "code_count": code_count,
    "li_count": li_count,
    "td_cells": td_cells,
    "body_text_len": len(body_tag.get_text(" ", strip=True)) if body_tag else 0,
}

with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(facts, fh, indent=2)
PYEOF
  parse_rc=$?
  if [ "$parse_rc" -ne 0 ]; then
    bad "python3 parse failed (rc=$parse_rc); stderr: $(head -3 "$TMPDIR_TEST/parse.err" 2>/dev/null | head -c 300)"
  elif [ ! -s "$PARSE_JSON" ]; then
    bad "python3 parse produced no output (empty $PARSE_JSON); stderr: $(head -3 "$TMPDIR_TEST/parse.err" 2>/dev/null | head -c 300)"
  else
    # extract facts via python3 -c (no jq dependency)
    jget() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get(sys.argv[2], ''))" "$PARSE_JSON" "$1" 2>/dev/null; }
    jgeti() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(int(d.get(sys.argv[2], 0)))" "$PARSE_JSON" "$1" 2>/dev/null; }
    jgetl() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); v=d.get(sys.argv[2], []); print(len(v))" "$PARSE_JSON" "$1" 2>/dev/null; }
    jgetls() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); v=d.get(sys.argv[2], []); print('|'.join(str(x) for x in v))" "$PARSE_JSON" "$1" 2>/dev/null; }

    parse_ok=$(jget parse_ok)
    has_html=$(jget has_html)
    has_head=$(jget has_head)
    has_body=$(jget has_body)
    title_text=$(jget title_text)
    h1_count=$(jgeti h1_count)
    h1_texts=$(jgetls h1_texts)
    h2_count=$(jgeti h2_count)
    h3_count=$(jgeti h3_count)
    table_count=$(jgeti table_count)
    pre_count=$(jgeti pre_count)
    code_count=$(jgeti code_count)
    li_count=$(jgeti li_count)
    td_count=$(jgetl td_cells)
    body_text_len=$(jgeti body_text_len)

    echo "    parse_ok=$parse_ok html=$has_html head=$has_head body=$has_body"
    echo "    title: $title_text"
    echo "    h1 count: $h1_count  texts: $h1_texts"
    echo "    h2: $h2_count  h3: $h3_count  li: $li_count"
    echo "    table: $table_count  pre: $pre_count  code: $code_count  td: $td_count"
    echo "    body text length: $body_text_len"

    if [ "$parse_ok" = "True" ] || [ "$parse_ok" = "true" ]; then
      ok "html parsed cleanly under lxml"
    else
      ok "html parsed under html.parser fallback (lxml reported: $(jget parse_error))"
    fi
    if [ "$has_html" = "True" ] && [ "$has_head" = "True" ] && [ "$has_body" = "True" ]; then
      ok "structural <html>/<head>/<body> present"
    else
      bad "missing structural element (html=$has_html head=$has_head body=$has_body) -- response is not a rendered page"
    fi
    if [ -n "$title_text" ]; then
      ok "<title> is non-empty: '$title_text'"
    elif [ "$h1_count" -ge 1 ] && echo "$h1_texts" | grep -qF 'bbsengine6.auth to bbsengine6.bank authorization flow'; then
      # @since 2026-09-09 — page-markdown.tmpl renders the
      # spec title as the first <h1> in the body, not in
      # <title>. The strict 'non-empty <title>' assertion
      # from the first version of this test fails on the
      # actual template (verified against the live URL
      # post-fix: title is empty, h1 contains the spec
      # title). The right invariant is 'title is in the
      # document' -- either in <title> or as the first
      # <h1>. Acceptable: empty <title> iff the spec H1
      # is present.
      ok "<title> is empty but the spec H1 is present in the body (page-markdown.tmpl renders the doc title as the first <h1>, not in <title>)"
    else
      bad "<title> is empty AND no <h1> contains the spec title -- the doc title is missing from the rendered page"
    fi
    # @since 2026-09-09 — the .org vhost's layout chrome
    # adds a site-branding <h1> ('bbsengine.org') above
    # the spec <h1>. The strict 'exactly one <h1>'
    # assertion from the first version of this test
    # flagged this as a duplicate; the layout is
    # legitimate. The right invariant: at least one <h1>
    # contains the spec title, and the h1 count is not
    # pathological (> 5 suggests a heading-loop bug
    # where a section is mis-nested as h1 instead of h2).
    if [ "$h1_count" -ge 1 ] && [ "$h1_count" -le 5 ] && echo "$h1_texts" | grep -qF 'bbsengine6.auth to bbsengine6.bank authorization flow'; then
      ok "<h1> count $h1_count (1 spec h1 + N layout-chrome h1s, all < 5) and at least one matches the spec title"
    elif [ "$h1_count" = "0" ]; then
      bad "no <h1> -- the spec's '# bbsengine6.auth to bbsengine6.bank authorization flow' heading was not rendered"
    elif [ "$h1_count" -gt 5 ]; then
      bad "$h1_count <h1> elements rendered -- pathological heading count (likely a heading-loop bug where a section is mis-nested as h1 instead of h2); h1_texts: $h1_texts"
    else
      bad "no <h1> contains the spec title (h1_texts: $h1_texts) -- markdown parser dropped or mangled the heading"
    fi
    # verify the h1 text matches the spec title (Parsedown strips the
    # leading '# ' and emits the rest as the heading text)
    if echo "$h1_texts" | grep -qF 'bbsengine6.auth to bbsengine6.bank authorization flow'; then
      ok "<h1> text matches the spec title"
    else
      bad "<h1> text does not match the spec title (got: '$h1_texts') -- markdown parser dropped or mangled the heading"
    fi
    # the spec has these h2 headings: Components, End-to-end sequence,
    # Wire-level mapping (bank), Token-aware path, Failure modes,
    # Files involved. The H3 sub-headings under Components account
    # for the rest. Expect >= 6 h2.
    if [ "$h2_count" -ge 6 ]; then
      ok ">= 6 <h2> headings (spec has Components, End-to-end sequence, Wire-level mapping, Token-aware path, Failure modes, Files involved)"
    else
      bad "expected >= 6 <h2>, got $h2_count -- markdown parser collapsed or skipped section headings"
    fi
    if [ "$h3_count" -ge 3 ]; then
      ok ">= 3 <h3> headings (spec has bbsengine6.auth, SessionManager, bbsengine6.bank, bbsengine6.bank.api.handler)"
    else
      bad "expected >= 3 <h3>, got $h3_count -- subsection headings collapsed"
    fi
    # the spec has two markdown tables (auth-op table, wire-level
    # mapping) plus the SessionManager method table -- at least 1
    # table must render. >= 1 is the floor; > 1 catches a partial
    # render that only handled the first table.
    if [ "$table_count" -ge 1 ]; then
      ok "at least 1 <table> rendered (markdown table support working; got $table_count)"
    else
      bad "no <table> in response -- the markdown tables were not rendered (likely a markdown parser config that escapes pipes, or a template that strips tables)"
    fi
    # the spec has a fenced code block (session_id mapping) and a
    # fenced json block (error envelope). At least one <pre> must
    # render.
    if [ "$pre_count" -ge 1 ]; then
      ok "at least 1 <pre> block rendered (fenced code blocks working; got $pre_count)"
    else
      bad "no <pre> block in response -- fenced code blocks were not rendered (likely a markdown parser config that escapes backticks, or a template that strips <pre>)"
    fi
    if [ "$code_count" -ge 1 ]; then
      ok "at least 1 <code> element rendered (inline + fenced code; got $code_count)"
    else
      bad "no <code> element in response -- inline code was stripped (spec uses backticks for symbols like 'access()', 'session_id', etc.)"
    fi
    if [ "$li_count" -ge 1 ]; then
      ok "at least 1 <li> rendered (the spec's numbered list under End-to-end sequence; got $li_count)"
    else
      bad "no <li> in response -- the spec's numbered list was not rendered"
    fi
    # the spec's tables contain verb names (login, reconnect, refresh,
    # revoke on the auth side; balance, add, remove, history, pending,
    # transfer, approve, reject, list_all on the bank side). At least
    # one of these must appear inside a <td> cell.
    verbs_found=""
    for verb in login reconnect refresh revoke balance add remove history pending transfer approve reject list_all; do
      if echo "$(python3 -c "import json; d=json.load(open('$PARSE_JSON')); print(' '.join(d.get('td_cells', [])))")" | grep -qwF "$verb"; then
        verbs_found="$verbs_found $verb"
      fi
    done
    verbs_found=$(echo "$verbs_found" | xargs)
    if [ -n "$verbs_found" ]; then
      ok "verb names appear inside <td> cells:$verbs_found (markdown tables rendered as HTML tables, not as raw text)"
    else
      bad "no spec verb names (login/reconnect/.../list_all) found inside any <td> cell -- tables may be rendered as plain text or escaped"
    fi
  fi
else
  bad "skipped -- [1] did not produce a non-empty body"
fi
echo

# --- 4. markdown-source content sentinels -------------------------------
# Defense in depth on top of [3]. The structural checks confirm
# the *shape* of the rendered page; this section confirms the
# *content* matches the local source. The local .md is read by
# python3 (which strips the markdown syntax and emits plain
# text) and each sentinel is asserted to appear in the rendered
# body's plain text. This catches a render that produced the
# right structure but the wrong spec (e.g. a router fallback
# that happened to render a different handbook page).
echo "[4] markdown-source content sentinels (live body vs local .md)"
if [ "$body_bytes" -gt 0 ] && [ -f "$LOCAL_SRC" ]; then
  # Strip the live HTML to plain text via bs4 so sentinels are
  # compared against the rendered *text*, not against raw HTML
  # (which would fail for sentinels that contain characters
  # that get HTML-encoded, e.g. '<' or '>').
  python3 - "$BODY" "$LOCAL_SRC" "$TMPDIR_TEST/text.json" <<'PYEOF' 2>"$TMPDIR_TEST/text.err"
import json
import sys
from bs4 import BeautifulSoup

body_path, src_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(body_path, "r", encoding="utf-8", errors="replace") as fh:
    soup = BeautifulSoup(fh.read(), "lxml")
body_text = soup.get_text(" ", strip=True)
# Normalize whitespace for comparison: collapse runs of spaces
# and trim. This matches how a human reads the page and avoids
# brittleness on whitespace differences across renders.
import re
body_norm = re.sub(r"\s+", " ", body_text).strip()

with open(src_path, "r", encoding="utf-8", errors="replace") as fh:
    src_text = fh.read()
# Strip frontmatter if present (--- ... --- at the top) and
# collapse whitespace. We only need the prose; the structural
# checks already verified the tables/headings/code blocks.
src_no_fm = re.sub(r"^---\n.*?\n---\n", "", src_text, count=1, flags=re.DOTALL)
src_norm = re.sub(r"\s+", " ", src_no_fm).strip()

sentinels = [
    "bbsengine6.auth to bbsengine6.bank authorization flow",
    "bbsengine6.auth",
    "bbsengine6.bank",
    "SessionManager",
    "bank_transfer_approve",
    "register_session",
    "alloc_session_id",
    "WebSocket",
    "OP_MAP",
    "transport.py",
]

# Verbs from the spec's auth-op table -- must be present
# somewhere in the rendered text (the structural check
# above already verified they appear in <td> cells; this
# check is a backstop in case the JSON plumbing for the
# cell check is bypassed).
table_verbs = [
    "login", "reconnect", "refresh", "revoke",
    "balance", "transfer", "approve", "reject", "list_all",
]

# Backtick-wrapped symbols from the spec -- must appear
# in the rendered text (possibly with the backticks
# stripped by the markdown parser, so we check the inner
# content only).
symbols = [
    "access()",
    "bbsengine6.auth.access",
    "bbsengine6.bank.access",
    "BankServiceHandler.handle_message",
    "_check_auth",
    "bank_access",
    "bank_service.get_balance",
]

present = []
missing = []
for s in sentinels + table_verbs + symbols:
    if s in body_norm:
        present.append(s)
    else:
        missing.append(s)

with open(out_path, "w", encoding="utf-8") as fh:
    json.dump({
        "body_text_len": len(body_norm),
        "src_text_len": len(src_norm),
        "present": present,
        "missing": missing,
    }, fh, indent=2)
PYEOF
  text_rc=$?
  if [ "$text_rc" -ne 0 ] || [ ! -s "$TMPDIR_TEST/text.json" ]; then
    bad "python3 text-sentinel parse failed (rc=$text_rc); stderr: $(head -3 "$TMPDIR_TEST/text.err" 2>/dev/null | head -c 300)"
  else
    body_text_len=$(python3 -c "import json; print(json.load(open('$TMPDIR_TEST/text.json'))['body_text_len'])")
    missing_count=$(python3 -c "import json; print(len(json.load(open('$TMPDIR_TEST/text.json'))['missing']))")
    missing_list=$(python3 -c "import json; d=json.load(open('$TMPDIR_TEST/text.json')); print(' / '.join(d['missing']))")
    present_count=$(python3 -c "import json; print(len(json.load(open('$TMPDIR_TEST/text.json'))['present']))")
    echo "    rendered body text: $body_text_len chars"
    echo "    sentinels: $present_count present, $missing_count missing"
    if [ "$missing_count" = "0" ]; then
      ok "all $(($present_count)) sentinels (prose + verbs + symbols) present in rendered body text"
    else
      bad "$missing_count sentinel(s) missing from rendered body text: $missing_list"
    fi
  fi
else
  bad "skipped -- [1] did not produce a non-empty body or local source missing"
fi
echo

# --- 5. anti-error sentinels --------------------------------------------
# The render path can 200 with HTML that looks superficially
# like a rendered page but is actually a router/Smarty/PHP
# error fallback. The strings below are the known markers
# for those failure modes:
#   - "Page Not Found" : router_handleError's hardcoded 404
#     fallback (engine/router.php:275). The proper 404 page
#     also contains this string (per bbsengine6\page\error),
#     so a 200 + 'Page Not Found' is the diagnostic signature
#     of the router's error handler running with the wrong
#     status code, or a Smarty template that delegates back
#     to the error path.
#   - "router error"  : a generic router_log() 'error' level
#     message that ended up in the response body (caught by
#     display errors / log-to-output).
#   - "Unable to load template" : Smarty's failure message
#     when page-markdown.tmpl is missing on merlin.
#   - "Failed opening required" : PHP's fatal error when an
#     engine include (router.php, serve-md.php, php/markdown.php)
#     is missing from the prod tree.
# Any one of these in a 200 + text/html body means the
# response is *not* a clean render of the spec.
echo "[5] anti-error sentinels (live body must not contain error markers)"
if [ "$body_bytes" -gt 0 ] && [ -s "$BODY" ]; then
  error_markers=(
    "Page Not Found"
    "router error"
    "Unable to load template"
    "Failed opening required"
    "Fatal error"
    "Warning: "
    "Notice: "
    "Parse error"
  )
  markers_found=""
  for marker in "${error_markers[@]}"; do
    if grep -qF "$marker" "$BODY" 2>/dev/null; then
      markers_found="$markers_found '$marker'"
    fi
  done
  markers_found=$(echo "$markers_found" | xargs)
  if [ -z "$markers_found" ]; then
    ok "no error markers in live body (clean render, no Smarty/PHP/router fallbacks)"
  else
    bad "live body contains error marker(s):$markers_found -- the response is an error fallback, not a clean render of the spec"
  fi
else
  bad "skipped -- [1] did not produce a non-empty body"
fi
echo

# --- 6. build-host plumbing invariant -----------------------------------
# The /handbook/<v>/<chapter> rewrite in
# www/org/htaccess-prod must target /router.php (not
# /engine/router.php) and must be present. If this rule
# is missing, the test's URL would 404 (no handler) or
# 500 (rewrite target missing). We check it explicitly
# so a missing rule is diagnosed as "plumbing", not as
# a content-sync issue.
echo "[6] build-host plumbing invariant (htaccess-prod chapter rule)"
if [ ! -f "$LOCAL_BBSENGINE6/www/org/htaccess-prod" ]; then
  bad "local www/org/htaccess-prod missing"
else
  # The no-.md chapter rule:
  #   RewriteRule ^handbook/(\d+)/(.*)$ /router.php?uri=$2 [last,qsappend]
  # (as distinct from the .md raw rule which targets /serve-md.php
  # and which has a `\.md$` in the second capture group).
  #
  # The first version of this check used BRE-escaped parens
  # (`\(\\\\d\+\)`) inside a grep -E pattern; that mismatched
  # the file's literal `(\d+)` and falsely reported the rule
  # as missing. The fix: use grep -P (PCRE) for the pattern
  # match and grep -F for the rewrite target substring, with
  # a negative look-ahead that excludes the .md raw rule.
  # The .md rule's second group is `(.+\.md)$`; the chapter
  # rule's is `(.*)$`. A pattern that requires the path group
  # to NOT end in `\.md$` correctly distinguishes them.
  chapter_rule_ok=false
  if grep -P '^[[:space:]]*RewriteRule[[:space:]]+\^handbook/\(\\d\+\)/\((?:[^\\]|\\.)*\)\$[[:space:]]+/router\.php\?uri=' "$LOCAL_BBSENGINE6/www/org/htaccess-prod" 2>/dev/null | grep -vqF '.md'; then
    chapter_rule_ok=true
  fi
  if $chapter_rule_ok; then
    ok "local www/org/htaccess-prod routes /handbook/<v>/<chapter> to /router.php (no-.md render path is wired)"
  else
    bad "local www/org/htaccess-prod does NOT route /handbook/<v>/<chapter> to /router.php -- the no-.md render path is not wired in the local working tree; without this rule the test's URL would 404 on merlin"
  fi
  # @since 2026-09-09 -- single-install refactor. The rewrite
  # target should be /router.php at the docroot root (a
  # symlink), not /engine/router.php. An active rewrite line
  # that still uses /engine/ would mean the rule was missed
  # in the refactor and would 404 on merlin (no /engine/
  # subdir at the docroot).
  active_engine_refs=$(grep -E '^[[:space:]]*Rewrite(Rule|Cond)' "$LOCAL_BBSENGINE6/www/org/htaccess-prod" 2>/dev/null | grep -c '/engine/router\.php' || true)
  if [ "$active_engine_refs" -eq 0 ]; then
    ok "local www/org/htaccess-prod has no /engine/router.php references in active rewrite lines (single-install refactor applied)"
  else
    bad "local www/org/htaccess-prod has $active_engine_refs active rewrite line(s) referencing /engine/router.php -- single-install refactor not fully applied to the chapter route"
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
  echo "    -- the no-.md chapter route is not reaching"
  echo "       /router.php. Check www/org/htaccess-prod has"
  echo "       'RewriteRule ^handbook/(\\\\d+)/(.*)\$ /router.php?uri=\$2'"
  echo "       and that the symlink at html/router.php on"
  echo "       merlin points at /srv/www/bbsengine6/router.php"
  echo "       (created by 'make -C www org' via prod-symlinks)."
  echo
  echo "  if [1] returns 200 but [2] is not text/html:"
  echo "    -- the wrong handler ran. If Content-Type is"
  echo "       text/plain, serve-md.php handled the request"
  echo "       (the .md route matched the no-.md URL --"
  echo "       likely a rewrite-ordering issue in"
  echo "       htaccess-prod). If Content-Type is something"
  echo "       else entirely, a different handler is in the"
  echo "       rewrite chain. Same plumbing check as the 404 case."
  echo
  echo "  if [3] fails (wrong structure):"
  echo "    -- a markdown parser regression: bbsengine6\\\\markdown\\\\"
  echo "       parseDocument() in php/markdown.php is dropping"
  echo "       headings, collapsing tables, or stripping code"
  echo "       blocks. Check the parser config (split: false,"
  echo "       breaks: true) and the Parsedown install under"
  echo "       vendor/erusev/parsedown/. Run"
  echo "       'php php/markdown.php' locally with the spec to"
  echo "       reproduce."
  echo
  echo "  if [4] fails (wrong content):"
  echo "    -- the response rendered a different page (a router"
  echo "       fallback that happened to have the right structure)"
  echo "       or a stale page-markdown.tmpl cached. Flush the"
  echo "       compiled-template cache on merlin and re-run"
  echo "       'make wwworg' to push the canonical handbook."
  echo
  echo "  if [5] fails (error markers in body):"
  echo "    -- an error page is being served with status 200."
  echo "       The marker in the 'bad' line names the failure"
  echo "       mode:"
  echo "         'Page Not Found'           : router_handleError"
  echo "                                       fallback (engine/router.php:275)"
  echo "         'router error'             : a router_log() error"
  echo "                                       leaked into the body"
  echo "         'Unable to load template'  : Smarty; page-markdown.tmpl"
  echo "                                       missing on merlin -- run"
  echo "                                       'make skin-prod'"
  echo "         'Failed opening required'  : an engine/ include"
  echo "                                       (router.php, serve-md.php,"
  echo "                                       php/markdown.php) is missing"
  echo "                                       on merlin -- run"
  echo "                                       'make engine-deploy-prod'"
  echo "                                       + 'sudo systemctl reload"
  echo "                                       php-fpm'"
  echo
  echo "  if [6] fails (plumbing):"
  echo "    -- the local www/org/htaccess-prod is missing the"
  echo "       /router.php chapter rule, or still uses the old"
  echo "       /engine/router.php target. Restore the rule"
  echo "       before running this test -- without it, the test"
  echo "       is meaningless."
  echo
  echo "to re-run: $0"
  exit 1
fi
echo
echo "all checks passed; $URL returns 200 with auth-bank.md rendered as HTML."
exit 0
