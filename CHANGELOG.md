# Changelog

All notable changes to `bbsengine6` are recorded here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

### smarty/function.teos: drop doubled TEOSURL prefix on `$uri`

`{teos uri=…}` no longer double-prefixes `TEOSURL`. The plugin now
respects a `title=` arg (added in the previous commit) without
re-emitting the URL prefix a second time. Operators that hard-coded
the doubled URL in their templates can drop one copy.

### smarty/function.teos: accept optional `title` arg

The `{teos}` plugin now accepts `title="…"` so callers can label the
breadcrumb independently of the link text.

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
