#!/usr/bin/env bash
# test_handbook_6_returns_200.sh
# Verifies that https://www.bbsengine.org/handbook/6/ returns 200
# with a rendered handbook body. Exits 0 on success, non-zero on
# failure. All checks operate against the public endpoint and
# the build-host filesystem (no ssh to merlin required).
#
# @since 2026-09-07
#
# What the test does NOT do (and why):
#
#   - It does not ssh to merlin. The build host is a separate
#     machine; merlin's prod tree is not bind-mounted here. Any
#     "is the file on merlin?" check would have to be a guess
#     based on the build-host's stale view of /srv/www/bbsengine6.
#     The HTTP probe is the only ground-truth signal of merlin's
#     state, and the test leans on it.
#
#   - It does not check the build-host's /srv/www/bbsengine6/engine/
#     or /srv/www/vhosts/www.bbsengine.org/html/engine/ for
#     existence. Those are the local-stage paths, not the prod
#     paths the engine/Makefile ssh-pushes to. Their presence
#     here does not imply presence on merlin, and their absence
#     here does not imply absence on merlin.
#
# What the test DOES check:
#
#   [1]  HTTP probe of https://www.bbsengine.org/handbook/6/
#   [2]  body looks like a rendered handbook page (not a 404
#        fallback, not a router-error 500)
#   [3]  additional probes (chapter, directory, raw .md) all
#        return 200 (verifies the router's per-mode dispatch
#        works, not just the index path)
#   [3b] legacy Flask / gunicorn / mod_wsgi artifact paths
#        return 404 (verifies the remove-legacy-handbook
#        cleanup ran and was not reverted)
#   [4]  build-host source invariants that catch a regression
#        in the local working tree (handbook.php is absent,
#        htaccess-prod has the new /handbook/<v>/ routing rules,
#        no /engine/ entry in bootstrap.php, .htaccess in
#        ENGINE_PHP, rsync --exclude patterns for engine/ and
#        the four legacy handbook files)
#
# Each check's "bad" message points at the specific failure
# mode and the operator action that resolves it.

set -u

URL_BASE="https://www.bbsengine.org/handbook/6"
LOCAL_BBSENGINE6="/home/opencode/data/work/bbsengine6"

pass=0
fail=0
diagnosis=""

ok()  { echo "  ok   $*"; pass=$((pass+1)); }
bad() { echo "  FAIL $*"; fail=$((fail+1)); diagnosis="$diagnosis\n  - $*"; }

probe() {
  # $1 = URL, $2 = output file
  curl -sS -o "$2" -w '%{http_code}' "$1" 2>/dev/null || echo "000"
}

# --- 1. HTTP probe of the canonical URL ---------------------------------
http_code=$(probe "$URL_BASE/" /tmp/handbook6.body)
body_bytes=$(wc -c < /tmp/handbook6.body 2>/dev/null | tr -d ' ' || echo 0)
echo "[1] HTTP probe of $URL_BASE/"
echo "    status: $http_code"
echo "    body:   $body_bytes bytes"
if [ "$http_code" = "200" ] && [ "$body_bytes" -gt 0 ]; then
  ok "HTTP 200 with non-empty body"
else
  bad "expected HTTP 200 with non-empty body, got $http_code ($body_bytes bytes) -- first line of body: $(head -1 /tmp/handbook6.body 2>/dev/null | head -c 200)"
fi
echo

# --- 2. body sanity: rendered handbook, not error fallback --------------
echo "[2] body content check"
if [ "$body_bytes" -gt 0 ] && grep -q -i -E 'bbsengine6|handbook' /tmp/handbook6.body 2>/dev/null; then
  if grep -q -i -E 'page not found|router error' /tmp/handbook6.body 2>/dev/null; then
    bad "body contains 'page not found' or 'router error' -- the router's error handler ran, the page did not render. Body: $(head -1 /tmp/handbook6.body 2>/dev/null | head -c 200)"
  else
    ok "body mentions 'bbsengine6' or 'handbook' and does not look like a router error"
  fi
else
  bad "body does not look like a rendered handbook page (no bbsengine6/handbook keyword). Body: $(head -1 /tmp/handbook6.body 2>/dev/null | head -c 200)"
fi
echo

