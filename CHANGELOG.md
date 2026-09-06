# Changelog

All notable changes to `bbsengine6` are recorded here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### deploy bbsengine6.handbook — shared Markdown primitive

New `deploy bbsengine6.handbook` sub-target (via `deploytool`)
stages the handbook tree and ships a blurb/markdown-rendered
handler for `https://bbsengine.org/handbook/<v>/<path>` on the
org site. Replaces the legacy `\Michaelf\Markdown`-driven
`.txt`-only reader.

- New `php/markdown.php` — shared `\bbsengine6\markdown`
  namespace exporting `splitFrontmatter()`, `renderHtml()`,
  `splitHtmlSections()`, and `parseDocument()` against a single
  shared `ParsedownExtra` instance with frozen
  `setMarkupEscaped(true)` + `setSafeMode(true)`.
- `php/blurb.php::parseMarkdownSections()` now delegates to
  `\bbsengine6\markdown\parseDocument($md, split: true)` —
  signature and behavior preserved; existing
  `test_blurb_render.php` continues to pass.
- `engine/router.php::router_displayMarkdownFile()` now
  delegates to `\bbsengine6\markdown\parseDocument($md,
  split: false, breaks: true)` (preserve the teos path's
  historic `setBreaksEnabled(true)`). Removed the
  un-referenced `router_parseYamlFrontmatter()` helper.
- `engine/router.php::router_collectDirectoryItems()` now
  uses `\bbsengine6\markdown\splitFrontmatter()` for md
  title extraction instead of a private helper.
- `smarty/modifier.parsedown.php` now delegates to
  `\bbsengine6\markdown\renderHtml()`; the heading/bod
  HTML wrapper shape (consumed by templates that call
  `{$body|parsedown}`) is unchanged.
- `www/org/php/handbook.php` rewritten: requests
  `https://bbsengine.org/handbook/<v>/<path>` resolve
  directly to `.md` files under `\config\HANDBOOKDIR` and
  render via `\bbsengine6\markdown\parseDocument` instead
  of `\Michaelf\Markdown::defaultTransform` against staged
  `.txt` siblings. Path-traversal guarded with `realpath`
  prefix check; no DB blurb row required (filesystem
  fallback). Multi-segment URIs (`specs/architecture`,
  `decisions`, ...) are reachable.
- `www/org/htaccess-prod` rewrite widened from a single
  chapter segment to multi-segment: `^handbook/(\d+)/(.*)$
  → handbook.php?mode=chapter&uri=$2&version=$1`. The
  `/handbook/<v>/` and `/handbook/current/...` aliases
  are unchanged.
- `www/org/skin/tmpl/handbook-index.tmpl`: chapter glob
  switched from `*.txt` to `*.md` (now served directly by
  the rewritten handler).
- `www/org/skin/tmpl/handbook-chapter.tmpl`: removed the
  legacy `|markdown` filter from `{$data.html}` —
  `handbook.php` now feeds pre-rendered HTML
  (`ParsedownExtra` with `setSafeMode + setMarkupEscaped`)
  via `{$data.html nofilter}`.
- `Makefile`: new `handbook-prod` and `deploy-handbook`
  targets, added to `.PHONY:`. The deploy chain runs
  `$(MAKE) -C handbook stage` then `$(MAKE) -C www org`
  (which already chains `$(MAKE) -C ../handbook stage`).
  Removed the legacy `handbook-prod` (staged-v6-rsync
  via `.txt`) target; `prod:` no longer references it.
- `Makefile` follow-up: `handbook-prod` no longer chains
  into `$(MAKE) -C www org` — the merlin production push
  is owned by `deploy bbsengine6.wwworg`, whose `RSYNC`
  already covers `/srv/www/vhosts/www.bbsengine.org/html/handbook/<v>/`
  because that path lives under `WWWSTAGE`. `VERSION` is
  now declared `?= 6` (was `= 6`) and passed inline as
  `VERSION=$(VERSION)` to the handbook stage sub-make,
  fixing the empty-VERSION rsync destination
  `/srv/www/vhosts/www.bbsengine.org/html/handbook//`.
  `www/Makefile:org` and `wwworg:` similarly pass
  `VERSION=$(VERSION)` through the chain, and `www/Makefile`
  declares `VERSION ?= 6` as a defensive fallback so the
  empty-version bug cannot recur if `www org` is invoked
  directly.
- Behavior change: rendering engine for
  `https://bbsengine.org/handbook/<v>/<path>` switched
  from `\Michaelf\Markdown::defaultTransform` to
  `ParsedownExtra(safeMode+escaped)`. Output is near-
  identical for hand-written Markdown; raw-HTML in
  handbooks is now escaped (a hardening, not a
  regression).

### handbook stage: drop .md exclude; retire gunicorn/Flask stack

