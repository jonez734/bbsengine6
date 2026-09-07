#!/usr/bin/env bash
# test_handbook_6_returns_200.sh
# Verifies that https://www.bbsengine.org/handbook/6/ returns 200.
# Exits 0 on success, non-zero on failure. Prints a diagnosis that
# pinpoints which upstream piece is missing (engine/ tree on merlin,
# bootstrap.php on merlin, .htaccess rewrite in effect, etc.) so the
# operator can fix the failing deploy step without guesswork.
#
# Run from the build host. No ssh is required -- the test only
# hits the public URL and reads /srv/www/bbsengine6/* which is
# bind-mounted on this host.
#
# @since 2026-09-07

set -u

URL="https://www.bbsengine.org/handbook/6/"
PROD_PHP_DIR="/srv/www/bbsengine6/php"
PROD_ENGINE_DIR="/srv/www/bbsengine6/engine"
ORG_DOCROOT="/srv/www/vhosts/www.bbsengine.org/html"
ORG_ENGINE_DIR="${ORG_DOCROOT}/engine"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

echo "=== test_handbook_6_returns_200.sh ==="
echo "URL: $URL"
echo

# --- 1. HTTP probe ------------------------------------------------------
http_code=$(curl -sS -o /tmp/handbook6.body -w '%{http_code}' "$URL" 2>/dev/null || echo "000")
body_bytes=$(wc -c < /tmp/handbook6.body 2>/dev/null | tr -d ' ' || echo 0)
echo "[1] HTTP probe"
echo "    status: $http_code"
echo "    body:   $body_bytes bytes"
if [ "$http_code" = "200" ] && [ "$body_bytes" -gt 0 ]; then
  ok "HTTP 200 with non-empty body"
else
  bad "expected HTTP 200 with non-empty body, got $http_code ($body_bytes bytes)"
fi
echo

# --- 2. body sanity: it should be a rendered handbook page --------------
echo "[2] body content check"
if [ "$body_bytes" -gt 0 ] && grep -q -i -E 'bbsengine6|handbook' /tmp/handbook6.body 2>/dev/null; then
  ok "body mentions 'bbsengine6' or 'handbook' (looks like a rendered page)"
else
  bad "body does not look like a rendered handbook page (no bbsengine6/handbook keyword)"
fi
echo

# --- 3. /srv/www/bbsengine6/engine/ must exist on the prod source tree ---
echo "[3] prod source tree: $PROD_ENGINE_DIR"
if [ -d "$PROD_ENGINE_DIR" ]; then
  ok "engine/ directory exists on prod source tree"
  if [ -f "$PROD_ENGINE_DIR/router.php" ]; then
    ok "engine/router.php present"
  else
    bad "engine/router.php MISSING -- make engine-deploy-prod did not take effect"
  fi
  if [ -f "$PROD_ENGINE_DIR/.htaccess" ]; then
    ok "engine/.htaccess present"
  else
    bad "engine/.htaccess MISSING -- Makefile ENGINE_PHP doesn't include it (see fix(engine/Makefile) commit)"
  fi
else
  bad "$PROD_ENGINE_DIR does not exist -- engine/Makefile deploy never landed the engine tree on merlin"
fi
echo

# --- 4. /srv/www/vhosts/www.bbsengine.org/html/engine/ must exist -------
echo "[4] prod .org docroot engine: $ORG_ENGINE_DIR"
if [ -d "$ORG_ENGINE_DIR" ]; then
  ok ".org/html/engine/ directory exists (re-seeded)"
else
  bad "$ORG_ENGINE_DIR does not exist -- engine/Makefile deploy did not recreate it (--mkpath missing or step not run)"
fi
echo

# --- 5. bootstrap.php on prod must NOT include the misleading /engine/ entry
echo "[5] prod php/bootstrap.php include_path defaults"
if [ -f "$PROD_PHP_DIR/bootstrap.php" ]; then
  if grep -q 'dirname(__DIR__) *\. *"/engine/"' "$PROD_PHP_DIR/bootstrap.php" 2>/dev/null \
     || grep -q '"/engine/"' "$PROD_PHP_DIR/bootstrap.php" 2>/dev/null; then
    bad "php/bootstrap.php \$defaults still includes a /engine/ entry -- that path is never populated and gives a false sense of correctness. The correct fix is the relative require in handbook.php, not an include_path entry. Run \`make php-deploy-prod\` after the relative-require commit lands."
  else
    ok "php/bootstrap.php \$defaults no longer includes the misleading /engine/ entry"
  fi