# --- 3. additional probes verify per-mode dispatch ----------------------
echo "[3] additional probes (new handbook content)"
extra_probes=(
  "$URL_BASE/index.md|200 (raw .md via engine/serve-md.php)"
  "$URL_BASE/specs/|200 (subdirectory listing)"
  "$URL_BASE/specs/architecture.md|200 (subdirectory chapter)"
)
for entry in "${extra_probes[@]}"; do
  url="${entry%%|*}"
  desc="${entry#*|}"
  code=$(probe "$url" /tmp/handbook6.extra)
  echo "    $url -> $code ($desc)"
  case "$code" in
    200) ok "extra probe $url returned 200" ;;
    404) bad "extra probe $url returned 404 -- a per-mode handler fell through to handleError. Body: $(head -1 /tmp/handbook6.extra 2>/dev/null | head -c 200)" ;;
    500) bad "extra probe $url returned 500 -- a handler threw (e.g. template not found, fatal). Body: $(head -1 /tmp/handbook6.extra 2>/dev/null | head -c 200)" ;;
    *)   bad "extra probe $url returned unexpected $code" ;;
  esac
done
echo

# --- 3b. legacy Flask / gunicorn / mod_wsgi artifacts must be gone -----
# These paths served dead weight from the retired Flask stack. The
# current request-time PHP handbook (engine/router.php +
# engine/serve-md.php, both shipped via engine-deploy-prod)
# does not reference any of them. `make -C www remove-legacy-handbook`
# ssh-deletes them on merlin; the test verifies they are gone.
echo "[3b] legacy handbook artifacts (should be 404 after remove-legacy-handbook)"
legacy_paths=(
  "https://www.bbsengine.org/handbook/bbsengine-handbook.conf"
  "https://www.bbsengine.org/handbook/handbook-wsgi.conf"
  "https://www.bbsengine.org/handbook/modules.adoc"
  "https://www.bbsengine.org/handbook/modules.html"
)
for path in "${legacy_paths[@]}"; do
  code=$(probe "$path" /tmp/handbook6.legacy)
  echo "    $path -> $code"
  case "$code" in
    404) ok "legacy path $path returned 404 (removed)" ;;
    200) bad "legacy path $path still returns 200 -- \`make -C www remove-legacy-handbook\` has not been run, or the cleanup was reverted by a subsequent \`make wwworg\` from the build host's read-only local stage" ;;
    301|302) bad "legacy path $path returned $code (redirect) -- cleanup did not remove the file" ;;
    *)   bad "legacy path $path returned unexpected $code" ;;
  esac
done
echo

# --- 4. build-host source invariants ------------------------------------
echo "[4] build-host source invariants"

if [ ! -f "$LOCAL_BBSENGINE6/www/org/php/handbook.php" ]; then
  ok "local www/org/php/handbook.php is absent (eradicated; /router.php + /serve-md.php are the .org handbook handlers)"
else
  bad "local www/org/php/handbook.php exists -- the handler is supposed to be eradicated; /router.php + /serve-md.php are the .org handbook handlers"
fi

if [ -f "$LOCAL_BBSENGINE6/php/bootstrap.php" ]; then
  if grep -q 'dirname(__DIR__) *\. *"/engine/"' "$LOCAL_BBSENGINE6/php/bootstrap.php" 2>/dev/null \
     || grep -q '"/engine/"' "$LOCAL_BBSENGINE6/php/bootstrap.php" 2>/dev/null; then
    bad "local php/bootstrap.php \$defaults still includes a /engine/ entry -- that path is never populated; remove it"
  else
    ok "local php/bootstrap.php \$defaults no longer includes a misleading /engine/ entry"
  fi
else
  bad "local php/bootstrap.php missing"
fi

# @since 2026-09-09 — single canonical install. The .org
# vhost's engine entry points are symlinks at the docroot
# root (no /engine/ URL prefix); the symlinks are created
# by www/org/Makefile stage and point at
# /srv/www/bbsengine6/ on merlin. The install itself is
# shipped by engine/Makefile deploy-engine. Verify the
# symlink-creation lines are present in the per-vhost
# Makefile; this is the new invariant replacing the
# previous engine/Makefile ENGINE_PHP check.
if [ -f "$LOCAL_BBSENGINE6/www/org/Makefile" ]; then
  symlinks_ok=true
  for entry in \
    'ln -sfn */srv/www/bbsengine6/router\.php' \
    'ln -sfn */srv/www/bbsengine6/serve-md\.php' \
    'ln -sfn */srv/www/bbsengine6/join\.php' \
    'ln -sfn */srv/www/bbsengine6/login\.php' \
    'ln -sfn */srv/www/bbsengine6/logout\.php'; do
    if ! grep -qE "$entry" "$LOCAL_BBSENGINE6/www/org/Makefile" 2>/dev/null; then
      symlinks_ok=false
      bad "local www/org/Makefile stage is missing symlink-creation line: $entry"
    fi
  done
  if $symlinks_ok; then
    ok "local www/org/Makefile stage creates the five symlinks (router.php, serve-md.php, join.php, login.php, logout.php) -> /srv/www/bbsengine6/"
  fi
else
  bad "local www/org/Makefile missing"