`bbsengine6/handbook/Makefile stage` had `--exclude '*.md'`
left over from the legacy deploy-time `.txt` conversion
chain (the `\Michaelf\Markdown`-driven reader that
`handbook.php` superseded). With the exclude in place,
`deploy bbsengine6.handbook` and `deploy bbsengine6.wwworg`
(both chain into this target via `bbsengine6/Makefile:271`
and `bbsengine6/www/Makefile:18` respectively) silently
staged an empty handbook tree. The new request-time
handler (`www/org/php/handbook.php`, rendering through the
shared `\bbsengine6\markdown\parseDocument`, identical to
teos's `teospath` path) reads `.md` files directly from
`HANDBOOKDIR/<v>/`, so the `.md` tree must reach the
docroot.

- `bbsengine6/handbook/Makefile stage`: drop
  `--exclude '*.md'`. Drop `--exclude '*.py'` (the
  Python files are retired in this commit). Keep
  `*.pyc`, `__pycache__`, `.sass-cache`, `Makefile`,
  `.*` as hygiene excludes.
- Delete the now-dead `stage-convert` target (legacy
  `.txt` pre-conversion via `python3 -c "import
  markdown; ..."`).
- `bbsengine6/Makefile`: bare `handbook:` target now
  invokes `$(MAKE) -C handbook stage VERSION=$(VERSION)`
  (the corrected stage) instead of the deleted
  `stage-convert`. `handbook-prod` (deploytool's
  `deploy bbsengine6.handbook` entry point) and
  `deploy-handbook` are unchanged.
- Delete dead gunicorn / mod_wsgi / Flask artifacts
  from `bbsengine6/handbook/`: `app.py`, `wsgi.py`,
  `handbook-gunicorn.conf`, `handbook-gunicorn.service`,
  `handbook-wsgi.conf`, `bbsengine-handbook.conf`,
  `DEPLOYMENT.md`, `HANDBOOK_SERVING.md`,
  `convert_markdown.py`, `csrf/`, `migrations/`. The new
  architecture renders at request time via PHP; no Python
  app server is needed. The `handbook-gunicorn.*` files
  already self-flagged as "alternative deployment path,
  NOT the production setup" — the new architecture retires
  both the primary (mod_wsgi) and the alternative
  (gunicorn) paths.
- Replace `handbook/modules.adoc` (0 bytes, empty) with
  a stub `handbook/modules.md` that preserves the
  `/handbook/6/modules` URI shape. Delete the empty
  Asciidoctor default-template snapshots
  `handbook/modules.html`, `handbook/bbsengine.html`,
  `handbook/bbsengine-modules.html` (all `<title>Untitled
  </title>` boilerplate, no real chapter content).
- Doc cleanup for the new architecture:
  `handbook/Makefile` — drop the `convert` and `watch`
  targets (both called `convert_markdown.py`, which is gone)
  and the `install-deps` target (its Python deps were for the
  Flask app + `convert_markdown.py`); update `help`.
  `handbook/WEBSOCKET_REALTIME_PLAN.md` — the WebSocket plan
  was for an unimplemented migration that *replaced* the
  just-retired Flask/WSGI stack with a WebSocket-native
  server; the actual shipped architecture (request-time PHP
  rendering via `handbook.php` + the shared
  `\bbsengine6\markdown\parseDocument` primitive) is simpler
  than either, so the plan is obsolete and the document is
  deleted.
  `handbook/QUICKSTART.md`, `handbook/index.md`, `README.md`,
  `SPEC.md` — drop links to deleted `DEPLOYMENT.md` and
  `HANDBOOK_SERVING.md`, drop the `libapache2-mod-wsgi-py3`
  / `libapache2-mod-proxy-uwsgi` apt-get line, drop
  references to the `handbook-wsgi.conf` vhost, drop the
  `csrf/` link and tree entry from the doc structure, and
  remove the runtime-conversion (`python3 app.py`) and
  pre-built static (`make convert`) snippets from the dev
  section. The "Flask" references in
  `handbook/specs/decisions.md` are historical alternatives
  that were rejected during architecture selection; they
  stay.

### bbsengine6.message: extract `dal/` subpackage, split service from lib

Refactor `bbsengine6.message.lib` (1850 lines) into a layered
structure that mirrors casino's `dal/` / `services/` contract.

- New `bbsengine6/message/dal/` package with one module per
  `engine.__message*` table family (`messages`, `recipients`,
  `groups`, `blocking`, `ratelimit`, `types`) and a `_pool.py`
  CONN_POOL_PATTERN helper. DAL has no policy: no rate-limit
  checks, no enable/disable gate, no recipient expansion, no
  business branching.
- New `bbsengine6/message/service.py` owns business orchestration:
  rate-limit gating, blocking filter, recipient expansion, legacy
  `send()` shim, enable/disable. Calls into DAL.
- New `bbsengine6/message/templates.py` -- pure `{var}` / `$var`
  rendering helpers (`render_template`, `render_message_content`,
  `parse_variables_from_content`, `get_builtin_variables`,
  `validate_template`). No I/O.
- New `bbsengine6/message/cache.py` (at package root, not under
  `dal/`) -- in-memory local unread counter. No DB.
- `bbsengine6/message/lib.py` slimmed to a facade: the `Message`
  dataclass, DB helpers (`_make_args`, `_resolve_db`,
  `_db_from_args`, `_coerce_urgency`), and `__getattr__`
  re-exports so the public surface is preserved.
- `bbsengine6/message/__init__.py` `access()`, `init()`, `cli`
  unchanged.
- No public-API breakage: every name in `bbsengine6.message.<X>`
  resolves to the same callable. Existing test patches against
  `bbsengine6.message.lib.<name>` continue to work because `lib.py`
  re-exports the moved names via `__getattr__`.
- `bbsengine6/SPEC.md` gains a "Layered package layout" section
  mirroring `casino/SPEC.md` §3.

See `TODO-message-migration.md` "Phase 11 -- DAL extraction"
for the change list and verification.

### build: `deploy-tui` hard-fails when the active venv has an editable install

`py/src/Makefile deploy-tui` (non-editable branch) silently no-op'd
if the active venv already had an editable install of `bbsengine6`.
PEP 660's editable finder `.pth` hook wins on `import`, so a
subsequent `pip install /srv/repo/bbsengine6/bbsengine6-*.whl` would
write a fresh `dist-info` but be shadowed at import time; the
operator's running TUI kept seeing the source tree, `pip show`
kept reporting the source-tree version, and fresh wheels piled up
in `/srv/repo/bbsengine6/` until `du` was the only way to notice.
This is structurally distinct from the minute-resolution collision
fixed previously — same observable symptom ("no changes"), different
failure mode (venv-state conflict, not filename collision).

The fix is a precondition check, not a precondition repair.

* `py/src/Makefile` — new `precheck-editable` recipe macro. Runs
  `pip show bbsengine6` and bails non-zero if the output contains
  `Editable project location:`, pointing the operator at the two
  clean remedies (`deploy --editable bbsengine6.tui` for editable,
  `pip uninstall bbsengine6 && deploy bbsengine6.tui` for wheels).
  Implemented as a recipe-time macro (not a `.PHONY` prerequisite)
  so the check only fires on the non-editable branch — `deploy
  --editable` legitimately has an editable install and must not
  be flagged. The Makefile does **not** call `pip uninstall` on the
  operator's behalf: that loses post-install hooks, races with any
  concurrent editable install in the same venv, and overrides the
  operator's conscious choice to be in editable mode.
* `py/src/Makefile` — new `verify-install` recipe macro, ported
  from `zoidoffice/src/Makefile VERIFY_INSTALL` (same shape as
  `casino/Makefile:verify-install`). Three-way cross-checks the
  wheel filename, the wheel METADATA, and the post-install `pip
  show` Version. Wired into the non-editable branch of
  `deploy-tui` so any future silent-no-op (orphaned `.dist-info`,
  permission-denied mid-install, the editable-in-venv conflict
  above, etc.) gets caught immediately rather than manifesting as
  weeks-old wheels in `/srv/repo/bbsengine6/`.
* `py/src/Makefile` — `precheck-editable` now branches on
  `DEPLOY_WITH_DEPS` (set by `deploytool --with-deps`; plumbed in
  the deploytool commit alongside this one). Default branch: hard
  fail with the two-remedy message, plus a third line pointing
  operators at the `--with-deps` escape hatch. `DEPLOY_WITH_DEPS=1`
  branch: warn-and-proceed. The `--with-deps` flag semantically
  promises "rebuild the venv, no questions asked", so blocking on
  a mixed editable/wheel state under that flag is wrong-headed;
  the post-install `verify-install` macro then becomes the actual
  correctness check — the editable `.pth` finder shadows the
  wheel install, `pip show` disagrees with the wheel's METADATA,
  and the deploy aborts with the same precise diagnosis as the
  default branch. The Makefile still does NOT call `pip uninstall`
  on the operator's behalf under either branch.

### docs: PREPARE_BUILD cross-reference points at the bed canonical

`bbsengine6/Makefile` already mirrors `bed/Makefile` for the
`PREPARE_BUILD` macro (rename foreign-owned `$(1)/build/`,
`chmod g-s,+t`). Comment cross-reference was aimed at the wrong
line numbers; promoted to the canonical `bed/Makefile:165-189`
with an explicit "all four projects (bed, bbsengine6, zoidoffice,
casino) target this comment + macro pair" note. No behavior
change.

### feat(bbsengine6.config): generic JSON+env+default merge helpers

A new `bbsengine6.config` module (`py/src/bbsengine6/config.py`)
provides small, dependency-free helpers for loading JSON config
files, deep-merging override dicts, expanding `${VAR}` and `~` in
string values, and layering environment variables on top of JSON
values. Downstream apps (zoidoffice, asimov, bed, achilles, ...) can
now share a single precedence chain instead of each re-implementing
their own.

The exported helpers are:

- `load_json_file(path)` — read a single JSON file; non-dict /
  missing / malformed → `{}`. Never raises. The `strict` variant
  raises for operator-visible misconfigurations.
- `search_config(candidates, *, env_var=None)` — walk a list of
  candidate paths; honor an optional environment-variable override
  (`ZOIDOFFICE_CONFIG`, `BED_CONFIG`, etc.) as the highest-priority
  entry.
- `deep_merge(base, override)` — recursive merge; override wins on
  scalar conflicts; lists replaced wholesale.
- `resolve(env, json, default)` — single-key precedence with env
  vars on top, then JSON, then hardcoded default.
- `get_section(config, *path)` — safe nested-dict lookup.
- `expand_value(value, *, env=None)` — recursive `${VAR}` and `~`
  expansion for any JSON-derived tree.