else
  bad "$PROD_PHP_DIR/bootstrap.php missing entirely"
fi
echo

# --- 5b. handbook.php on prod must use the relative require shape -------
echo "[5b] prod handbook.php require shape"
if [ -f "$ORG_DOCROOT/handbook.php" ]; then
  if grep -q 'require_once *("router\.php")' "$ORG_DOCROOT/handbook.php" 2>/dev/null; then
    bad "handbook.php still has bare require_once(\"router.php\") -- depends on include_path that the engine deploy never populates. The commit that switches to require_once __DIR__ . \"/engine/router.php\" is not yet on prod. Run \`make wwworg\` (or \`make deploy-handbook-prod\`) after the relative-require commit lands."
  elif grep -q 'require_once *__DIR__ *\. *"/engine/router\.php"' "$ORG_DOCROOT/handbook.php" 2>/dev/null; then
    ok "handbook.php uses require_once __DIR__ . \"/engine/router.php\" (relative require)"
  else
    bad "handbook.php require shape is unrecognized -- inspect manually"
  fi
else
  bad "$ORG_DOCROOT/handbook.php missing"
fi
echo

# --- 6. .htaccess on the .org docroot must rewrite /handbook/<v>/... to handbook.php
echo "[6] .org .htaccess rewrite rule"
if [ -f "$ORG_DOCROOT/.htaccess" ]; then
  if grep -qE 'handbook/\\\\?\\d\\+|handbook/.*\\.php' "$ORG_DOCROOT/.htaccess" 2>/dev/null \
     || grep -qE 'handbook/' "$ORG_DOCROOT/.htaccess" 2>/dev/null; then
    ok ".htaccess appears to carry a /handbook/ rewrite rule"
  else
    bad ".htaccess on $ORG_DOCROOT does not appear to carry a /handbook/ rewrite"
  fi
else
  bad "$ORG_DOCROOT/.htaccess missing"
fi
echo

# --- 7. legacy Flask artifacts under html/handbook/ should be gone -----
echo "[7] legacy Flask docroot cleanup"
if [ -d "$ORG_DOCROOT/handbook" ]; then
  if [ -f "$ORG_DOCROOT/handbook/bbsengine-handbook.conf" ] || [ -d "$ORG_DOCROOT/handbook/csrf" ]; then
    bad "$ORG_DOCROOT/handbook/ still contains legacy Flask artifacts (bbsengine-handbook.conf / csrf/ / migrations/ / handbook-wsgi.conf) -- the old docroot was not removed when the new request-time handbook.php shipped"
  else
    ok "html/handbook/ exists but no legacy Flask artifacts"
  fi
else
  ok "html/handbook/ does not exist (legacy docroot fully retired)"
fi
echo

# --- summary ------------------------------------------------------------
echo "=== summary ==="
echo "passed: $pass"
echo "failed: $fail"
if [ "$fail" -gt 0 ]; then
  echo
  echo "diagnosis (most likely causes, in order):"
  printf "%b\n" "$diagnosis"
  echo
  echo "remediation on the build host (no ssh required for the rsync"
  echo "step itself, but ENGINE_PHP ssh-pushes to merlin):"
  echo
  echo "  cd /home/opencode/data/work/bbsengine6"
  echo "  make php-deploy-prod             # push php/bootstrap.php to merlin"
  echo "  make engine-deploy-prod          # ssh-push engine/ to both prod docroots"
  echo "  # on merlin:"
  echo "  sudo systemctl reload php-fpm"
  echo
  echo "then re-run: $0"
  exit 1
fi
echo
echo "all checks passed; handbook/6/ returns 200 and the upstream"
echo "engine/ + bootstrap.php + .htaccess state is consistent."
exit 0