fi

if [ -f "$LOCAL_BBSENGINE6/engine/Makefile" ]; then
  if grep -q 'ENGINE_PHP *= *\.htaccess' "$LOCAL_BBSENGINE6/engine/Makefile" 2>/dev/null; then
    ok "local engine/Makefile ENGINE_PHP includes .htaccess"
  else
    bad "local engine/Makefile ENGINE_PHP does NOT include .htaccess -- fix(engine/Makefile) commit not in working tree"
  fi
  # @since 2026-09-09 — single canonical install. The engine
  # Makefile now ships the install to ENGINEHOST:INSTALL_DIR
  # in addition to the .com docroot copy. The .org docroot
  # is no longer a target of engine/Makefile.
  if grep -q 'INSTALL_DIR' "$LOCAL_BBSENGINE6/engine/Makefile" 2>/dev/null; then
    ok "local engine/Makefile ships canonical install to INSTALL_DIR (single-install model)"
  else
    bad "local engine/Makefile missing INSTALL_DIR rsync target -- single-install refactor not in working tree"
  fi
  if grep -qE '^[A-Z_]*=.*WWWENGINEPRODDOCROOT|^[A-Z_]*=.*WWWENGINESTAGEDOCROOT' "$LOCAL_BBSENGINE6/engine/Makefile" 2>/dev/null; then
    bad "local engine/Makefile still defines WWWENGINEPRODDOCROOT / WWWENGINESTAGEDOCROOT -- these were dropped in the single-install refactor"
  else
    ok "local engine/Makefile no longer defines the .org docroot rsync vars (single-install refactor applied)"
  fi
else
  bad "local engine/Makefile missing"
fi

if [ -f "$LOCAL_BBSENGINE6/www/org/htaccess-prod" ]; then
  # @since 2026-09-07 — handbook.php eradicated; the .org
  # htaccess must route /handbook/<v>/<chapter> and
  # /handbook/<v>/<dir> through /router.php, and
  # /handbook/<v>/<uri>.md through /serve-md.php.
  # A catch-all .md rule that matches anywhere on the vhost
  # is too greedy; the handbook-specific .md rule must be
  # present and prefixed. Use grep -F (fixed string) for the
  # rewrite target substrings; the prior test used BRE-escaped
  # parens that didn't actually match the ERE pattern in
  # htaccess-prod, so the regex check was broken even when the
  # rule was present and correct.
  handbook_md_ok=false
  if grep -E '^[[:space:]]*RewriteRule[[:space:]]+\^handbook/' "$LOCAL_BBSENGINE6/www/org/htaccess-prod" 2>/dev/null | grep -qF '/serve-md.php'; then
    handbook_md_ok=true
  fi
  if $handbook_md_ok; then
    ok "local htaccess-prod routes /handbook/<v>/<uri>.md to /serve-md.php (no /engine/ prefix)"
  else
    bad "local htaccess-prod does NOT route /handbook/<v>/<uri>.md to /serve-md.php -- fix(www/htaccess-prod) routing rule missing or uses /engine/ prefix"
  fi
  # @since 2026-09-09 — chapter + directory routes target
  # /router.php, not /engine/router.php. Use grep -F
  # (fixed string) for the rewrite target; the prior test's
  # BRE-escaped regex was broken (see .md check above).
  handbook_chapter_ok=false
  if grep -E '^[[:space:]]*RewriteRule[[:space:]]+\^handbook/' "$LOCAL_BBSENGINE6/www/org/htaccess-prod" 2>/dev/null | grep -qF '/router.php?uri='; then
    handbook_chapter_ok=true
  fi
  if $handbook_chapter_ok; then
    ok "local htaccess-prod routes /handbook/<v>/<chapter> to /router.php (no /engine/ prefix)"
  else
    bad "local htaccess-prod does NOT route /handbook/<v>/<chapter> to /router.php -- chapter rule missing or uses /engine/ prefix"
  fi
  # @since 2026-09-09 — no /engine/ prefix in any rewrite
  # rule's target. The single-install refactor moved the
  # entry points to the docroot root, so rewrite targets
  # are /router.php, /serve-md.php, /join.php, /login.php,
  # /logout.php. Lines that mention /engine/ in COMMENTS
  # (e.g. "@since 2026-09-09 — flattened from
  # /engine/router.php") are still allowed; this check
  # inspects the active rewrite rules only.
  active_rewrite_engine_refs=$(grep -E '^[[:space:]]*Rewrite(Rule|Cond)' "$LOCAL_BBSENGINE6/www/org/htaccess-prod" 2>/dev/null | grep -c '/engine/' || true)
  if [ "$active_rewrite_engine_refs" -eq 0 ]; then
    ok "local htaccess-prod has no /engine/ references in active RewriteRule/RewriteCond lines"
  else
    bad "local htaccess-prod has $active_rewrite_engine_refs active RewriteRule/RewriteCond line(s) referencing /engine/ -- all rewrite targets should be flattened"
  fi
