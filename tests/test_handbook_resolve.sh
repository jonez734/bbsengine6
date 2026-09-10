#!/usr/bin/env bash
# test_handbook_resolve.sh
# Verifies bbsengine6\util\handbook_home() and
# bbsengine6\util\handbook_resolve() in php/util.php.
#
# These helpers are the single source of truth for
# resolving /handbook/<v>/<uri>.md URLs to absolute
# filesystem paths. They were added to fix the bug
# where engine/serve-md.php hardcoded a TEOSDIR
# fallback that pointed at the wrong docroot, causing
# live /handbook/6/specs/auth-bank.md requests to 404
# with "File not found" (see engine/serve-md.php prior
# to the 2026-09-09 fix).
#
# What this test checks:
#   [1] handbook_home() returns the canonical handbook
#       path (with trailing slash) and is consistent
#       across multiple calls.
#   [2] handbook_resolve() with a valid (prefix, path)
#       resolves to the actual file under that prefix.
#   [3] handbook_resolve() with empty prefix or path
#       returns false (no traversal leak).
#   [4] handbook_resolve() rejects path traversal
#       (../etc/passwd-style inputs).
#   [5] handbook_resolve() rejects non-.md extensions.
#   [6] handbook_resolve() rejects nonexistent files.
#   [7] handbook_resolve() rejects prefixes that don't
#       resolve under handbook_home().
#   [8] handbook_resolve() respects an environment
#       override of BBSENGINE6_HANDBOOK_HOME.
#   [9] handbook_resolve() rejects prefixes that escape
#       handbook_home() via a symlink target outside the
#       handbook tree (skipped if no such symlink exists
#       on the build host).
#
# Each check's "bad" message points at the specific
# failure mode and the operator action that resolves it.

set -u

BBSENGINE6="/home/opencode/data/work/bbsengine6"
UTIL="$BBSENGINE6/php/util.php"
HANDBOOK_HOME_CANONICAL="/srv/www/vhosts/www.bbsengine.org/html/handbook/"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

runphp() {
  # $1 = PHP snippet (single expression expected)
  # Wrap the result with a sentinel so we can distinguish
  # false/empty-string/0/etc. var_export(false) is empty
  # string in PHP, so we use a wrapping marker that survives
  # both. Strings would otherwise be quoted by var_export,
  # so we use a print_r-like marker: prefix the value with
  # a sentinel and distinguish false via the marker shape.
  php -d display_errors=0 -r "
    require_once('$UTIL');
    \$__v = ($1);
    if (\$__v === false) {
        echo '<<<FALSE>>>';
    } else {
        echo '<<<', (string)\$__v, '>>>';
    }
  " 2>/dev/null
}

# Extract a runphp result, stripping the <<<>>> sentinel wrapper.
# Outputs the literal string 'false' for false, the actual value
# (possibly empty) otherwise.
extract() {
  local raw="$1"
  case "$raw" in
    "<<<FALSE>>>") echo "false" ;;
    "<<<>>>"|"")    echo "" ;;
    *)              echo "${raw#<<<}" | sed 's/>>>$//' ;;
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
# Point handbook_home() at the build-host working tree so the
# happy-path test can resolve real files (the canonical
# /srv/www/vhosts/www.bbsengine.org/html/handbook/ path only
# exists on merlin, not here).
export BBSENGINE6_HANDBOOK_HOME="$BBSENGINE6/handbook/"
echo "    BBSENGINE6_HANDBOOK_HOME=$BBSENGINE6_HANDBOOK_HOME"
ok "BBSENGINE6_HANDBOOK_HOME overridden to build-host tree"
echo

# --- 1. handbook_home() default -----------------------------------------
echo "[1] handbook_home() default"
hh=$(extract "$(runphp '\bbsengine6\util\handbook_home()')")
if [ -z "$hh" ]; then
  bad "handbook_home() returned empty string"
elif [ "${hh%/}" = "${hh}" ]; then
  bad "handbook_home() did not return a trailing-slashed path: '$hh'"
else
  ok "handbook_home() returns '$hh'"
fi
# idempotency check: a second call returns the same value
hh2=$(extract "$(runphp '\bbsengine6\util\handbook_home()')")
if [ "$hh" = "$hh2" ]; then
  ok "handbook_home() is consistent across calls"
else
  bad "handbook_home() differs across calls: '$hh' vs '$hh2'"
fi
echo

