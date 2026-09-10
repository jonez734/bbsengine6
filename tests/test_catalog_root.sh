#!/usr/bin/env bash
# test_catalog_root.sh
# Verifies bbsengine6\util\catalog_root() in php/util.php.
#
# catalog_root() is the new (2026-09-10) sibling of
# bbsengine6\util\handbook_home() and bbsengine6\util\teos_dir().
# It returns the teos catalog content root, with this
# resolution order:
#   1. getenv('CATALOG_ROOT')
#   2. defined('CATALOG_ROOT') constant
#   3. getenv('TEOSDIR')
#   4. defined('TEOSDIR') constant
#   5. hardcoded default (teos docroot)
#
# What this test checks:
#   [1] default (no env, no constant) returns the teos docroot
#   [2] CATALOG_ROOT env override wins
#   [3] CATALOG_ROOT env trailing-slash is normalized
#   [4] CATALOG_ROOT constant wins when env is empty
#   [5] TEOSDIR env still honored when CATALOG_ROOT is unset
#       (backward compat with existing vhost configs)
#   [6] TEOSDIR constant still honored when env is empty
#   [7] CATALOG_ROOT env beats TEOSDIR env (the new var wins)
#   [8] teos_dir() and catalog_root() return the same value
#       (they're aliases; teos_dir() delegates to catalog_root())

set -u

BBSENGINE6="/home/opencode/data/work/bbsengine6"
UTIL="$BBSENGINE6/php/util.php"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

runphp() {
  # $1 = PHP snippet (single expression expected).
  php -d display_errors=0 -r "
    require_once('$UTIL');
    \$__v = ($1);
    if (\$__v === false) echo '<<<FALSE>>>';
    elseif (\$__v === null) echo '<<<NULL>>>';
    elseif (\$__v === '') echo '<<<EMPTY>>>';
    else echo '<<<' . (string)\$__v . '>>>';
  " 2>/dev/null
}

extract() {
  local raw="$1"
  case "$raw" in
    "<<<FALSE>>>") echo "__FALSE__" ;;
    "<<<NULL>>>")  echo "__NULL__" ;;
    "<<<EMPTY>>>") echo "__EMPTY__" ;;
    "<<<>>>"|"")   echo "" ;;
    *)             echo "${raw#<<<}" | sed 's/>>>$//' ;;
  esac
}

# --- 0. preconditions ---
echo "[0] preconditions"
if [ ! -f "$UTIL" ]; then
  bad "php/util.php not found at $UTIL"
  echo "    cannot continue"
  exit 1
fi
ok "php/util.php exists"
if ! command -v php >/dev/null 2>&1; then
  bad "php CLI not available on PATH"
  echo "    cannot continue"
  exit 1
fi
ok "php CLI available"
echo

# --- 1. default ---
echo "[1] catalog_root() default (no env, no constant)"
val=$(extract "$(env -u CATALOG_ROOT env -u TEOSDIR php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\catalog_root();
" 2>/dev/null)")
expected="/srv/www/vhosts/zoidtechnologies.com/html/teos/"
if [ "$val" = "$expected" ]; then
  ok "catalog_root() returns '$val'"
else
  bad "catalog_root() returned '$val', expected '$expected'"
fi
echo

# --- 2. CATALOG_ROOT env override ---
echo "[2] catalog_root() honors CATALOG_ROOT env override"
val=$(CATALOG_ROOT=/srv/www/vhosts/zoidtechnologies.com/html/teos/ php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\catalog_root();
" 2>/dev/null)
expected="/srv/www/vhosts/zoidtechnologies.com/html/teos/"
if [ "$val" = "$expected" ]; then
  ok "CATALOG_ROOT env -> catalog_root() returns '$val'"
else
  bad "CATALOG_ROOT env -> catalog_root() returned '$val', expected '$expected'"
fi
echo

# --- 3. trailing-slash normalization ---
echo "[3] catalog_root() normalizes trailing slashes"
val=$(CATALOG_ROOT=/tmp/no-slash php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\catalog_root();
" 2>/dev/null)
expected="/tmp/no-slash/"
if [ "$val" = "$expected" ]; then
  ok "CATALOG_ROOT without trailing slash normalized to '$val'"
else
  bad "CATALOG_ROOT normalization: got '$val', expected '$expected'"
fi
echo

# --- 4. CATALOG_ROOT constant override ---
echo "[4] catalog_root() honors CATALOG_ROOT constant when env is empty"
val=$(env -u CATALOG_ROOT env -u TEOSDIR php -r "
  require_once('$UTIL');
  define('CATALOG_ROOT', '/const/catalog');
  echo \bbsengine6\util\catalog_root();
" 2>/dev/null)
expected="/const/catalog/"
if [ "$val" = "$expected" ]; then
  ok "CATALOG_ROOT constant -> catalog_root() returns '$val'"
else
  bad "CATALOG_ROOT constant -> catalog_root() returned '$val', expected '$expected'"
fi
echo

# --- 5. TEOSDIR env backward compat ---
echo "[5] catalog_root() falls back to TEOSDIR env (backward compat)"
val=$(env -u CATALOG_ROOT TEOSDIR=/from/teosdir php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\catalog_root();
" 2>/dev/null)
expected="/from/teosdir/"
if [ "$val" = "$expected" ]; then
  ok "TEOSDIR env fallback -> catalog_root() returns '$val'"
else
  bad "TEOSDIR env fallback: got '$val', expected '$expected'"
fi
echo

# --- 6. TEOSDIR constant backward compat ---
echo "[6] catalog_root() falls back to TEOSDIR constant (backward compat)"
val=$(env -u CATALOG_ROOT env -u TEOSDIR php -r "
  require_once('$UTIL');
  define('TEOSDIR', '/const/teosdir');
  echo \bbsengine6\util\catalog_root();
" 2>/dev/null)
expected="/const/teosdir/"
if [ "$val" = "$expected" ]; then
  ok "TEOSDIR constant fallback -> catalog_root() returns '$val'"
else
  bad "TEOSDIR constant fallback: got '$val', expected '$expected'"
fi
echo

# --- 7. CATALOG_ROOT env beats TEOSDIR env ---
echo "[7] CATALOG_ROOT env wins over TEOSDIR env"
val=$(env -u CATALOG_ROOT -u TEOSDIR sh -c '
  export CATALOG_ROOT=/from/catalog
  export TEOSDIR=/from/teosdir
  php -r "
    require_once(\"'$UTIL'\");
    echo \bbsengine6\util\catalog_root();
  "
' 2>/dev/null)
expected="/from/catalog/"
if [ "$val" = "$expected" ]; then
  ok "CATALOG_ROOT beats TEOSDIR: catalog_root() returned '$val'"
else
  bad "CATALOG_ROOT should beat TEOSDIR: got '$val', expected '$expected'"
fi
echo

# --- 8. teos_dir() == catalog_root() ---
echo "[8] teos_dir() and catalog_root() are equivalent"
val_td=$(env -u CATALOG_ROOT env -u TEOSDIR php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\teos_dir();
" 2>/dev/null)
val_cr=$(env -u CATALOG_ROOT env -u TEOSDIR php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\catalog_root();
" 2>/dev/null)
if [ "$val_td" = "$val_cr" ]; then
  ok "both return '$val_td'"
else
  bad "teos_dir()='$val_td' but catalog_root()='$val_cr' (they should match)"
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
  exit 1
fi
echo
echo "all checks passed; bbsengine6\\util\\catalog_root() behaves correctly."
exit 0
