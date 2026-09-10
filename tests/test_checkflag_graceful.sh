#!/usr/bin/env bash
# test_checkflag_graceful.sh
#
# Verifies that the working-tree bbsengine6\php\libmember.php
# checkflag() function is graceful about database failures.
#
# Background: on 2026-09-10 the live /rec/arts/tv/ URL on
# the teos vhost 500'd with
#   SQLSTATE[42883]: function engine.checkflag(unknown,
#   unknown) does not exist
# because the engine schema had been migrated to a version
# where the function signature was different. The call chain
# was engine.php:607 -> member\lib\checkflag() ->
# engine.checkflag SQL function. The fix wraps the SQL call
# in try/catch so the caller's `if (checkflag())` branch
# evaluates to false and the page renders successfully.
#
# What this test checks:
#   [1] working-tree libmember.php lints clean
#   [2] checkflag() with SQLite (no engine.checkflag) returns null
#   [3] checkflag() with SQLite emits a log entry mentioning the failure
#   [4] checkflag() with null moniker does not throw
#   [5] checkflag() with unreachable DB (connect throws) returns null
#   [6] the raw query that the function uses would throw without
#       the wrapper (proves the test exercises the failure path)
#
# How the test works:
#   The PHP harness is written to a stable file (not mktemp)
#   so it persists for debugging. It defines stub
#   bbsengine6\database\* and bbsengine6\util\logentry in
#   their own namespaces, then evals only the active
#   checkflag() function from the working-tree libmember.php
#   (the one at line 130, not the commented-out one at line 49).
#   This isolates checkflag() from the rest of the bbsengine6
#   runtime (PEAR, Smarty, etc.) so the test runs in <100ms.

set -u

WORKTREE="/home/opencode/data/work"
LIBMEMBER="$WORKTREE/bbsengine6/php/libmember.php"
HARNESS="/tmp/checkflag_graceful_harness.php"
pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

# --- preconditions ---
echo "[0] preconditions"
if [ ! -f "$LIBMEMBER" ]; then
  bad "missing $LIBMEMBER"
  exit 1
fi
ok "libmember.php exists"
if ! command -v php >/dev/null 2>&1; then
  bad "php CLI not available on PATH"
  exit 1
fi
ok "php CLI available"
echo

# --- 1. lints clean ---
echo "[1] libmember.php lints clean"
if php -l "$LIBMEMBER" 2>&1 | grep -q "No syntax errors"; then
  ok "php -l passes"
else
  bad "php -l reports errors:"
  php -l "$LIBMEMBER" 2>&1 | sed 's/^/      /'
  exit 1
fi
echo

# --- write the PHP harness (kept stable for debugging) ---
cat > "$HARNESS" <<'PHP'
<?php
namespace bbsengine6\database {
    $GLOBALS['__shim_getDSN'] = $argv[3] ?? 'sqlite::memory:';
    function connect($dsn) {
        if (is_string($dsn) && str_starts_with($dsn, 'sqlite:')) {
            $pdo = new \PDO($dsn);
            $pdo->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);
            return $pdo;
        }
        throw new \PDOException("could not find driver (shim)");
    }
    function getDSN() { return $GLOBALS['__shim_getDSN']; }
    function query($dbh, $sql, $params = []) {
        $stmt = $dbh->prepare($sql);
        $stmt->execute($params);
        return $stmt;
    }
}
namespace bbsengine6\util {
    function logentry($msg) {
        global $test_log;
        $test_log[] = $msg;
    }
    function echo_traceback($msg) { /* noop */ }
    function actionlog($note = null, $moniker = null) { /* noop */ }
}
namespace bbsengine6\member\lib {
    function getDSN() { return \bbsengine6\database\getDSN(); }
    function getcurrentmoniker() { return 'shim-moniker'; }
}
namespace {

function load_active_checkflag(string $libmember_path): string {
    $src = file_get_contents($libmember_path);
    if (!preg_match('/(\* \@param string \$name.*?^     \})/sm', $src, $m)) {
        fwrite(STDERR, "could not extract checkflag block\n");
        exit(1);
    }
    if (!preg_match('/(function checkflag\b.*?\n     \})/s', $m[1], $m2)) {
        fwrite(STDERR, "could not find function body\n");
        exit(1);
    }
    $fn = preg_replace('/^     /m', '    ', $m2[1]);
    return "namespace bbsengine6\\member\\lib {\n" . $fn . "\n}\n";
}

function run_scenario(string $name, callable $fn): array {
    global $test_log;
    $test_log = [];
    try {
        $r = $fn();
        return ['threw' => false, 'result' => $r, 'log' => $test_log];
    } catch (\Throwable $e) {
        return ['threw' => true, 'message' => $e->getMessage(), 'log' => $test_log];
    }
}

$scenario = $argv[1] ?? 'A';
$code = load_active_checkflag($argv[2]);
eval($code);

if ($scenario === 'A') {
    $r = run_scenario('A', fn() => \bbsengine6\member\lib\checkflag("SYSOP", "test-moniker"));
} elseif ($scenario === 'B') {
    $r = run_scenario('B', fn() => \bbsengine6\member\lib\checkflag("APPROVED", null));
} elseif ($scenario === 'C') {
    $GLOBALS['__shim_getDSN'] = 'pgsql:host=127.0.0.1;port=5432;dbname=unreachable';
    $r = run_scenario('C', fn() => \bbsengine6\member\lib\checkflag("SYSOP", "test"));
    $GLOBALS['__shim_getDSN'] = 'sqlite::memory:';
}

echo "THREW=" . ($r['threw'] ? "1" : "0") . "\n";
if ($r['threw']) {
    echo "MESSAGE=" . substr($r['message'], 0, 200) . "\n";
} else {
    echo "RESULT_TYPE=" . gettype($r['result']) . "\n";
    echo "RESULT_VALUE=" . var_export($r['result'], true) . "\n";
}
echo "LOG_COUNT=" . count($r['log']) . "\n";
foreach ($r['log'] as $i => $m) {
    echo "LOG[$i]=" . substr($m, 0, 150) . "\n";
}
}
PHP