- `expand_paths(value)` — additional `safe_path` expansion for keys
  ending in `_path` / `_file` / `_dir` / `_socket` / `_log`
  (matches the convention already in `bed.config`).
- `build_argparse_defaults(json_config, *, section, keys, env_prefix,
  global_section, hardcoded_defaults, coerce)` — produce the
  `defaults=` dict for an argparse group with the full precedence
  chain in one call.
- `validate_schema(config, *, known_sections)` — light warning when
  the JSON file contains unknown top-level sections. Doesn't raise;
  typo-catching only.

70 new unit tests in `py/src/bbsengine6/tests/test_config.py`.

### build: `PY_VERSION` now has second resolution; `deploy-tui` falls back to newest wheel in `OUTDIR`

`bbsengine6/Makefile:26` `PY_VERSION` (and the matching fallback
`bbsengine6/py/src/Makefile:7` `VERSION`) are now captured at
**second** resolution (`%Y%m%d%H%M%S`), not minute resolution.
Minute resolution produced a 60-second window during which two
`deploy bbsengine6.tui` runs collided on the same wheel filename:
the second run's `pip install` saw the freshly-built wheel's
`Version` was identical to the already-installed `Version` and
reported `Requirement already satisfied`, leaving the operator's
venv stale while new wheels piled up in `/srv/repo/bbsengine6/`.
Second resolution collapses that window to one second.

`bbsengine6/py/src/Makefile deploy-tui` now also logs the resolved
wheel path (`WHEEL=…`) to stdout before invoking pip and falls
back to `ls -t $(OUTDIR)/$(PROJECT)-*.whl | head -1` if the
explicit-filename wheel isn't on disk (e.g. clock skew between
parent Makefile parse time and the moment `python -m build`
finished writing the wheel, or a stale OUTDIR). The fallback
prints a stderr breadcrumb so the operator can see when it
fired.

### php: local bcrypt hashing, no PostgreSQL crypt() round-trip

The PHP `bbsengine6\member\lib\setpassword()` and
`checkpassword()` previously delegated to PostgreSQL's `crypt(..., gen_salt('bf'))`
and `crypt(plaintext, password)` respectively. Both round-trips have
been replaced with local PHP hashing via a new
`bbsengine6\password` namespace (`libpassword.php`), mirroring
`bbsengine6.util.encryptpassword` on the Python side.

**Why:** the prior PHP path was the asymmetric cousin of the
Python side: Python already produced new hashes locally
(`bbsengine6.util._BCRYPT_ROUNDS = 6`) but PHP still round-tripped
through PG. This caused two issues — (1) every `checkpassword()` call
hit PG twice (the SELECT and the embedded `crypt()` expression), and
(2) any drift in PG-side bcrypt behaviour (e.g. pgcrypto version
change, cost-factor mismatch) was an auth outage waiting to happen.

**New code:**

* `bbsengine6/php/libpassword.php` — single source of truth for
  PHP-side hashing. Exposes `hash_password()`,
  `verify_password()`, `is_healthy_hash()`, `needs_rehash()`,
  `classify_hash()`. Cost factor `BBSENGINE_BCRYPT_COST = 6`
  matches Python `_BCRYPT_ROUNDS = 6` and PG `gen_salt('bf')`
  default.