else
  bad "local www/org/htaccess-prod missing"
fi

if [ -f "$LOCAL_BBSENGINE6/www/Makefile" ]; then
  # @since 2026-09-09 — single-install refactor dropped the
  # --exclude engine/ and --exclude html/engine/ lines from
  # the org rsync. The .org docroot no longer has an
  # html/engine/ subdir; engine entry points are symlinks
  # at the docroot root, created by www/org/Makefile stage
  # and carried by $(RSYNC)'s --archive/-l. The excludes
  # would now be actively harmful (rsync --delete-after
  # would strip the symlinks). Verify they are absent.
  if grep -qE 'exclude *"engine/"' "$LOCAL_BBSENGINE6/www/Makefile" 2>/dev/null \
     || grep -qE 'exclude *"html/engine/"' "$LOCAL_BBSENGINE6/www/Makefile" 2>/dev/null; then
    bad "local www/Makefile org rsync still has --exclude engine/ or --exclude html/engine/ -- these were dropped in the single-install refactor and would strip the docroot symlinks on --delete-after"
  else
    ok "local www/Makefile org rsync no longer excludes engine/ or html/engine/ (single-install refactor applied)"
  fi
  # --exclude html/handbook/{*.conf,modules.*}: prevent the read-only
  # build-host local stage from re-pushing the four legacy Flask
  # artifacts after `make -C www remove-legacy-handbook` cleans them
  # on merlin.
  legacy_excludes_ok=true
  for pattern in \
    'exclude *"html/handbook/bbsengine-handbook\.conf"' \
    'exclude *"html/handbook/handbook-wsgi\.conf"' \
    'exclude *"html/handbook/modules\.adoc"' \
    'exclude *"html/handbook/modules\.html"'; do
    if ! grep -qE "$pattern" "$LOCAL_BBSENGINE6/www/Makefile" 2>/dev/null; then
      legacy_excludes_ok=false
      bad "local www/Makefile org rsync is missing $pattern -- remove-legacy-handbook cleanup will be reverted on the next make wwworg run"
    fi
  done
  if $legacy_excludes_ok; then
    ok "local www/Makefile org rsync excludes the four legacy handbook artifacts (bbsengine-handbook.conf, handbook-wsgi.conf, modules.adoc, modules.html)"
  fi
else
  bad "local www/Makefile missing"
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
  echo "  if the HTTP probe is 200 but body checks fail:"
  echo "    -- the router's leading-slash URI handling in"
  echo "       engine/router.php (handleFolder, handleMarkdown) does"
  echo "       not strip the leading '/' before calling"
  echo "       bbsengine6\\\\util\\\\safe_path_web, which rejects"
  echo "       leading-slash components. Fix in router.php to ltrim()"
  echo "       the URI before passing it to safe_path_web."
  echo
  echo "  if the HTTP probe is 500 with 'Failed opening required':"
  echo "    -- engine/ tree did not land on merlin. Run:"
  echo "       make engine-deploy-prod"
  echo "       sudo systemctl reload php-fpm   # on merlin"
  echo
  echo "  if the HTTP probe is 500 with 'Unable to load template':"
  echo "    -- the skin/ template (e.g. browse.tmpl) is missing on"
  echo "       merlin. Run: make skin-prod"
  echo
  echo "  if a legacy handbook artifact check (3b) returns 200:"
  echo "    -- \`make -C www remove-legacy-handbook\` removes the"
  echo "       four files (bbsengine-handbook.conf, handbook-wsgi.conf,"
  echo "       modules.adoc, modules.html) on merlin via ssh. Run"
  echo "       that target. Note: the build host's local stage at"
  echo "       /srv/www/vhosts/www.bbsengine.org/html/handbook/ is"
  echo "       read-only and still has the files; a subsequent"
  echo "       \`make wwworg\` from the read-only mount will re-push"
  echo "       them unless the build host's stage is also cleaned"
  echo "       (out of scope for the Makefile -- requires sudo /"
  echo "       remount on the build host)."
  echo
  echo "  if a filesystem check (3-5b in the old version) failed"
  echo "    despite the HTTP probe being 200:"
  echo "    -- the test was reading the build host's stale local-stage"
  echo "       view, not merlin's prod tree. The build host and merlin"
  echo "       are different machines; only the HTTP probe is ground truth."
  echo
  echo "to re-run: $0"
  exit 1
fi
echo
echo "all checks passed; handbook/6/ returns 200 with a rendered body."
exit 0