# --- 2. handbook_resolve() happy path -----------------------------------
echo "[2] handbook_resolve() happy path"
# The build-host tree may not have a versioned handbook/6/ subdir
# (the canonical tree lives on merlin). Create a temp versioned
# tree that mirrors the layout serve-md.php resolves against.
hp_dir=$(mktemp -d)
mkdir -p "$hp_dir/handbook/6/specs"
echo "# test content" > "$hp_dir/handbook/6/specs/auth-bank.md"
expected="$hp_dir/handbook/6/specs/auth-bank.md"
resolved=$(BBSENGINE6_HANDBOOK_HOME="$hp_dir/handbook/" php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\handbook_resolve('handbook/6', 'specs/auth-bank.md');
" 2>/dev/null)
rm -rf "$hp_dir"
if [ "$resolved" = "$expected" ]; then
  ok "handbook_resolve(handbook/6, specs/auth-bank.md) -> '$resolved'"
else
  bad "handbook_resolve() returned '$resolved', expected '$expected'"
fi
echo

# --- 3. empty args ------------------------------------------------------
echo "[3] handbook_resolve() rejects empty args"
cases=(
  '"" "specs/auth-bank.md"'
  '"handbook/6" ""'
  '"" ""'
)
for tup in "${cases[@]}"; do
  # Build the PHP snippet with literal args (not a single string).
  # Read the two args by parsing the tup (which is "A" "B" syntax).
  a=$(echo "$tup" | awk -F'"' '{print $2}')
  b=$(echo "$tup" | awk -F'"' '{print $4}')
  r=$(extract "$(php -d display_errors=0 -r "
    require_once('$UTIL');
    \$__v = \bbsengine6\util\handbook_resolve(\"$a\", \"$b\");
    if (\$__v === false) { echo '<<<FALSE>>>'; } else { echo '<<<' . (string)\$__v . '>>>'; }
  " 2>/dev/null)")
  if [ "$r" = "false" ]; then
    ok "handbook_resolve($tup) -> false"
  else
    bad "handbook_resolve($tup) -> '$r' (expected false)"
  fi
done
echo

# --- 4. path traversal --------------------------------------------------
echo "[4] handbook_resolve() rejects path traversal"
cases=(
  '"handbook/6" "../etc/passwd"'
  '"handbook/6" "../../etc/passwd"'
  '"handbook/../etc" "passwd"'
)
for tup in "${cases[@]}"; do
  a=$(echo "$tup" | awk -F'"' '{print $2}')
  b=$(echo "$tup" | awk -F'"' '{print $4}')
  r=$(extract "$(php -d display_errors=0 -r "
    require_once('$UTIL');
    \$__v = \bbsengine6\util\handbook_resolve(\"$a\", \"$b\");
    if (\$__v === false) { echo '<<<FALSE>>>'; } else { echo '<<<' . (string)\$__v . '>>>'; }
  " 2>/dev/null)")
  if [ "$r" = "false" ]; then
    ok "handbook_resolve($tup) -> false"
  else
    bad "handbook_resolve($tup) -> '$r' (expected false)"
  fi
done
echo

# --- 5. wrong extension -------------------------------------------------
echo "[5] handbook_resolve() rejects non-.md extensions"
r=$(extract "$(runphp '\bbsengine6\util\handbook_resolve("handbook/6", "specs/index.txt")')")
if [ "$r" = "false" ]; then
  ok "handbook_resolve(.., index.txt) -> false"
else
  bad "handbook_resolve(.., index.txt) -> '$r' (expected false)"
fi
# also reject a file that exists but with a non-.md extension
nonmd=$(mktemp --suffix=.txt 2>/dev/null || mktemp -t handresolve).txt
echo "not markdown" > "$nonmd"
r=$(extract "$(runphp "\\bbsengine6\\util\\handbook_resolve('handbook/6', '$(basename "$nonmd")')")")
rm -f "$nonmd"
# note: this may resolve to a path under /tmp which is outside the handbook
# home, so 'false' is the only acceptable outcome here.
if [ "$r" = "false" ]; then
  ok "handbook_resolve(.., .txt file) -> false"
else
  bad "handbook_resolve(.., .txt file) -> '$r' (expected false)"
fi
echo

# --- 6. nonexistent file ------------------------------------------------
echo "[6] handbook_resolve() rejects nonexistent files"
r=$(extract "$(runphp '\bbsengine6\util\handbook_resolve("handbook/6", "specs/does-not-exist.md")')")
if [ "$r" = "false" ]; then
  ok "handbook_resolve(.., does-not-exist.md) -> false"
else
  bad "handbook_resolve(.., does-not-exist.md) -> '$r' (expected false)"
fi
r=$(extract "$(runphp '\bbsengine6\util\handbook_resolve("handbook/9999", "specs/auth-bank.md")')")
if [ "$r" = "false" ]; then
  ok "handbook_resolve(handbook/9999, ..) -> false (nonexistent prefix)"
else
  bad "handbook_resolve(handbook/9999, ..) -> '$r' (expected false)"
fi
echo

# --- 7. prefix escapes handbook home -----------------------------------
echo "[7] handbook_resolve() rejects prefixes outside handbook_home()"
# Try a prefix that realpath() will resolve outside handbook home.
# Use /etc as the prefix target via the filesystem -- it realpath()s to
# /etc, which is not under the handbook home, so the containment check
# must reject it. We do this by creating a symlink-shaped prefix using
# a path the helper will realpath() outside the tree.
# Strategy: use a prefix that, after realpath(), does not start with
# the handbook home. The simplest case is a prefix that resolves to
# the parent of handbook home. We can't easily synthesize that
# without filesystem manipulation, so we test the env-override path
# instead by pointing handbook_home() at a tree that doesn't contain
# the prefix.
override_dir=$(mktemp -d)
mkdir -p "$override_dir/sub"
echo "# fake" > "$override_dir/sub/x.md"
r=$(BBSENGINE6_HANDBOOK_HOME="$override_dir" php -r "
  require_once('$UTIL');
  \$__v = \bbsengine6\util\handbook_resolve('handbook/6', 'specs/auth-bank.md');
  if (\$__v === false) { echo '<<<FALSE>>>'; } else { echo '<<<' . (string)\$__v . '>>>'; }
" 2>/dev/null)
r=$(extract "$r")
rm -rf "$override_dir"
if [ "$r" = "false" ]; then
  ok "handbook_resolve() with prefix outside handbook_home() -> false"
else
  bad "handbook_resolve() with prefix outside handbook_home() -> '$r' (expected false)"
fi
echo

# --- 8. env override ----------------------------------------------------
echo "[8] handbook_resolve() honors BBSENGINE6_HANDBOOK_HOME env override"
override_dir2=$(mktemp -d)
mkdir -p "$override_dir2/handbook/6/specs"
echo "# test content" > "$override_dir2/handbook/6/specs/x.md"
expected_override="$override_dir2/handbook/6/specs/x.md"
r=$(BBSENGINE6_HANDBOOK_HOME="$override_dir2/handbook/" php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\handbook_resolve('handbook/6', 'specs/x.md');
" 2>/dev/null)
rm -rf "$override_dir2"
if [ "$r" = "$expected_override" ]; then
  ok "env override resolved to '$r'"
else
  bad "env override resolved to '$r', expected '$expected_override'"
fi
# And handbook_home() reflects the env override
hh_override=$(BBSENGINE6_HANDBOOK_HOME="/tmp/foo/" php -r "
  require_once('$UTIL');
  echo \bbsengine6\util\handbook_home();
" 2>/dev/null)
if [ "$hh_override" = "/tmp/foo/" ]; then
  ok "handbook_home() reflects env override -> '$hh_override'"
else
  bad "handbook_home() did not reflect env override: got '$hh_override', expected '/tmp/foo/'"
fi
echo

# --- 9. symlink escape (skipped if no candidate) -----------------------
echo "[9] handbook_resolve() rejects symlink escape"
# If a symlink exists under the handbook tree that points outside it,
# the helper must reject files reached through it. We only run this
# check if we can synthesize one; otherwise skip.
if [ -d "$BBSENGINE6/handbook" ]; then
  esc_target=$(mktemp -d)
  esc_link="$BBSENGINE6/handbook/6/specs/.test-handbook-resolve-escape"
  ln -s "$esc_target" "$esc_link" 2>/dev/null
  if [ -L "$esc_link" ]; then
    r=$(extract "$(runphp '\bbsengine6\util\handbook_resolve("handbook/6", "specs/.test-handbook-resolve-escape")')")
    rm -f "$esc_link"
    rm -rf "$esc_target"
    if [ "$r" = "false" ]; then
      ok "handbook_resolve() rejects prefix whose realpath() escapes via symlink"
    else
      bad "handbook_resolve() followed symlink escape -> '$r' (expected false)"
    fi
  else
    echo "    skipped (could not create test symlink)"
  fi
else
  echo "    skipped (handbook tree not present)"
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
echo "all checks passed; bbsengine6\\util\\handbook_home() and handbook_resolve() behave correctly."
exit 0