* `bbsengine6/php/libmember.php` — `setpassword()` now produces the
  hash locally and writes it via a single `UPDATE password = :hash
  WHERE moniker = :m`. `checkpassword()` now does one
  `SELECT password FROM ...` and verifies locally via
  `password_verify()`. A new `rehashpassword()` helper rewrites a
  legacy hash to fresh bcrypt on the first successful login of a
  legacy user (mirrors Python's opportunistic-rehash pattern).

**Tests:**

* `bbsengine6/tests/unit/test_libpassword.php` — 13 unit tests
  pinning hash format, prefix, length, constant-time verify,
  healthy/needs_rehash classification. No DB required.
* `bbsengine6/tests/integration/test_php_password_round_trip.php`
  — 9 integration tests against a live PG (requires
  `BBSENGINE_TEST_DSN`). Includes the legacy-`$1$`-MD5-crypt
  rehash end-to-end and an explicit "PG `crypt()` does not
  recognise `$2y$`" pin so any future regression that reintroduces
  the round-trip backstop catches the prefix drift immediately.

**Cross-platform note:** PHP `password_hash()` emits `$2y$` and
Python passlib emits `$2b$`. PG `crypt(plaintext, stored)` only
recognises `$2a$` (i.e. `gen_salt('bf')` output), so neither local
writer is verifiable by the PG side. This was always going to be
true once the DB round-trip was eliminated; verification is now
local on each platform and the lock-step-with-PG property is no
longer load-bearing.

**Compatibility:** the `chk_member_password_bcrypt` CHECK
constraint (`^\$2[abxy]\$`, length 60) and the audit hook
(`bbsengine6.member.audit_password_hash`) accept `$2y$` and the
rehash path so legacy `$1$` MD5-crypt rows are healed organically
on the next successful login.

@since 20260823

### py: member.checkpassword — local verify + opportunistic rehash (PHP parity)

Mirrors the PHP-side change above on the Python side:

* bbsengine6.member.checkpassword no longer round-trips through
  PostgreSQL crypt(plaintext, password). The stored hash is
  fetched with one SELECT and verified locally via a new
  bbsengine6.member.lib._verify_any helper that tries stdlib
  crypt(plaintext, stored) first (handles $1$ MD5-crypt,
  $5$ SHA-256-crypt, $6$ SHA-512-crypt, and the
  $2[abxy]$ bcrypt family in one path with the constant-time
  guarantees of the underlying libc) and falls through to passlib
  bcrypt.verify as a bcrypt-specific fallback.
* On successful verify of a legacy $1$ MD5-crypt hash, the
  column is transparently rewritten to a fresh $2b$06$...
  value via the new bbsengine6.member.rehashpassword helper.
  Healthy $2[abxy]$06$ rows are not rewritten. The 2026-08-22
  bed auth login incident now heals organically on the next
  successful login — no psql \i bbsengine6.sql migration
  required.
* bbsengine6.member.setpassword gains the full
  CONN_POOL_PATTERN (cur=/conn=/pool=/args= priority order) and
  surfaces a no-row failure (False return + level=error log)
  instead of the silent no-op behaviour of the pre-rewrite path.
* bbsengine6.util.encryptpassword is the new single-source-of-truth
  helper for new password hashes; setpassword and any future
  caller delegate here so the cost factor and salt format stay in
  lock-step with the PHP side.

**Why mirror PHP:** the pre-2026-08-23 code was asymmetric — PHP
round-tripped through PG (two PG queries per login), Python already
produced new hashes locally via bbsengine6.util._BCRYPT_ROUNDS=6
but still round-tripped the verify. After both sides rewrite, every
auth path produces the hash locally, verifies locally, and writes the
hash in a single UPDATE. The chk_member_password_bcrypt CHECK
constraint on engine.__member.password and the per-auth
audit_password_hash diagnostic accept both $2y$ (PHP) and
$2b$ (Python) prefixes so cross-language migrations are
uneventful.

**Cross-platform note:** PHP password_hash() emits $2y$,
Python passlib emits $2b$, PG crypt(plaintext, stored) only
recognises $2a$. Since verification is now local on each
platform after eliminating the DB round-trip, the prefix drift is
harmless. tests/integration/test_php_password_round_trip.php
pins PG crypt() does not recognise $2y$ so any future
regression that reintroduces a PG-side backstop catches the mismatch
immediately.

**Tests:** py/tests/test_member_checkpassword_local.py (new, 18
cases) pins no-PG-crypt, exactly-two-selects-no-updates on healthy
rows, opportunistic rehash on $1$ legacy, malformed-hash
tolerance, and full CONN_POOL_PATTERN coverage for both
checkpassword and the new rehashpassword.

@since 20260823

### member + sql: password column hardening — legacy MD5-crypt audit + bcrypt CHECK constraint

Resolves the three checkboxes in `zoid6/TODO.md` "Password column
hardening — legacy MD5-crypt migration (@since 20260822)" via
`bbsengine6` (the schema authority) and a per-auth audit hook.
This is the follow-up to the 2026-08-22 `bed auth login` incident
where `engine.__member.password` for `jam` held a `$1$` MD5-crypt
hash that defeated the bcrypt round-trip in `member.checkpassword`.

**New code (Python):**

* `bbsengine6.member.audit_password_hash(args, moniker, **kwargs)`
  reads `engine.member.password` for `moniker` and returns a
  `PasswordHashAudit` namedtuple
  (`present, non_empty, prefix, is_bcrypt, is_md5crypt, length_ok`).
  Emits `level="warning"` on any unhealthy flag or `True`
  `is_md5crypt`; emits `level="ok"` on the healthy path. Follows
  the standard CONN_POOL_PATTERN (cur → conn → pool → args).
  Docstring points at `zoid6/TODO.md` and
  `bbsengine6/io/echo.py:1317` for the level="ok" green-bg prefix.

* `bbsengine6.member.audit_password_column(args, **kwargs)` returns
  the list of monikers holding a legacy `$1$` hash. SQL matches the
  discovery query in `zoid6/TODO.md` verbatim:
  `select moniker from <schema>.member
   where password is not null and password ~ '^\$1\$'`.
  Same CONN_POOL_PATTERN; same prefix-routing via `_qualified()`.

* `member.checkpassword` now calls `audit_password_hash(args,
  membermoniker, cur=cur)` immediately before the bcrypt round-trip
  SELECT, on the same cursor (no extra connection). On
  `is_md5crypt=True` the audit logs the warning AND the round-trip
  proceeds (the legacy plaintext might still MD5-match the stored
  hash; the warning is the operator signal, not a hard reject).

**New schema (SQL):**

* `bbsengine6/sql/member.sql` — top-of-file comment documents the
  bcrypt-only invariant, lists the known-good writers
  (`bbsengine6.member.setpassword`, `console.member.{add,edit}`,
  `bbsengine6/scripts/setpassword.py`, post-port `engine/join.php`),
  and cross-references the audit + migration entry points.
* `bbsengine6/sql/manage_password_format.sql` (new) — adds
  `chk_member_password_bcrypt` on `engine.__member.password`:
  `password ~ '^\$2[abxy]\$'`. NULL is allowed; any non-NULL value
  must satisfy the prefix check. Created via
  `DROP CONSTRAINT IF EXISTS` then `ADD CONSTRAINT` so re-running
  `bbsengine6.sql` against an existing DB is a no-op. Run AFTER the
  audit is clean (CHECK constraints validate on write, not on
  creation).
* `bbsengine6/sql/bbsengine6.sql` — `\i manage_password_format.sql`
  added after `memberview.sql` / `memberinet.sql` so the constraint
  is in place by the time `memberview.sql`'s predicates reference
  `engine.__member`.

**New tests (Python):**

* `bbsengine6/py/tests/test_member_audit_password_hash.py` —
  16 unit cases covering the 6-case matrix from the TODO
  (bcrypt, MD5-crypt, NULL, empty, 34-char non-prefixed,
  60-char non-bcrypt) plus 4 specific cases
  (missing member, cursor reuse) plus 6 wire-up tests in
  `TestCheckpasswordCallsAudit` pinning `checkpassword`'s
  audit invocation against both healthy bcrypt and the
  2026-08-22 MD5 incident scenario.
* `bbsengine6/py/tests/test_member_legacy_hash_audit.py` — 6 unit
  cases pinning the audit SQL pattern (engine.member schema, NULL
  exclusion, `$1$` regex, no bcrypt prefix) plus 1 live-DB
  regression pin asserting `len(rows) == 0` against the `zoid6`
  database (gated by `@pytest.mark.requires_db`; the conftest's
  `test_transaction` rollback keeps any change from persisting).
  The live-DB assertion fails as long as any row holds a `$1$`
  hash — operator signal that the migration is incomplete.

**Verification:**

- [x] `python3 -m pytest tests/test_member_audit_password_hash.py tests/test_member_legacy_hash_audit.py -m unit -p no:cacheprovider` → 22 passed, 1 skipped (live-DB).
- [x] `python3 -m pytest tests/test_console_member_add_edit.py tests/test_auth_password_e2e.py tests/test_password_hash_scrypt.py tests/test_member_verify_found.py -m unit -p no:cacheprovider` → 27 passed, 7 deselected (existing tests unaffected).
- [x] `python3 -m ruff check src/bbsengine6/member/lib.py tests/test_member_audit_password_hash.py tests/test_member_legacy_hash_audit.py` → All checks passed.

Cross-ref: `zoid6/TODO.md` "Password column hardening" (all three
checkboxes now ticked). The audit-and-migrate workflow is split
between the two repos per the TODO note: this repo owns the schema
and the SQL layer; zoid6 owns the operator-facing audit-and-migrate
workflow + the `.pth` cleanup.

**Follow-ups (this release):**

* `bbsengine6.startup` now installs the constraint and runs the
  audit on every bootstrap — no operator `psql \i bbsengine6.sql`
  re-run required. New `backend/checkpasswordformat.py` module
  SAVEPOINT-wraps a `DROP CONSTRAINT IF EXISTS` / `ADD CONSTRAINT`
  pair (idempotent against any DB state) and then unconditionally
  calls `bbsengine6.member.audit_password_column(args, conn=conn)`
  on the same connection. Wired into `backend/stage_one.py`'s
  module tuple immediately after `checkclasses`, so the engine
  schema is already owned by `zoid6` (`checkengine.py:97`) before
  the constraint lands. New `database.constraintexists(args, conn,
  schema, constraintname)` helper mirrors the shape of
  `classexists`/`functionexists`/`typeexists`/`schemaexists`
  (joins `pg_constraint` against `pg_namespace` for schema
  filtering).

* New tests: `tests/test_checkpasswordformat.py` (8 unit cases
  pinning the install/audit sequence against a stub database)
  plus 3 `constraintexists` cases added to
  `tests/test_database_helpers.py`. Lint+test verification
  commands below.

* **Upstream close-out (cross-repo):** 7 casino test fixtures
  were writing raw `crypt('test', gen_salt('md5'))` hashes into
  `engine.__member.password` from their `asyncSetUp` blocks
  (`casino/src/casino/tests/test_{blackjack_flow,
  blackjack_three_hands, member_services, new_features_integration,
  player_observer, player_stats_integration, slots_integration}.py`).
  Each one has been migrated to the canonical reference shape
  (`casino/tests/test_member_create_and_casino_auth.py:294-319`):
  insert with the `password` column omitted (so it stays NULL,
  which the constraint allows), then call
  `bbsengine6.member.setpassword(args, password, moniker, pool=pool)`
  which writes `crypt($1, gen_salt('bf'))`. The orphan
  `casino/src/casino/sql/test_data.sql` (zero importers, grep
  empty) has been deleted. These two changes close the upstream
  write path that produced the `$1$` hashes in the first place;
  the constraint + audit are now belt-and-braces rather than the
  sole line of defense.

* `bbsengine6/scripts/setpassword.py` — capture the return value
  of `member.setpassword` (None when the UPDATE matched zero
  rows), log via `io.echo(level="error")` on the failure path,
  and `sys.exit(1)` so deploy scripts and CI can detect the
  bad state instead of seeing only a False verify result.

**Verification (this release):**

- [x] `python3 -m pytest tests/test_checkpasswordformat.py tests/test_database_helpers.py -m unit -p no:cacheprovider` → all passed.
- [x] `python3 -m bbsengine6.startup --databasename zoid6` → logs `constraint chk_member_password_bcrypt: ok` + `audit_password_column: 0 row(s) with $1$ hash`.
- [x] `psql -d zoid6 -c "\d engine.__member"` lists `chk_member_password_bcrypt` in the CHECK constraints section.
- [x] `python3 -m pytest casino/src/casino/tests/ -m unit -p no:cacheprovider` → all passed (fixtures use `libmember.setpassword`, no MD5 writes).
- [x] `python3 -m ruff check src/bbsengine6/backend/checkpasswordformat.py src/bbsengine6/database.py src/bbsengine6/backend/stage_one.py scripts/setpassword.py` → All checks passed.

### build: add `PREPARE_BUILD` macro to root Makefile

`bbsengine6/Makefile` lacked the `PREPARE_BUILD` helper that
`bed/Makefile:189-194`, `getdate_next/Makefile:32-36`,
`casino/Makefile:75-110`, and `zoid6/src/Makefile:132-167` (this
release) already have. The macro is added with `$(1) = $(CURDIR)/py`
to match the existing `build` target's `cd py && python3 -m build`
shape.

`py/` is currently mode `775` (no setgid), so this tree is
"safe-by-accident" today — `py/build/` won't inherit setgid from
`py/`, so the `shutil.copystat` cascade won't fire. The macro is
added here anyway so a future `chmod 2775 py/` (e.g. matching the
rest of the tree for consistency) doesn't silently regress the
EPERM.

`py/src/Makefile` was intentionally *not* modified — it only
runs `pip install -e .`, never `python -m build`, so the EPERM
cascade can't apply there.

Tracked in `zoid6/TODO.md` "PREPARE_BUILD standardization
(cross-project)" — that checkbox is now ticked.

### member: auth hot path uses psycopg3 `%s` parameter binding, not `database.query()` `$N`

Three functions on the password-verification path now bypass the
`database.query()` regex-replacement layer and bind their values
as standard psycopg3 `%s` parameters:

* `bbsengine6.member.checkpassword` — both the
  `select password from <schema>.member where moniker=…` read
  and the `password=crypt(…, password)` match.
* `bbsengine6.member.has_password` — the `select password from
  <schema>.member where moniker=…` read.
* `bbsengine6.member._verify_member` (the shared implementation
  used by `verifyMemberFound` / `verifyMemberNotFound`) — the
  `select 1 from <schema>.member where <column>=…` read.

The schema slot still flows through `_qualified(rel, args)` so
`args.databaseschema` is respected (the same routing
`database.query()` would do for `$engine.member`); only the value
binding changed. End result:

* The password value never flows through the `database.query()`
  `re.finditer` / `sql.Literal` substitution path on the auth
  hot path.
* psycopg3 prepared-statement caching applies to all three
  functions (the prior `$1` → `sql.Literal` form bypassed the
  cache because the SQL string changed per call).
* `cur.execute(sql, params)` is the canonical psycopg3 form; the
  rest of the file can be migrated to it incrementally.

The `regression` commit `f0e9366` (`use %s placeholder in
verifyMemberFound and has_password`) pre-dated the
`database.query()` rework that handles `$N` → `sql.Literal()`
(`7a30b29`); its bug was real for an earlier code path and is
no longer reproducible. This commit is belt-and-braces: it
removes one entire layer of "is the regex doing the right thing"
worry from the auth path and pins the new `%s` + parameter-tuple
shape with a unit test (`tests/test_member_verify_found.py`
`test_emits_select_against_schema_member_keyed_on_loginid` was
updated to assert `where loginid = %s` and
`params == ('alice',)`).

### build: depend on `clean` to wipe stale egg-info before each `python -m build`

The root `Makefile` `build` target (`bbsengine6/Makefile:156-157`)
now declares `clean` as a prerequisite so `bbsengine6/py/build/`,
`bbsengine6/py/dist/`, and `bbsengine6/py/src/bbsengine6.egg-info/`
are wiped before every `python -m build` invocation. This sidesteps
the setuptools SOURCES.txt absolute-path failure mode that surfaces
when `bbsengine6.egg-info/SOURCES.txt` carries forward absolute
paths from a prior run (the working tree currently has a stale
`bbsengine6.egg-info/SOURCES.txt` from a `2026-08-21 10:59` build
whose paths point at the operator's home).

`py/Makefile:clean` was extended from `-rm *~` to also wipe
`build/`, `dist/`, `src/*.egg-info`, and the standard pytest /
ruff / mypy cache directories, mirroring the pattern already
shipped in `zoid6/src/Makefile:118-124`.

### deploy-tui: install from `/srv/repo/bbsengine6/` wheel by default; `DEPLOY_EDITABLE=1` for editable

Part of the cross-monorepo Phase 1 work in `deploytool`'s
`--editable` flag (see `deploytool/CHANGELOG.md` `[Unreleased]`).
bbsengine6's `deploy-tui` target now matches the pattern shared
by `bed`, `casino`, `zoid6`, and `deploytool`.

Before: `bbsengine6/Makefile deploy-tui` called
`$(MAKE) -C py/src install`, which `py/src/Makefile:11-12`
resolved to `cd .. && pip install --no-cache-dir -e .` — always
editable, never went through `/srv/repo/bbsengine6/`.

After:

- Default: `bbsengine6/Makefile deploy-tui` depends on `build`
  and delegates to `py/src/Makefile deploy-tui`. The inner
  target picks the most-recently-built wheel under
  `/srv/repo/bbsengine6/bbsengine6-*.whl` via
  `ls -t | head -1` and installs it with
  `pip install --no-cache-dir $WHEEL`.
- `DEPLOY_EDITABLE=1` (set by `deploytool --editable`):
  installs editable from the source tree via
  `cd py && pip install --no-cache-dir -e .`.

The wheel glob uses `$(PROJECT)-*.whl` (not `$(VERSION)-*.whl`)
because the wheel filename embeds the version from
`pyproject.toml`'s `[tool.setuptools.dynamic] version = ...`
attribute — which `py/src/Makefile version:` writes fresh to
`src/bbsengine6/_version.py` at build time. Top-level
`bbsengine6/Makefile`'s `$(VERSION)` is `6` (a semantic-version
sentinel) and does NOT match the wheel filename.

Verified: `make -n -C bbsengine6 deploy-tui` shows
`pip install /srv/repo/bbsengine6/bbsengine6-*.whl`; the same
with `DEPLOY_EDITABLE=1` shows `cd py && pip install -e .`.

### backend: dedicated `zoid6` role owns the SECURITY DEFINER helpers

The five `public.*` privilege helpers (`manage_schema_priv`,
`manage_database_priv`, `manage_role_privs`,
`manage_secondary_role`, `get_role_privs`) are now owned by a
dedicated, unprivileged role `zoid6` rather than by the bootstrap
principal. This narrows the trust surface enforced by
`database.verify_function_owner` and removes a non-deterministic
allow-list entry (`getpass.getuser()`).

- New `backend.checkzoid6role` module: creates `zoid6` as
  `NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN INHERIT`. Hard-fails
  if a pre-existing `zoid6` has `rolsuper=True`, since that would
  silently break the trust model.
- New `backend.checkzoid6owner` module: idempotently reassigns
  ownership of the five helpers to `zoid6` via
  `ALTER FUNCTION public.<fn>(<args>) OWNER TO zoid6`. Verbose on
  first run so the operator sees exactly which functions moved
  owners and from whom. Idempotent on re-run.
- `backend.checkengine`: allow-list changed from
  `(install_role, "postgres")` to hard-coded `("zoid6", "postgres")`.
  `postgres` is kept for one release as a transition aid; it will
  be dropped in a subsequent release — see
  `bbsengine6/TODO_zoid6_role.md`.
- `stage_zero` module loop now runs `checkzoid6role` after
  `checkroles` and `checkzoid6owner` after `checkfunctions`.
- `backend.checkengine` now creates the `engine` schema with
  `AUTHORIZATION zoid6` (fresh installs) or, for BC, issues
  `ALTER SCHEMA engine OWNER TO zoid6` when an existing schema is
  owned by a different role. This is required because
  `manage_schema_priv` is owned by `zoid6` (NOSUPERUSER) and can
  only GRANT on objects it owns.
- `database.verify_function_owner` error message updated to
  reference `checkzoid6owner`.
- Tests: `py/tests/test_manage_schema_priv.py` now asserts
  `EXPECTED_OWNER = "zoid6"`. New integration tests
  `tests/integration/test_checkzoid6_role.py`,
  `tests/integration/test_checkzoid6_owner.py`, and a new
  `test_main_reassigns_engine_schema_to_zoid6_when_owner_differs`
  case in `tests/integration/test_stage_one_checkengine.py`.

#### Follow-up: cross-module schema ownership (casino)

Downstream of the role tightening above, the `casino` schema's
ownership also matters. `manage_schema_priv` (owned by `zoid6`)
`GRANT USAGE` on the `casino` schema in
`casino/sql/schema.sql`, so the schema itself must be owned by
`zoid6` (or another role the helper owns objects under) for that
grant to succeed under NOSUPERUSER. Otherwise the bootstrap halts
with `permission denied for schema casino`.

The casino project now ships `casino.startup.checkcasino` — a
mirror of `bbsengine6.backend.checkengine`'s schema-ownership
block — which `casino.startup.main` invokes between the citext
extension install and the `schema.sql` import. It is idempotent
and `BBSENGINE6_DBNAME`-aware (uses the same env var as the
existing `casino` test plumbing). See `casino/CHANGELOG.md` for
the casino-side entry and `bbsengine6/TODO_zoid6_role.md` §4 for
the cross-module pattern.

#### Follow-up: stage_one regression fix + bank schema ownership

Two related fixes found during the `casino.startup.checkcasino`
smoke test on a fresh `zoid6` database:

- `backend.stage_one`: add `"checkzoid6owner"` to the module
  loop (after `"checkfunctions"`). `stage_zero` runs against the
  admin `postgres` DB and its `checkzoid6owner` correctly
  reassigns the 5 helpers to `zoid6` there, but `stage_one` runs
  against the target DB (`args.databasename`) and its
  `checkfunctions` re-`CREATE`s the helpers, resetting their
  owner to the connecting user (typically the bootstrap
  superuser). Without this fix, the target DB's copies stay
  owned by the bootstrap principal — the verbose
  "already zoid6" line in `stage_zero`'s output masked the
  regression because it reported against the admin DB, not the
  target DB. This broke the trust model that
  `database.verify_function_owner` and
  `casino.startup.checkcasino` both depend on.

- `backend.checkbank`: add `_ensure_zoid6_owner()` block that
  issues `ALTER SCHEMA bank OWNER TO zoid6` after
  `bank_schema.sql` is imported, idempotent. Per the operator
  directive ("we should be using `zoid6`, not `opencode`"),
  all BBS-owned schemas (`engine`, `bank`, `casino`) now have
  `zoid6` as their canonical owner. The block mirrors the
  engine schema block in `checkengine` and the casino schema
  block in `casino.startup.checkcasino`.

End-to-end verification on a fresh `zoid6` DB: all 5 SECURITY
DEFINER helpers owned by `zoid6` in both admin and target DBs;
all 3 BBS schemas owned by `zoid6`; `casino.startup.main` runs
cleanly with no `permission denied for schema casino`; both
`bbsengine6` and `casino` startup are idempotent on re-run.

### net.ping: shared WebSocket liveness check for any bbsengine6-based daemon

New module `bbsengine6.net.ping` provides a single code path for
the `bedping`-style friendly-error pattern used across every
project that talks to a bbsengine6-based WebSocket daemon. The
helper exposes:

- `class PingUnavailable(Exception)` — carries `host`, `port`,
  original `exc`, and a `prog` keyword that controls the message
  prefix so each `*-ping` shim identifies itself.
- `async def connect(host, port, *, path="/", timeout=5.0, prog="ping")`
  — bare WebSocket connect that converts
  `ConnectionRefusedError`, `OSError`, `asyncio.TimeoutError`, and
  `WebSocketException` into `PingUnavailable` (no raw exception
  escapes).
- `async def send_ping(...)` — opens a connection, sends
  `{"type":"ping"}`, returns the parsed JSON reply.
- `def build_parser(prog)` — argparse builder shared by every
  shim so `--host`, `--port`, `--path`, `--timeout` behave
  identically regardless of which project owns the entry point.
- `def main(argv, *, prog)` — CLI entry point that catches
  `PingUnavailable`, calls `bbsengine6.io.echo(level="error")`,
  and returns `1` so the shim exits non-zero without a Python
  traceback.

New bin script `bin/bbsengine6-ping` is a 6-line shim around
`bbsengine6.net.ping.main(prog="bbsengine6-ping")` and ships via
`[tool.setuptools] script-files` in `pyproject.toml`.

The `bedping` shim, the new `casino-ping` shim, and the new
`zoid6-ping` shim all call the same helper, so future
`websockets`-version fixes land in one place.

### net.transport: WebSocketServer accepts `binds=[]` for multi-bind

`WebSocketServer.__init__` now takes an optional `binds` keyword
argument — a sequence of `(host, port)` pairs. When given, the
server opens one listening socket per `(family, address)` tuple
returned by `getaddrinfo(host, port, AF_UNSPEC)`, so a single host
name like `localhost` fans out to one IPv4 and one IPv6 listener
without a dual-stack socket.

Legacy `host=`/`port=` keyword arguments remain the 1-element
shortcut; passing both shapes raises `ValueError`. State
(`channel_state`, `session_manager`, service registry, router,
pre/post dispatch hooks) is shared across every listener so a
service registered once reaches every bind.

`start()` opens all sockets first, then hands each to its own
`websockets.serve()` call. Partial-bind failures (EADDRINUSE on the
second bind, EACCES on a privileged port, `gaierror` on a typo'd
host) close any sockets already opened and re-raise so the caller
sees a clean error rather than a half-started server.

New attributes on `WebSocketServer`:

* `self._bound_addrs: List[Tuple[str, str, int]]` — `(family_name,
  host_str, port)` per listener, in bind order. New code should
  prefer this over the legacy `self._bound_port` (which still
  reports the port of the first listener for back-compat).

New test file `py/tests/test_transport_multibind.py` covers
dual-stack bind, `localhost` expansion, partial-bind cleanup,
idempotent `stop()`, unresolvable host before any socket opens,
and services visible across every listener. All existing
transport tests pass unchanged.

### net.transport: warn on `register_service` overwrites

`WebSocketServer.register_service` overwrites `self._services[msg_type]`
per-key (and the `self._default_service` slot) without telling the
operator. A second registration for the same message type was
indistinguishable from a first, which made intentional swaps (e.g.
bed's `PingService` overwriting a router's own `["ping"]`) and
accidental swaps (e.g. a custom router registering `"auth"` and
silently replacing bed's `AuthService`) both invisible.

The method now emits a `WARNING` line whenever a registration would
replace an existing handler, naming both the previous and the new
service class. New regression test in
`py/tests/test_register_service_overwrite.py` covers per-type,
mixed-batch, default-slot, and "last writer wins" cases.

### bbsengine6: `make install` runs `version` and rebuilds with `--no-cache-dir`

- `Makefile` `install` now depends on `version` (closes a gap where
  `bbsengine6 --version` reported a stale date if the operator
  invoked `install` without first running `make version`).
- The wheel-rebuild step now passes `--no-cache-dir` so wheel reuse
  from a previous build can never silently regress the install.

### www: protect remote templates_c/ from wwworg/wwwcom deploy rsyncs

`bbsengine6/www/Makefile` `org` and `com` push rsyncs now pass
`--exclude "templates_c"` and `--chmod=Dg+rwxs`.

Without `--exclude`, every `deploy bbsengine6.wwworg` push walked
`templates_c/` on the remote with `--delete-after`; the per-sub
`stage` target creates `$(ORGSTAGE)templates_c/` (and
`$(COMSTAGE)templates_c/`) empty locally, so rsync considered every
file on the remote's cache stale and deleted it. Smarty then had to
recompile every template on the next request — and worse, on hosts
where the cache was not group-writable + setgid, the first request
failed outright with a `Permission denied` writing to
`templates_c/<hash>.php`.

`--chmod=Dg+rwxs` makes rsync enforce `g=rwxs` on every directory
it creates on the remote, so freshly-created `templates_c/` (or any
other dir) ends up group-writable + setgid without operator
intervention.

`bbsengine6/www/org/Makefile` and `bbsengine6/www/com/Makefile`
`stage` targets keep their `mkdir -p .../templates_c/` (for local
dev) and now also `touch .../templates_c/.gitkeep` so an empty
stage dir doesn't confuse rsync with "directory disappeared"
warnings. The push-rsync `--exclude` is what actually protects the
remote.

Regression coverage lives in
`deploytool/tests/test_deploy_bbsengine6_www.py`:
`test_www_push_rsyncs_exclude_templates_c_and_setgid_dirs` and
`test_wwworg_and_wwwcom_stage_templates_c_locally_with_gitkeep`.

### smarty/function.teos: drop doubled TEOSURL prefix on `$uri`

`{teos uri=…}` no longer double-prefixes `TEOSURL`. The plugin now
respects a `title=` arg (added in the previous commit) without
re-emitting the URL prefix a second time. Operators that hard-coded
the doubled URL in their templates can drop one copy.

### smarty/function.teos: accept optional `title` arg

The `{teos}` plugin now accepts `title="…"` so callers can label the
breadcrumb independently of the link text.

### Phase 6: bbsengine6.channel — production schema, namespacing, admin

`bbsengine6.channel` is now usable end-to-end by casino and other
modules. The pub/sub primitives in `bbsengine6.net` have existed
for a while but had no prod schema, no permission gating, no admin
surface, and no shared channel state between the WebSocketServer
and the message router.

**New code:**

- `bbsengine6/services/channel.py` — `ChannelService` with
  `create_channel`, `get_channel`, `list_channels`,
  `set_announce_only`, `add_announcer`, `remove_announcer`,
  `can_publish`. Persistent via `engine.__channel`,
  `engine.__channel_announcer`, `engine.channel` view.
- `bbsengine6/channel/naming.py` — `table_channel`, `member_channel`,
  `global_channel`, `announcement_channel`, `shout_channel`,
  `parse_channel`. Single source of truth for the channel naming
  convention so typos don't silently route messages to the wrong
  audience.
- `bbsengine6/channel/api/handler.py` — `MessageRouter` (subscribe /
  unsubscribe / get_subscriptions), `ChannelAdminHandler`
  (`channel_create` / `channel_list` / `channel_get` /
  `channel_set_announce_only` / `channel_add_announcer` /
  `channel_remove_announcer`), and `_auto_seed_channels` for lazy
  daemon member + channel seeding at register time. Reads both
  flat (bed.json) and nested (zoid6.json) config shapes.
- `bbsengine6/console/channel.py` — `con channel <verb>` CLI.
  JSON output. Each verb delegates to `ChannelService` and threads
  the actor moniker through `_require_authority`.
- `bbsengine6/backend/checkchannel.py` — `stage_one` checkclass
  that loads `engine.__channel` + `engine.__channel_announcer` on
  fresh DBs (idempotent on existing DBs).
- `bbsengine6/backend/checkmember_moniker_format.py` — always-run
  migration module that extends the `chk_member_moniker_format`
  constraint to permit namespaced monikers. Runs every startup;
  no-op once the constraint is updated.
- `bbsengine6/member/lib.py` — `RESERVED_MONIKERS` (4 shipped PG
  role names), `is_namespaced_moniker`, `_validate_moniker_shape`,
  `register_module_member` (bypass path for module bootstrap with
  structural namespacing requirement).

**Schema changes:**

- `engine.__channel` and `engine.__channel_announcer` — added.
- `chk_member_moniker_format` — extended to allow
  `<module>:<purpose>` namespaced monikers.

**Permission hardening:**

- `ChannelService._require_authority` returns None if the actor is
  a sysop OR the channel's `createdby`. Gates all mutators.
- `set_announce_only`, `add_announcer`, `remove_announcer` go
  through `_require_authority`. `remove_announcer` got a new
  required `actor_moniker` parameter (breaking change).

**bed.json / zoid6.json:**

- Top-level `channel` section with `enabled`, `modulepath`,
  `admin_handler_enabled`, `auto_seed` list. The auto_seed step
  lazily creates the namespaced daemon member (e.g. `zoid6:casino`)
  via `register_module_member` and seeds `casino:global` +
  `system:announcements` with the right announce-only settings.

**bed.main.BED.start** now constructs one `ChannelState()` per
daemon and threads it to both `WebSocketServer(channel_state=...)`
and `MessageRouterClass(..., channel_state=state)`. Per-router
`server._channel_state = self.channel_state` boilerplate removed.

**zoid6** `_register_module` forwards `config=module_config` to
sub-routers (TypeError fallback for older routers that don't
accept it). Modules can now read their `services.<module>` sub-config
without re-parsing the whole JSON.

**Tests** — 117 in bbsengine6 (test_member_reserved,
test_channel_config, test_cli_con, test_channel_naming,
test_message_channel, test_channel_announce_only), 5 in casino
(test_channel_integration). All pass.

**Bug fix:** `add_announcer` was calling `verifyMemberFound`
without the required `pool=` kwarg (pre-existing failure on legacy
test runs). Replaced with inline existence check on the same
connection as the INSERT.

**Bug fix:** `register_module_member`'s bypass path was tripping
on three layers of defense (shape validation, pool requirement,
default primarykey="id" on a table that has no id column). Now
threads `_skip_shape_validation=True`, builds its own
`database.connect` context when no caller pool/conn is given, and
defaults to `primarykey="moniker"`.

**Docs:** `bbsengine6/EXTENDING_CHANNELS.md` walks module authors
through the four-step onboarding pattern (channel_state kwarg,
sender_moniker plumbing, namespaced daemon members, auto_seed
entries). Cross-references added to `member/lib.py.RESERVED_MONIKERS`
and `channel/api/handler.MessageRouter`.

**Migration owner caveat:** `checkmember_moniker_format` runs
`ALTER TABLE engine.__member` which requires the connecting role
to own the table. In production that's `sysop` (per the GRANT
chain in `channel.sql`/`grants.sql`). In dev sandboxes where the
connecting role doesn't own the table, the migration can't apply
— this is a sandbox limitation, not a code issue.

## [0.0.1.dev202608032039] — 2026-08-03

### Phase 5: regression tests + ROBUSTNESS_REVIEW.md

Pin every Phase 1-4 fix with a regression test so future changes
can't reintroduce the bug silently. New tests in `py/tests/`:

- `test_echo_raw_lock.py` — Finding 4.4 (global `_raw` flag with no lock)
- `test_inputstring_filter_kwarg.py` — Finding 4.3 (filter kwarg leak)
- `test_inputdate_fallback.py` — Finding 4.7 (`getdate_next` not-optional)
- `test_listbox_key_end_math.py` — Finding 4.5 (`_handle_key_end` math)
- `test_bottombar_truncate.py` — Finding 4.6 (negative slice in `_render_bottombar`)
- `test_safe_path_containment.py` — Finding 2.9 (`util.get_safe_path` bypass)
- `test_password_hash_scrypt.py` — Finding 2.1 (scrypt migration)
- `test_module_runcallback_no_eval.py` — Finding 2.2 (eval → importlib)
- `test_packet_bounds.py` — Finding 2.7 (`Packet.decode` bounds check)
- `test_check_notifications_args_pool.py` — Stage-1 pool plumbing

Also adds `ROBUSTNESS_REVIEW.md` (681 lines) — the canonical audit
document. See `SPEC.md` §7 for the summary.

### Phase 4: Python I/O / UI hardening

7 findings, all fixed:

- `io/common.get_dsr` actually waits for the response (was racy).
- `io/inputstring.handle_help` declares `_input_dirty` properly
  (was a local; was never assigned).
- `inputstring()` pops `filter` from kwargs before forwarding to
  the verify callback (was leaking through and breaking the verify
  signature).
- `io/echo` adds a lock around the global `_raw` flag (was
  unsynchronized; racy in concurrent sessions).
- `listbox._handle_key_end` math off-by-one corrected.
- `bottombar._render_bottombar` produces a non-negative slice
  (was negative when the rendered buffer was shorter than the
  header).
- `inputdate` no longer requires `getdate_next` when not installed.

### Phase 3: PHP web layer hardening

14 findings, all fixed:

- `engine.php` no longer echoes passwords, hashes, or raw
  exception text into logs and HTTP responses.
- `engine.php` no longer echoes raw `PDOException` text into the
  HTTP response.
- Session cookie `lifetime` is `0` → fixed to a real expiry.
- Session cookie is `Secure` + `HttpOnly` + `SameSite=Lax`.
- `session.write` propagates the regenerated session id back to the
  client.
- `session.validate` rejects any string as a session id (was
  accepting arbitrary input).
- `libmember.checkflag` no longer indexes `fetchColumn()` like an
  array.
- `database.autoExecute` does not interpolate `$where` as raw SQL.
- `engine.accesspost("add", ...)` returns `false` for
  unauthenticated callers.
- `engine/router.php` renders Markdown via Parsedown **with
  safe-mode**.
- `engine/logout.php` actually destroys the session.
- `smarty/modifier.linkurl.php` no longer uses `preg_replace /e`
  (removed in PHP 7).
- `php/folder.php` validates the free-form path argument.
- `php/util.php` no longer hard-codes "now()" SQL strings.

### Phase 2: Python security + concurrency

9 findings, all fixed:

- `password_hash` migrated to scrypt (primary); SHA-256 kept for
  legacy verification only.
- `module.runcallback` no longer `eval()`s dotted callbacks — uses
  `importlib.import_module`.
- Bank transfers no longer have a TOCTOU race between balance read
  and write (single transaction).
- `member.verifyMemberFound` has no SQL-injection vector in the
  column name.
- `pgrole.py` no longer interpolates table/schema names into SQL.
- `blurb.py` migrated to `psycopg` (was `psycopg2`), constrains
  paths, persists approval state.
- `net/packet.Packet.decode` checks payload bounds before slicing.
- `folder.py` closes its database connection.
- `util.get_safe_path` can no longer be bypassed via a relative
  base.

### Phase 1: Python runtime crashes

7 findings, all fixed:

- `message.py` calls `_get_message_recipients` (was undefined).
- `member/lib.py` imports `psycopg` (was missing).
- `editor.py` no longer references undefined `diaryfn`, quotes
  paths properly, closes file descriptors.
- `menu.py` uses `setvariable` correctly (was a typo), guards
  `None` before `.upper()`, clamps negative indexes.
- `io/__init__.py` re-exports `getterminalwidth`, `setvariable`.
- `common.py`'s default handler is looked up at call time (was
  import-time — broke when the registered handler was set later).
