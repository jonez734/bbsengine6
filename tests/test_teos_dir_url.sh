#!/usr/bin/env bash
# test_teos_dir_url.sh
# Verifies bbsengine6\util\teos_dir() and
# bbsengine6\util\teos_url() in php/util.php.
#
# These helpers are the single source of truth for the
# vhost-polymorphic TEOSDIR / TEOSURL constants. router.php
# putenv()s them per request (handbook vs teos), and the
# helpers prefer env over defined-constant over hardcoded
# default.
#
# What this test checks:
#   [1] teos_dir() with no env / no constant returns the
#       hardcoded teos docroot (with trailing slash).
#   [2] teos_dir() returns the value of a TEOSDIR env override.
#   [3] teos_dir() normalizes trailing slashes.
#   [4] teos_dir() returns the value of a defined TEOSDIR
#       constant when env is empty.
#   [5] teos_dir() is consistent across calls.
#   [6] teos_url() with no env / no constant returns '' (matches
#       bare-constant behavior used by engine.php/folder.php).
#   [7] teos_url() returns the value of a TEOSURL env override.
#   [8] teos_url() returns the value of a defined TEOSURL
#       constant when env is empty.
#   [9] env wins over constant (the production pattern:
#       router.php putenv()'s and callers should see the env).

set -u

BBSENGINE6="/home/opencode/data/work/bbsengine6"
UTIL="$BBSENGINE6/php/util.php"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

