# Changelog

All notable changes to `bbsengine6` are recorded here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