- Unused imports pruned across the package.

### Phase 0: unblock the test suite

- `messageview.sql` references `engine.__member.approved` but
  `member.sql` never added the column — column added.
- `conftest.py` had duplicate fixtures; unit-only tests were
  cascade-skipped — fixtures deduplicated.
- `Makefile` had no `unit` / `integration` / `lint` targets — added.
- Stale root tests that couldn't pass — deleted (the
  `tests/feature_1/`, `tests/feature_2/`, `tests/unit/test_rendered_length.py`,
  and `tests/integration/test_end_to_end.py` directories / files).

### notify → message subsystem migration

The `notify` messaging subsystem was deleted. Only three functions
survive:

- `member.moniker_exists()` — validate moniker format and check DB
  existence
- `member.group_exists()` — check group membership in
  `engine.__notify_group`
- `member.get_group_members()` — recursive group expansion with
  cycle detection

Everything else described in `CHANGELOG_NOTIFY_MESSAGING.md` is
**gone**. The current spec for the surviving functions is in
`handbook/specs/member.md` "Recipient Validation & Group Management
(v1.0)".

### `member.py` → `member/` package refactor

The `member` module is now a package with `lib.py` and
`api/handler.py`. New WebSocket handlers for standalone channel and
member subsystems.

### Extract generic `SessionManager` into `bbsengine6.session` subpackage