run_scenario() {
  local label="$1" scenario="$2"
  out=$(php -d display_errors=0 -d log_errors=0 "$HARNESS" "$scenario" "$LIBMEMBER" 2>/dev/null)
  echo "$out"
}

# --- 2-3. scenario A: SQLite, no engine.checkflag ---
echo "[2-3] checkflag() with SQLite (no engine.checkflag)"
out=$(run_scenario A A)
threw=$(echo "$out" | grep '^THREW=' | cut -d= -f2-)
result_value=$(echo "$out" | grep '^RESULT_VALUE=' | cut -d= -f2-)
log_count=$(echo "$out" | grep '^LOG_COUNT=' | cut -d= -f2-)
log0=$(echo "$out" | grep '^LOG\[0\]=' | cut -d= -f2-)

if [ "$threw" = "1" ]; then
  bad "checkflag() THREW: $(echo "$out" | grep '^MESSAGE=' | cut -d= -f2-)"
else
  if [ "$result_value" = "NULL" ]; then
    ok "checkflag() returned null"
  else
    bad "checkflag() returned: $result_value (expected NULL)"
  fi
fi
if [ "$log_count" = "1" ] 2>/dev/null; then
  ok "1 log entry emitted"
  if echo "$log0" | grep -q "libmember.checkflag.*-fail"; then
    ok "log mentions the failure: $log0"
  else
    bad "log doesn't mention libmember.checkflag.*-fail: $log0"
  fi
else
  bad "expected 1 log entry, got $log_count"
fi
echo

# --- 4. scenario B: null moniker ---
echo "[4] checkflag() with null moniker"
out=$(run_scenario B B)
threw=$(echo "$out" | grep '^THREW=' | cut -d= -f2-)
result_value=$(echo "$out" | grep '^RESULT_VALUE=' | cut -d= -f2-)

if [ "$threw" = "1" ]; then
  bad "checkflag(null moniker) THREW: $(echo "$out" | grep '^MESSAGE=' | cut -d= -f2-)"
else
  ok "checkflag(null moniker) returned gracefully: $result_value"
fi
echo

# --- 5. scenario C: unreachable DB ---
echo "[5] checkflag() with unreachable DB (connect throws)"
out=$(run_scenario C C)
threw=$(echo "$out" | grep '^THREW=' | cut -d= -f2-)
result_value=$(echo "$out" | grep '^RESULT_VALUE=' | cut -d= -f2-)
log_count=$(echo "$out" | grep '^LOG_COUNT=' | cut -d= -f2-)
log0=$(echo "$out" | grep '^LOG\[0\]=' | cut -d= -f2-)

if [ "$threw" = "1" ]; then
  bad "checkflag() THREW on unreachable DB: $(echo "$out" | grep '^MESSAGE=' | cut -d= -f2-)"
else
  if [ "$result_value" = "NULL" ]; then
    ok "checkflag() returned null on unreachable DB"
  else
    bad "checkflag() returned: $result_value (expected NULL)"
  fi
fi
if [ "$log_count" = "1" ] 2>/dev/null; then
  if echo "$log0" | grep -q "libmember.checkflag.connect-fail"; then
    ok "log mentions connect-fail: $log0"
  else
    bad "log doesn't mention connect-fail: $log0"
  fi
else
  bad "expected 1 log entry, got $log_count"
fi
echo

# --- 6. raw query throws (proves test exercises failure path) ---
echo "[6] raw query (no wrapper) does throw -- proves test is meaningful"
out=$(php -d display_errors=0 -d log_errors=0 -r '
try {
    $pdo = new PDO("sqlite::memory:");
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $stmt = $pdo->prepare("select engine.checkflag(:name, :moniker)");
    $stmt->execute(["name" => "foo", "moniker" => "bar"]);
    echo "NO_THROW\n";
} catch (\Throwable $e) {
    echo "THREW=" . substr($e->getMessage(), 0, 80) . "\n";
}
' 2>/dev/null)
if echo "$out" | grep -q "^THREW="; then
  ok "raw query throws: $(echo "$out" | grep '^THREW=' | cut -d= -f2-)"
else
  bad "raw query did not throw (test would be meaningless)"
fi
echo

# --- summary ---
echo "=== summary ==="
echo "passed: $pass"
echo "failed: $fail"
if [ "$fail" -gt 0 ]; then
  echo
  echo "diagnosis:"
  printf "%b\n" "$diagnosis"
  echo
  echo "to re-run: $0"
  echo "harness kept at: $HARNESS (rerun manually for debugging)"
  exit 1
fi
echo
echo "checkflag() is graceful about DB failures (returns null, logs the issue)."
echo "harness at: $HARNESS (delete manually to clean up)"
exit 0
