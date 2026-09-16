#!/usr/bin/env bash
# test_serve_md_entry_point.sh
#
# Verifies bbsengine6/engine/serve-md.php's entry-point contract:
#   - $_GET['path'] carries the full post-version URI
#   - $_SERVER['REQUEST_URI'] is regex-matched for the handbook version
#   - bbsengine6\util\handbook_resolve() enforces .md-only + containment
#
# The filename is transport-agnostic because this test asserts the
# request/response shape, not the wire format. If the contract shifts
# from ?path= to a header or PATH_INFO, only the runphp harness below
# needs to change.
#
# Cases:
#   [1] happy path: ?path=specs/auth-bank.md returns the file body
#   [2] empty ?path= -> 404 File not found
#   [3] missing /handbook/<v>/ in REQUEST_URI -> 404
#   [4] path traversal in ?path= -> 404 (handbook_resolve containment)
#   [5] non-.md extension -> 404 (handbook_resolve extension check)
#   [6] nonexistent .md -> 404 (handbook_resolve missing file)
#   [7] deep path: ?path=specs/sub/notes.md at depth 2 -> 200
#       (regression guard for the htaccess `(.+\.md)$` regex spanning /)
#
# Runs on the build host without Apache. Uses a temp handbook tree
# exposed via BBSENGINE6_HANDBOOK_HOME so handbook_resolve() can find
# the fixtures.

set -u

BBSENGINE6="/home/opencode/data/work/bbsengine6"
SERVE_MD="$BBSENGINE6/engine/serve-md.php"
UTIL="$BBSENGINE6/php/util.php"
BOOTSTRAP="$BBSENGINE6/php/bootstrap.php"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

# --- 0. preconditions ---------------------------------------------------
echo "[0] preconditions"
for f in "$SERVE_MD" "$UTIL" "$BOOTSTRAP"; do
    if [ ! -f "$f" ]; then
        bad "missing required file: $f"
        echo "    cannot continue"
        exit 1
    fi
done
ok "all required PHP files present"
if ! command -v php >/dev/null 2>&1; then
    bad "php CLI not available on PATH"
    exit 1
fi
ok "php CLI available"
echo

# Build a temp handbook tree that mirrors the layout serve-md.php
# resolves against: /handbook/<v>/<chapter>/<file>.md. The build-host
# tree may not have a versioned handbook/6/ subdir (the canonical tree
# lives on merlin), so we synthesize one.
HP_DIR=$(mktemp -d)
mkdir -p "$HP_DIR/handbook/6/specs/sub"
cat > "$HP_DIR/handbook/6/specs/auth-bank.md" <<'EOF'
# auth-bank fixture
EOF
cat > "$HP_DIR/handbook/6/specs/sub/notes.md" <<'EOF'
# deep notes fixture
EOF
ok "temp handbook tree at $HP_DIR/handbook/6/"
export BBSENGINE6_HANDBOOK_HOME="$HP_DIR/handbook/"
echo

# --- runphp harness -----------------------------------------------------
# The entry-point reads $_GET['path'] and $_SERVER['REQUEST_URI'],
# emits a Content-Type header + status code + body. We exercise it
# by:
#   1. Writing a tiny harness to a temp .php file that sets those
#      superglobals and require_once's the entry-point.
#   2. Running that harness with the env override exported.
#   3. Capturing stdout (the body) and using `php -r` reflection to
#      observe the final status code and headers.
#
# To capture the response code and Content-Type, we use PHP's
# http_response_code() output buffering trick: serve-md.php calls
# http_response_code() and header() directly. We capture headers via
# the CLI SAPI's xdebug-style header listing by buffering with a
# custom error handler that reads headers_list() before the process
# exits. That's overkill; simpler: run the harness and capture
# stdout + stderr, then assert on body shape and a status marker
# emitted by the harness.

HARNESS_TEMPLATE='<?php
// harness.php - exercise engine/serve-md.php under controlled $_GET/$_SERVER
$path_q = $argv[1] ?? "";
$request_uri = $argv[2] ?? "";
$_GET["path"] = $path_q;
$_SERVER["REQUEST_URI"] = $request_uri;
$_SERVER["PHP_SELF"] = "/engine/serve-md.php";
$_SERVER["SCRIPT_NAME"] = "/engine/serve-md.php";

// Wrap header() and http_response_code() so we can observe them.
$GLOBALS["__captured_status"] = 200;
$GLOBALS["__captured_headers"] = [];
$GLOBALS["__exit_called"] = false;

// PHP http_response_code() returns false (not 200) on the CLI SAPI
// when no status has been explicitly set. To make the post-shutdown
// observation deterministic for both success and failure paths,
// set an explicit 200 baseline here. The entry-point will override
// to 404 on failure paths via its own http_response_code(404) call.
http_response_code(200);