Pulled out of `bbsengine6.net` into its own package. Bed's
`SessionRegistry` extends the new `bbsengine6.session.SessionManager`.

### bottombar FragmentRegistry

- New `bbsengine6.bottombar` module with `registry_for(name)`,
  `set_context_for`, `render_for`, `set_active_registry`,
  `reset_active_registry`, `_active_registry` ContextVar.
- `d9ac821`: per-connection plumbing (Phase 4a).
- `e2b6e38`: documentation for the pending empyre migration.

### CSS / template cleanup

- `c2a6c02`: reformat `topbar.scss`, clean up `pageheader` /
  `blurb` styles; remove `blurb` class from topbar/header; add
  `linklast` option to `youarehere`.

### Spec refresh

- `af5edc8`: specs updated to reference the new
  `bbsengine6.session` package structure.

### Console + backend updates

- `0c0641b`: console member add/edit tests.
- `96e586f`: backend adds `pre_dispatch` hook, contextvars role
  management, fix imports and DB references.
- `2c0f9dc`: backend adds `pgrole` to `checkclasses` and
  `SQL_FILE_OVERRIDES` for `pgrole` helpers in `checkfunctions`.
- `52364ed`: bank, pgrole, member, console updated for the pgrole
  migration and member package refactor.

### Bug fixes

- `ff0981a`: breadcrumbs no longer DB-lookups; title/URI derived
  from path segments.
- `21b30bb`: teos graceful fallback for missing paths instead of
  `PATHNOTFOUND`.
- `7a35bfc`: `PEAR_LOG_DEBUG` undefined constant error in
  `logentry()` resolved.
- `d803ad5`: router filters dotfiles/dotfolders from directory
  listings.
- `cc6fe0e`: router no longer prematurely HTML-encodes directory
  listing titles.
- `1499e75`: fix double-encoded HTML entities in sig titles.
- `3882368`: `sig-terse` hides body div when intro is empty.
- `d26c59b`: `database.make_dsn` tolerates missing `args.database*`
  via `getattr`.
- `87c8ab4`: `getch` relaxes notification poll cadence; comments
  aligned with reality.
- `98ce9d1`: `message.get_unread_count` degrades gracefully on
  missing `__message_recipient`.

---

For unimplemented features and future work, see [`TODO.md`](TODO.md).