runphp() {
  # $1 = PHP snippet (single expression expected). Sentinel-wrapped
  # so empty/false/null can be distinguished.
  php -d display_errors=0 -r "
    require_once('$UTIL');
    \$__v = ($1);
    if (\$__v === false) {
        echo '<<<FALSE>>>';
    } elseif (\$__v === null) {
        echo '<<<NULL>>>';
    } elseif (\$__v === '') {
        echo '<<<EMPTY>>>';
    } else {
        echo '<<<' . (string)\$__v . '>>>';
    }
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

# --- 0. preconditions ---------------------------------------------------
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

# --- 1. teos_dir() default ---------------------------------------------
echo "[1] teos_dir() default (no env, no constant)"
unset TEOSDIR
val=$(extract "$(env -u TEOSDIR php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\teos_dir();
" 2>/dev/null)")
expected="/srv/www/vhosts/zoidtechnologies.com/html/teos/"
if [ "$val" = "$expected" ]; then
  ok "teos_dir() returns '$val'"
elif [ "$val" = "__EMPTY__" ] || [ "$val" = "__NULL__" ] || [ "$val" = "__FALSE__" ]; then
  bad "teos_dir() returned sentinel $val (expected the hardcoded teos path)"
else
  bad "teos_dir() returned '$val', expected '$expected'"
fi
echo

# --- 2. teos_dir() env override ----------------------------------------
echo "[2] teos_dir() honors TEOSDIR env override"
val=$(TEOSDIR=/srv/www/vhosts/www.bbsengine.org/html/handbook/6/ php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\teos_dir();
" 2>/dev/null)
expected="/srv/www/vhosts/www.bbsengine.org/html/handbook/6/"
if [ "$val" = "$expected" ]; then
  ok "TEOSDIR env -> teos_dir() returns '$val'"
else
  bad "TEOSDIR env -> teos_dir() returned '$val', expected '$expected'"
fi
echo

# --- 3. teos_dir() trailing-slash normalization ------------------------
echo "[3] teos_dir() normalizes trailing slashes"
# Pass without trailing slash; helper should append one.
val=$(TEOSDIR=/tmp/no-trailing-slash php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\teos_dir();
" 2>/dev/null)
expected="/tmp/no-trailing-slash/"
if [ "$val" = "$expected" ]; then
  ok "TEOSDIR without trailing slash normalized to '$val'"
else
  bad "TEOSDIR normalization: got '$val', expected '$expected'"
fi
# Pass with trailing slash; should not double up.
val=$(TEOSDIR=/tmp/with-trailing-slash/ php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\teos_dir();
" 2>/dev/null)
expected="/tmp/with-trailing-slash/"
if [ "$val" = "$expected" ]; then
  ok "TEOSDIR with trailing slash stays at '$val' (no double slash)"
else
  bad "TEOSDIR trailing slash: got '$val', expected '$expected'"
fi
echo

# --- 4. teos_dir() constant override -----------------------------------
echo "[4] teos_dir() honors TEOSDIR constant when env is empty"
val=$(env -u TEOSDIR php -r "
  require_once('$UTIL');
  define('TEOSDIR', '/const/path');
  echo \bbsengine6\util\teos_dir();
" 2>/dev/null)
expected="/const/path/"
if [ "$val" = "$expected" ]; then
  ok "TEOSDIR constant -> teos_dir() returns '$val'"
else
  bad "TEOSDIR constant -> teos_dir() returned '$val', expected '$expected'"
fi
echo

# --- 5. teos_dir() idempotency -----------------------------------------
echo "[5] teos_dir() is consistent across calls"
val1=$(TEOSDIR=/foo/bar php -r "require_once('$UTIL'); echo \bbsengine6\util\teos_dir();")
val2=$(TEOSDIR=/foo/bar php -r "require_once('$UTIL'); echo \bbsengine6\util\teos_dir();")
if [ "$val1" = "$val2" ]; then
  ok "teos_dir() returns '$val1' both times"
else
  bad "teos_dir() differs: '$val1' vs '$val2'"
fi
echo

# --- 6. teos_url() default ---------------------------------------------
echo "[6] teos_url() default (no env, no constant) returns ''"
val=$(extract "$(env -u TEOSURL php -r "
  require_once('$UTIL');
  \$__v = \bbsengine6\util\teos_url();
  echo (\$__v === '' ? '<<<EMPTY>>>' : '<<<' . \$__v . '>>>');
" 2>/dev/null)")
if [ "$val" = "__EMPTY__" ]; then
  ok "teos_url() returns empty string (matches bare \TEOSURL behavior)"
else
  bad "teos_url() returned '$val', expected empty string"
fi
echo

# --- 7. teos_url() env override ----------------------------------------
echo "[7] teos_url() honors TEOSURL env override"
val=$(TEOSURL=/handbook/6/ php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\teos_url();
" 2>/dev/null)
expected="/handbook/6/"
if [ "$val" = "$expected" ]; then
  ok "TEOSURL env -> teos_url() returns '$val'"
else
  bad "TEOSURL env -> teos_url() returned '$val', expected '$expected'"
fi
echo

# --- 8. teos_url() constant override -----------------------------------
echo "[8] teos_url() honors TEOSURL constant when env is empty"
val=$(env -u TEOSURL php -r "
  require_once('$UTIL');
  define('TEOSURL', '/const/url/');
  echo \bbsengine6\util\teos_url();
" 2>/dev/null)
expected="/const/url/"
if [ "$val" = "$expected" ]; then
  ok "TEOSURL constant -> teos_url() returns '$val'"
else
  bad "TEOSURL constant -> teos_url() returned '$val', expected '$expected'"
fi
echo

# --- 9. env wins over constant -----------------------------------------
echo "[9] env wins over constant (production pattern)"
# This is what router.php relies on: it putenv()s TEOSDIR/TEOSURL
# based on the request's URI prefix, and that env value must
# shadow the constant the same file defines (see engine/router.php:591-592).
val=$(TEOSDIR=/from/env php -r "
  require_once('$UTIL');
  define('TEOSDIR', '/from/constant');
  echo \bbsengine6\util\teos_dir();
" 2>/dev/null)
expected="/from/env/"
if [ "$val" = "$expected" ]; then
  ok "env beats constant: teos_dir() returned '$val'"
else
  bad "env should beat constant: teos_dir() returned '$val', expected '$expected'"
fi
val=$(TEOSURL=/from/env/ php -r "
  require_once('$UTIL');
  define('TEOSURL', '/from/constant/');
  echo \bbsengine6\util\teos_url();
" 2>/dev/null)
expected="/from/env/"
if [ "$val" = "$expected" ]; then
  ok "env beats constant: teos_url() returned '$val'"
else
  bad "env should beat constant: teos_url() returned '$val', expected '$expected'"
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
echo "all checks passed; bbsengine6\\util\\teos_dir() and teos_url() behave correctly."
exit 0