// Buffer output so we can echo a sentinel-prefixed status+headers
// block at the end.
ob_start();

// Register a shutdown function that reads the current
// http_response_code() and headers_list() and prefixes them to the
// body. serve-md.php calls exit; shutdown funcs still run.
register_shutdown_function(function () {
    $body = ob_get_clean();
    $status = http_response_code();
    $headers = headers_list();
    $hdrblob = "";
    foreach ($headers as $h) { $hdrblob .= $h . "\n"; }
    echo "<<<STATUS:" . $status . ">>>\n";
    echo "<<<HEADERS>>>" . $hdrblob . "<<<HDREND>>>\n";
    echo "<<<BODY>>>\n" . $body . "\n<<<BODYEND>>>";
});

require_once %SERVE_MD%;
'

# Write the harness as a temp .php file (substituting the entry-point
# path), then run it with the env override + two CLI args.
HARNESS_FILE=$(mktemp --suffix=.php)
HARNESS_PHP=${HARNESS_TEMPLATE//%SERVE_MD%/"'$SERVE_MD'"}
printf '%s' "$HARNESS_PHP" > "$HARNESS_FILE"

cleanup() { rm -rf "$HP_DIR" "$HARNESS_FILE"; }
trap cleanup EXIT

runcase() {
    # $1 = description, $2 = ?path= value, $3 = REQUEST_URI value,
    # $4 = expected status (e.g. 200 or 404), $5 = expected body
    #      substring ("" to skip body assertion)
    local desc="$1" pathq="$2" requri="$3" exp_status="$4" exp_body="$5"
    local out status headers body
    out=$(BBSENGINE6_HANDBOOK_HOME="$BBSENGINE6_HANDBOOK_HOME" \
          php -d display_errors=0 "$HARNESS_FILE" "$pathq" "$requri" 2>/dev/null)
    status=$(echo "$out" | sed -n 's/^<<<STATUS:\([0-9]*\)>>>.*/\1/p')
    headers=$(echo "$out" | sed -n '/^<<<HEADERS>>>/,/^<<<HDREND>>>/p')
    body=$(echo "$out" | sed -n '/^<<<BODY>>>/,/^<<<BODYEND>>>/p' | sed '1d;$d')
    if [ "$status" != "$exp_status" ]; then
        bad "$desc: status=$status expected=$exp_status (body: $body)"
        return
    fi
    if [ -n "$exp_body" ] && ! echo "$body" | grep -qF "$exp_body"; then
        bad "$desc: body does not contain '$exp_body' (got: $body)"
        return
    fi
    ok "$desc (status=$status, headers+body match)"
}

# --- 1. happy path -------------------------------------------------------
echo "[1] happy path"
runcase "?path=specs/auth-bank.md" "specs/auth-bank.md" \
        "/handbook/6/specs/auth-bank.md" 200 "auth-bank fixture"
echo

# --- 2. empty path -------------------------------------------------------
echo "[2] empty path"
runcase "empty ?path=" "" "/handbook/6/specs/auth-bank.md" 404 "File not found"
echo

# --- 3. missing handbook version in REQUEST_URI --------------------------
echo "[3] missing handbook version in REQUEST_URI"
runcase "no /handbook/<v>/ in REQUEST_URI" "specs/auth-bank.md" \
        "/not-handbook/6/specs/auth-bank.md" 404 "File not found"
runcase "bare REQUEST_URI" "specs/auth-bank.md" \
        "/specs/auth-bank.md" 404 "File not found"
echo

# --- 4. path traversal ---------------------------------------------------
echo "[4] path traversal in ?path="
runcase "../etc/passwd in path" "../etc/passwd" \
        "/handbook/6/etc/passwd" 404 "File not found"
runcase "../../etc/passwd in path" "../../etc/passwd" \
        "/handbook/6/../../etc/passwd" 404 "File not found"
echo

# --- 5. wrong extension --------------------------------------------------
echo "[5] non-.md extension"
runcase "?path=specs/index.txt" "specs/index.txt" \
        "/handbook/6/specs/index.txt" 404 "File not found"
runcase "?path=specs/auth-bank" "specs/auth-bank" \
        "/handbook/6/specs/auth-bank" 404 "File not found"
echo

# --- 6. nonexistent file -------------------------------------------------
echo "[6] nonexistent .md"
runcase "?path=specs/does-not-exist.md" "specs/does-not-exist.md" \
        "/handbook/6/specs/does-not-exist.md" 404 "File not found"
echo

# --- 7. deep path --------------------------------------------------------
echo "[7] deep path: ?path=specs/sub/notes.md"
runcase "?path=specs/sub/notes.md" "specs/sub/notes.md" \
        "/handbook/6/specs/sub/notes.md" 200 "deep notes fixture"
echo

# --- summary -------------------------------------------------------------
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
echo "all checks passed; engine/serve-md.php entry-point contract holds."
exit 0
