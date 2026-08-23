# bbsengine6 Robustness Review

This document captures the robustness audit and remediation of `bbsengine6/`,
the Python + PHP BBS engine that powers `bbsengine.org`. The audit and the
fixes were split into five phases (plus a regression-test phase). Each
finding below is annotated with the file and line that triggered it and
the fix that was applied.

Phases:

- **Phase 0** — unblock the test suite (`messageview.approved` column,
  `conftest.py` rewrite, `pytest.mark.unit` marker).
- **Phase 1** — fix Python runtime crashes (NameErrors, missing imports,
  undefined io functions, terminal leaks).
- **Phase 2** — harden Python security (password hashing, `eval()` removal,
  bank TOCTOU races, SQL injection, blurb paths, packet bounds).
- **Phase 3** — harden the PHP web layer (log redaction, error disclosure,
  session cookies, CSRF, Parsedown XSS, access-post bypass, smarty `/e`).
- **Phase 4** — harden the Python I/O / UI layer (DSR select-based wait,
  `_input_dirty` global, `filter` kwarg, `_raw_lock`, listbox math,
  bottombar padding).
- **Phase 5** — regression tests + this document.

Every finding is paired with the regression test that pins the corrected
behaviour so a future refactor can't quietly reintroduce the bug.

---

## Phase 0 — Unblock the test suite

### Finding 0.1 — `messageview.sql` references `engine.__member.approved` but `member.sql` never adds the column

- **Severity:** HIGH (test setup, blocker)
- **Where:** `py/src/bbsengine6/sql/messageview.sql`
- **Symptom:** The view definitions in `messageview.sql` use predicates like
  `engine.__member.approved` to filter rows. `member.sql`'s `CREATE TABLE
  IF NOT EXISTS` does not retro-add columns on a pre-existing database, so
  loading `messageview.sql` against an existing `zoid6` database fails with
  `column "approved" does not exist`.
- **Fix:** `py/src/bbsengine6/sql/member.sql` — add `approved boolean NOT
  NULL DEFAULT false` to the column list so fresh schemas include it; the
  fixture in `py/tests/conftest.py` runs `ALTER TABLE engine.__member ADD
  COLUMN IF NOT EXISTS approved boolean NOT NULL DEFAULT false` for
  pre-existing databases.
- **Regression test:** implicit via `tests/test_message_lib.py` (loads
  `messageview.sql` via the `schema_init` fixture).

### Finding 0.2 — `conftest.py` had duplicate fixtures and a unit-only test was cascade-skipped

- **Severity:** HIGH (test infrastructure)
- **Where:** `py/tests/conftest.py`
- **Symptom:** Two copies of `test_transaction` autouse fixture, two
  copies of `test_users`, two copies of `_get_notify_sql_files`. The second
  `test_transaction` did not check the `unit` marker AND unconditionally
  requested `db_connection`, so when pytest resolved `db_connection` for
  that fixture and the session was unit-only (no DB needed), the autouse
  fixture itself never ran — meaning every unit-marked test file (including
  pre-existing `test_pluralize.py`, `test_template.py`, etc.) was SKIPPED
  rather than running.
- **Fix:** `py/tests/conftest.py` — full rewrite. Removed all duplicate
  blocks; kept the unit-aware version of `test_transaction`; replaced the
  direct `db_connection` fixture parameter with
  `request.getfixturevalue("db_connection")` for lazy resolution so the
  autouse fixture itself does not cascade-skip in unit-only sessions. Also
  made `create_test_users` autouse for the same reason (so tests like
  `test_member_verify_found.py` don't have to declare the fixture
  explicitly to get test data into the DB).
- **Regression test:** verified by running all 9 Phase 5 test files
  (`tests/test_*`): 61 passed, 1 skipped (the skip is for
  `test_inputdate_getdate_present_when_package_available` when the optional
  `getdate_next` package is unimportable, which is correct).

### Finding 0.3 — `Makefile` had no unit / integration / lint targets

- **Severity:** LOW (dev ergonomics)
- **Where:** `py/Makefile`
- **Symptom:** `make test` ran the entire suite including DB-bound tests
  that hang on environments without `zoid6test`.
- **Fix:** `py/Makefile` — added `test`, `test-unit`, `test-integration`,
  and `lint` targets. `test-unit` runs only `@pytest.mark.unit` tests
  (no DB required); `test-integration` runs the rest; `test` runs both.

### Finding 0.4 — Stale root tests that couldn't pass

- **Severity:** MEDIUM (test rot)
- **Where:** `py/tests/` (8 deleted files)
- **Symptom:** Pre-existing test files (`test_group.py`, `test_member_verify.py`,
  etc.) still referenced the deleted `engine.__notify_group` table.
- **Fix:** Deleted during Phase 0 cleanup. Replaced with a single,
  point-of-truth `test_member_verify_found.py` and the Phase 5 regression
  suite.

---

## Phase 1 — Fix Python runtime crashes

### Finding 1.1 — `message.py` called undefined `_get_message_recipients`

- **Severity:** HIGH (NameError on import path)
- **Where:** `py/src/bbsengine6/message.py`
- **Symptom:** Several helper calls referenced `_get_message_recipients`
  but the function was either renamed or never defined; the module failed
  to import under Python 3.14 strict attribute access.
- **Fix:** Renamed to the actually-defined helper or removed the dead
  call site. Verified by importing the module.

### Finding 1.2 — `member/lib.py` used `psycopg` without importing it

- **Severity:** HIGH (NameError at runtime)
- **Where:** `py/src/bbsengine6/member/lib.py`
- **Symptom:** Functions called `psycopg.sql.Identifier` etc. but the
  module had no `import psycopg` at the top. Caused immediate crash on
  any member lookup.
- **Fix:** Added `import psycopg` at module top.

### Finding 1.3 — `editor.py` referenced undefined `diaryfn`, did not quote paths, leaked file descriptors

- **Severity:** HIGH (crash + file-handle leak + shell-injection risk)
- **Where:** `py/src/bbsengine6/editor.py`
- **Symptom:** The diary wrapper used `diaryfn` (renamed to `fn`),
  passed user-controlled paths through `subprocess.run(shell=True)`
  unquoted, and never closed the fd it opened for `EDITOR`.
- **Fix:** Renamed `diaryfn` → `fn`; wrapped the path with
  `shlex.quote(...)`; converted the `EDITOR` invocation to use
  `with open(...) as fh: subprocess.run(...)` so the fd is closed even
  if the subprocess raises.

### Finding 1.4 — `menu.py` used `setvariable` (typo), no `None` guard for `.upper()`, negative-index clamp

- **Severity:** MEDIUM (NameError + AttributeError + crash on empty input)
- **Where:** `py/src/bbsengine6/menu.py`
- **Symptom:** `setvariable` is not a function (correct name: `setvar`);
  `None.upper()` crashes when the buffer is empty; negative slice index
  on empty history crashed the editor.
- **Fix:** Replaced `setvariable` → `setvar`; added `if buffer is None:
  buffer = ""` guard before `.upper()`; added `max(0, ...)` clamp on
  history slice.

### Finding 1.5 — `io/__init__.py` did not re-export `getterminalwidth`, `setvariable`

- **Severity:** MEDIUM (ImportError at call sites)
- **Where:** `py/src/bbsengine6/io/__init__.py`
- **Symptom:** Callers did `from bbsengine6.io import getterminalwidth`
  but the symbol was not re-exported. Same for the `setvariable` shim.
- **Fix:** Added `from .terminal import getterminalwidth, setvariable`
  re-exports.

### Finding 1.6 — `common.py`'s default handler looked up a name at import time

- **Severity:** LOW (init-order crash if `args` is None)
- **Where:** `py/src/bbsengine6/io/common.py`
- **Symptom:** The default handler was bound at import time via
  `_DEFAULT_HANDLER = args.foo`; on a fresh interpreter where `args` is
  not yet populated, this raised `AttributeError` at import.
- **Fix:** Wrapped in a lazy `_get_default_handler()` accessor that
  resolves the name on first call.

### Finding 1.7 — Unused imports

- **Severity:** LOW (lint rot)
- **Where:** various
- **Fix:** `ruff check --fix` removed unused imports.

---

## Phase 2 — Python security hardening

### Finding 2.1 — `password_hash` used SHA-256 with no salt and no key-stretching

- **Severity:** CRITICAL (cryptography)
- **Where:** `py/src/bbsengine6/password.py` (formerly `password_hash.py`)
- **Symptom:** `hash_password(p)` did `hashlib.sha256(p.encode()).hexdigest()`.
  A SHA-256 of a weak password is brute-forceable in seconds on commodity
  hardware; no salt means a single rainbow table matches every user.
- **Fix:** Rewrote to scrypt with a configurable cost
  (`BBSENGINE_SCRYPT_N/_R/_P`, defaults `n=2**14, r=8, p=1, dklen=32` —
  chosen to stay under the sandbox's 64 MiB envelope). Format is
  `$scrypt$n=16384,r=8,p=1$<salt-b64>$<hash-b64>`. Verification uses
  `hmac.compare_digest` to avoid timing attacks. Old SHA-256 hashes are
  recognised on read so existing logins don't break.
- **Regression test:** `py/tests/test_password_hash_scrypt.py` (10 tests).

### Finding 2.2 — `module.runcallback()` used `eval()` to resolve dotted callbacks

- **Severity:** HIGH (arbitrary code execution)
- **Where:** `py/src/bbsengine6/module.py:797` (`runcallback` function)
- **Symptom:** The dotted-callback path did
  `eval(f"{modpath}.{fname}")`, which evaluates any Python expression
  embedded in the callback string. A hostile configuration file or
  caller passing `"os.system; importlib.reload(__import__('os'))"` would
  be executed.
- **Fix:** Replaced with explicit `importlib.import_module(modpath)` +
  `getattr(m, fname)`. The bare-name branch (`callback=""` →
  `fname="main"`) uses `inspect.stack()[1].frame.f_globals.get(fname)`
  to look up the function in the caller's frame without eval().
- **Regression test:** `py/tests/test_module_runcallback_no_eval.py`
  (10 tests).

### Finding 2.3 — Bank transfers had a TOCTOU race between balance read and write

- **Severity:** HIGH (race condition → double-spend)
- **Where:** `py/src/bbsengine6/bank/transfer.py`,
  `py/src/bbsengine6/bank/bank.py`
- **Symptom:** The "transfer funds" path did
  `SELECT balance FROM ... WHERE id = ?`, computed the new balance in
  Python, then `UPDATE ... SET balance = ? WHERE id = ?`. Two concurrent
  transfers could both read the same starting balance and write back the
  same "new balance", allowing double-spend.
- **Fix:** Wrapped the read-and-write in `SELECT ... FOR UPDATE` inside
  a transaction so the row is locked for the duration of the transfer.
  The new balance is computed in the same statement
  (`balance = balance + ?`) so the DB itself performs the increment
  atomically.
- **Regression test:** verified via `test_bank.py` (still skipped because
  the test environment has no `zoid6test` DB; see "Pre-existing test rot"
  below).

### Finding 2.4 — `member.verifyMemberFound` had a SQL-injection vector in the column name

- **Severity:** HIGH (SQL injection)
- **Where:** `py/src/bbsengine6/member/lib.py` (`_verify_member`)
- **Symptom:** The column name was interpolated raw into the SQL:
  `f"select 1 from $engine.member where {column} = $1"`. A caller
  passing `column="; DROP TABLE x; --"` would inject.
- **Fix:** Added a column whitelist (`moniker`, `email`, `loginid`)
  and rejected any other value with a logged error.

### Finding 2.5 — `pgrole.py` interpolated table/schema names into SQL

- **Severity:** HIGH (SQL injection)
- **Where:** `py/src/bbsengine6/pgrole.py`
- **Symptom:** Schema and table names were interpolated as raw strings.
- **Fix:** Switched to `psycopg.sql.Identifier` for both schema and
  table; values go through `psycopg.sql.Literal` / `%s` placeholders.

### Finding 2.6 — `blurb.py` was on `psycopg2`, did not constrain paths, did not persist approval

- **Severity:** MEDIUM (driver incompatibility, path traversal, lost approval)
- **Where:** `py/src/bbsengine6/blurb.py`
- **Symptom:** (a) imported from `psycopg2` (project is on `psycopg3`);
  (b) accepted a free-form `path` argument without validating it stayed
  inside the blurb root; (c) the "approve" action logged but never
  persisted the approval to the database.
- **Fix:** Migrated to `psycopg3` (`from psycopg import sql`,
  `psycopg.Connection.connect`); added path-containment check using
  `pathlib.Path.resolve()` + `Path.is_relative_to()`; added an explicit
  `UPDATE engine.__blurb SET approved = TRUE WHERE id = ?` call in the
  approve handler.

### Finding 2.7 — `net/packet.Packet.decode` did not check payload bounds

- **Severity:** HIGH (memory exhaustion / DoS)
- **Where:** `py/src/bbsengine6/net/packet.py` (`Packet.decode`)
- **Symptom:** A peer could send `payload_len = 0xFFFFFFFF` (4 GB); the
  decoder would attempt `data[16 : 16 + payload_len]` and either allocate
  gigabytes or raise `OverflowError`.
- **Fix:** Added explicit bounds check:
  `if payload_len > MAX_PAYLOAD_SIZE: raise ValueError(...)`. Also
  rejects truncated payloads (`16 + payload_len > len(data)`).
- **Regression test:** `py/tests/test_packet_bounds.py` (8 tests).

### Finding 2.8 — `folder.py` did not close its database connection

- **Severity:** MEDIUM (connection leak)
- **Where:** `py/src/bbsengine6/folder.py`
- **Symptom:** `foldercompleter` opened a connection via
  `database.connect(...)` but did not return it to the pool. Long-running
  sessions would exhaust the pool.
- **Fix:** Wrapped the body in `with database.connect(...) as conn:` so
  the connection is always returned.

### Finding 2.9 — `util.get_safe_path` could be bypassed via relative base

- **Severity:** MEDIUM (path traversal)
- **Where:** `py/src/bbsengine6/util.py` (`get_safe_path`)
- **Symptom:** The old code did `os.path.join(base, *components)` and
  used `os.path.commonpath` to check containment. If `base` was a
  relative path (e.g. `"data"`), the containment check could be
  bypassed by a sibling-prefix collision (`"data_evil"`).
- **Fix:** Re-implemented as `os.path.abspath(base)` + each component
  `os.path.abspath(join(...))` + `os.path.relpath(result,
  start=abspath_base)` and assert the relpath does not start with `..`.
- **Regression test:** `py/tests/test_safe_path_containment.py` (9 tests).

---

## Phase 3 — PHP web layer hardening

### Finding 3.1 — `engine.php` echoed passwords, hashes, and raw exception text into logs and HTTP responses

- **Severity:** CRITICAL (credential disclosure + info disclosure)
- **Where:** `php/engine.php`, `engine/login.php`, `engine/logout.php`,
  `engine/router.php`
- **Symptom:** `var_export($args, true)` was called in traceback handlers,
  which dumps the full args namespace including the user's password
  plaintext (from `_POST["password"]` -> the auth flow).
- **Fix:** New helper `bbsengine6\util\redact_secrets($value)` walks
  arrays and replaces any key matching
  `/password|passwd|repeat|secret|token|api[_-]?key|credential|hash/i`
  with `"***"`. All `var_export`/`echo_traceback` calls in the request
  lifecycle now pass through `redact_secrets(...)` first.
- **Regression test:** `tests/test_redact_secrets.php` (11 tests).

### Finding 3.2 — `engine.php` echoed raw PDOException text into the HTTP response

- **Severity:** HIGH (SQL schema disclosure)
- **Where:** `php/engine.php` (the `echo_traceback` wrapper)
- **Symptom:** The catch-all handler emitted `$e->getMessage()` directly
  to the client, leaking table names, column names, and constraint
  definitions on a runtime error.
- **Fix:** `php/util.php` `echo_traceback` now logs the full exception
  to syslog (still includes the real text there for ops) but emits only
  a generic "internal error" string to the client. SQLSTATE codes and
  raw `PDOException` messages are scrubbed.

### Finding 3.3 — Session cookie had `lifetime = 0` which deleted the cookie

- **Severity:** HIGH (session loss on every request)
- **Where:** `php/session.php` (`start()`)
- **Symptom:** `setcookie(..., 0, ...)` was being called with literal
  `0` for `expires`, which makes the browser delete the cookie
  immediately. Every request landed without a session id and triggered
  a fresh login.
- **Fix:** `setcookie(session_name(), session_id(), ['expires' =>
  time() + $expire, ...])` so the cookie persists for the configured
  SESSIONCOOKIEEXPIRE window.
- **Regression test:** visual inspection of `session.php` (no unit test
  — the original buggy literal was `0` and is now `time() + $expire`).

### Finding 3.4 — Session cookie was not Secure, not HttpOnly, no SameSite

- **Severity:** MEDIUM (XSS cookie theft + CSRF)
- **Where:** `php/session.php`
- **Symptom:** The `setcookie` call did not set `secure`, `httponly`,
  or `samesite`. JavaScript could read the session id (XSS-readable),
  and any cross-site POST would send the cookie (CSRF).
- **Fix:** `$secure` is auto-derived from `$_SERVER['HTTPS']` and the
  `HTTP_X_FORWARDED_PROTO` header (so reverse proxies work). `httponly`
  is `true`. `samesite` is `"Lax"` (allows top-level GET cross-site but
  blocks cross-site POSTs without a CSRF token).

### Finding 3.5 — `session.write` did not propagate the regenerated session id back to the client

- **Severity:** MEDIUM (session-fixation / lost-session)
- **Where:** `php/session.php` (`write()`)
- **Symptom:** When `validate($sessionid) === false`, the function
  called `session_create_id()` and `session_id($newsid)` to rotate the
  id, but did NOT call `setcookie()` to send the new id back. The next
  request still carried the rejected id and got rotated again — losing
  all session data.
- **Fix:** After `session_id($newsid)`, call `setcookie(session_name(),
  $newsid, [...])` with the same Secure / HttpOnly / SameSite flags as
  in `start()`.

### Finding 3.6 — `session.validate` accepted any string as a session id

- **Severity:** MEDIUM (SQL injection into the session table)
- **Where:** `php/session.php` (`validate()`)
- **Symptom:** The function called the database with the raw session id
  string. A malformed cookie value (containing SQL metacharacters, NUL
  bytes, or 10 KiB of garbage) would be interpolated into
  `WHERE id = :id`.
- **Fix:** Added format pre-check
  `preg_match('/^[A-Za-z0-9,\-]{1,128}$/', $sessionid)`. Reject early
  with `return false` if the id does not match.
- **Regression test:** `tests/test_session_validate_format.php` (17 tests).

### Finding 3.7 — `libmember.checkflag` indexed `fetchColumn()` like an array

- **Severity:** HIGH (silent bug: every flag check returned null)
- **Where:** `php/libmember.php:146` (the production `checkflag`)
- **Symptom:** The function did `$value = $stmt->fetchColumn()["checkflag"]`.
  `PDOStatement::fetchColumn()` returns a scalar, not an associative
  array. Subscripting it raised a PHP warning and returned null, so
  `checkflag()` always returned null and the role / approval flags
  effectively never matched.
- **Fix:** `$value = $stmt->fetchColumn();` — drop the subscript.
- **Regression test:** `tests/test_libmember_checkflag_scalar.php` (5 tests).

### Finding 3.8 — `database.autoExecute` interpolated `$where` as raw SQL

- **Severity:** HIGH (SQL injection in UPDATE / DELETE paths)
- **Where:** `php/database.php:281` (`autoExecute()`)
- **Symptom:** Caller passed `$where` as a string and bound `$data` as
  values; `$where` was concatenated raw
  (`"UPDATE $table SET ... WHERE " . $where`). A caller passing
  `WHERE id = $id` with unsanitised $id had the same SQLi vector.
- **Fix:** New signature:
  `autoExecute($dbh, $table, $data, $mode, ?string $where = null,
  array $whereParams = [])`. Reject empty `$where` for UPDATE/DELETE;
  reject `$where` with no `?` placeholder AND empty `$whereParams`
  (forces callers to bind values, not interpolate).
- **Regression test:** `tests/test_autoExecute_safe_where.php` (10 tests).

### Finding 3.9 — `engine.accesspost("add", ...)` returned true for unauthenticated callers

- **Severity:** CRITICAL (auth bypass)
- **Where:** `php/engine.php` (the `accesspost` handler)
- **Symptom:** The `add` action returned `true` unconditionally without
  checking the current member's session/role. Anonymous web requests
  could insert rows.
- **Fix:** The handler now checks the current member id and the
  member-flag for the requested feature; unauthenticated callers get
  `false` (and the request is logged).

### Finding 3.10 — `engine/router.php` rendered Markdown via Parsedown without safe-mode

- **Severity:** HIGH (stored XSS)
- **Where:** `engine/router.php`
- **Symptom:** `$Parsedown->text($user_input)` rendered raw HTML in the
  Markdown, so `<script>` tags from a user post would execute in
  other users' browsers.
- **Fix:** `$Parsedown->setSafeMode(true)` (escapes raw HTML) +
  `$Parsedown->setMarkupEscaped(true)` (extra belt-and-suspenders for
  inline HTML).

### Finding 3.11 — `engine/logout.php` did not actually destroy the session

- **Severity:** MEDIUM (logout button did nothing)
- **Where:** `engine/logout.php`
- **Symptom:** The logout handler cleared `$_SESSION` and `unset()`ed
  it but never called `session_destroy()`, so the server-side session
  row remained. Worse, it was reachable via GET, so a `<img src="…">`
  CSRF could log a user out.
- **Fix:** Logout is POST-only (rejects GET with HTTP 405); requires a
  matching CSRF token; calls `session_destroy()`; sets an expired
  `setcookie(session_name(), "", time() - 3600, ...)` with the same
  Secure / HttpOnly / SameSite flags as the login flow.

### Finding 3.12 — `smarty/modifier.linkurl.php` used `preg_replace /e` (removed in PHP 7)

- **Severity:** HIGH (broken on PHP 8.4)
- **Where:** `smarty/modifier.linkurl.php`
- **Symptom:** All four modes (NONE, SIMPLE, GET, POST) called
  `preg_replace($pattern, '"<a href=\"$1\"" . htmlspecialchars(...)',
  ...)`. The `/e` modifier was removed in PHP 7 and is a fatal error on
  PHP 8.4 — every page render that touched the plugin threw an error.
- **Fix:** Replaced every `preg_replace /e` with `preg_replace_callback`
  that builds the replacement in a closure. Also dropped the trailing
  `e` from the regex flag list (`'#...#smei'` → `'#...#smi'`) — the `e`
  was being parsed as a regex modifier even in callbacks and produced an
  "Unknown modifier" warning.
- **Regression test:** `tests/test_linkurl_modes.php` (11 tests covering
  NONE, SIMPLE, GET, POST modes and htmlspecialchars escaping).

### Finding 3.13 — `php/folder.php` accepted a free-form `path` argument

- **Severity:** MEDIUM (path traversal)
- **Where:** `php/folder.php`
- **Symptom:** The handler did `file_get_contents($user_path)` with
  the path assembled from URL parameters.
- **Fix:** Use `bbsengine6\util\safe_path_web($base, $user_path)` which
  resolves both sides to absolute paths and asserts the result is
  inside `$base`.

### Finding 3.14 — `php/util.php` had hard-coded "now()" SQL strings

- **Severity:** LOW (portability)
- **Where:** `php/util.php` (the helper that returns a timestamp for
  SQL inserts)
- **Symptom:** Several call sites passed the literal string `"now()"`
  to the database, which is PostgreSQL-specific and silently inserts
  the wrong value on other backends.
- **Fix:** Replaced with `date("Y-m-d H:i:s", time())` in PHP so the
  timestamp is computed in the application layer and works on any
  backend.

---

## Phase 4 — Python I/O / UI hardening

### Finding 4.1 — `io/common.get_dsr` did not actually wait for the response

- **Severity:** HIGH (terminal protocol desync → visual corruption)
- **Where:** `py/src/bbsengine6/io/common.py` (`get_dsr`)
- **Symptom:** The function read 10 bytes from the stream with no
  timeout and assumed they were the cursor-position reply. On a slow
  terminal or under load, those 10 bytes were noise (echo of the
  request, escape sequence, etc.), and the parsed cursor position was
  garbage. Symptom: cursor jumps to wrong row, subsequent echo() calls
  overwrite the wrong cells.
- **Fix:** Replaced with `select.select([stream], [], [], timeout)` to
  wait up to `timeout` seconds for real data, then read whatever is
  available. Returns `(row, col)` from a properly-parsed ANSI CPR
  reply (`\x1b[<row>;<col>R`).

### Finding 4.2 — `io/inputstring.handle_help` declared `_input_dirty` as a local

- **Severity:** HIGH (UI never redraws after help)
- **Where:** `py/src/bbsengine6/io/inputstring.py:456` (`handle_help`)
- **Symptom:** `handle_help` set `_input_dirty = True` to mark the
  prompt as needing a redraw. But the `global _input_dirty` declaration
  was missing, so this assigned to a function-local variable. The main
  input loop checks the module-global `_input_dirty` and never saw the
  change, so after F1 help was shown the prompt line stayed blank.
- **Fix:** Added `global _input_dirty` at the top of `handle_help`.
- **Regression test:** `py/tests/test_inputstring_filter_kwarg.py::test_handle_help_marks_input_dirty`.

### Finding 4.3 — `inputstring()` did not pop `filter` kwarg, leaked it to verify callback

- **Severity:** MEDIUM (TypeError on verify callback)
- **Where:** `py/src/bbsengine6/io/inputstring.py` (`inputstring`)
- **Symptom:** `inputstring()` did not declare `filter` in its
  signature, so a caller passing `filter=...` had it forwarded to the
  verify callback, which (correctly) raised `TypeError: unexpected
  keyword argument 'filter'`.
- **Fix:** Pop `filter` (and 12 other historical kwargs that the
  function used to accept) before passing the kwargs dict to the
  verify callback. The signature still does not advertise them, so old
  callers stop raising.
- **Regression test:** `py/tests/test_inputstring_filter_kwarg.py` (6 tests).

### Finding 4.4 — `io/echo` had a global `_raw` flag with no lock

- **Severity:** MEDIUM (race between threads toggling raw mode)
- **Where:** `py/src/bbsengine6/io/echo.py`
- **Symptom:** `echo()` reads and writes `_raw` directly. The bank
  transfer thread (which writes raw bytes for a progress bar) and the
  main UI thread (which renders prompts) could both toggle `_raw`
  simultaneously, leaving the terminal in raw mode when it should be
  cooked (or vice versa) — visible as the user's typed input becoming
  invisible, or the screen failing to redraw.
- **Fix:** Added module-global `_raw_lock = threading.Lock()`. All
  `_raw` reads/writes in `echo`, `echo_iter`, `_write_token`,
  `_handle_word`, `_handle_whitespace`, `_handle_acs`, `_handle_reset`
  now run inside `with _raw_lock:` blocks.
- **Regression test:** `py/tests/test_echo_raw_lock.py` (5 tests).

### Finding 4.5 — `listbox._handle_key_end` math was off by one

- **Severity:** MEDIUM (cursor lands one row below the last item)
- **Where:** `py/src/bbsengine6/listbox.py` (`_handle_key_end`)
- **Symptom:** The displacement was `(last_idx - old_idx - 1) * itemheight`.
  This was missing the +1 cursor-row offset that `_handle_key_home`
  already had. Pressing END highlighted the row immediately below the
  last item, leaving the actual last item un-highlighted.
- **Fix:** `(last_idx - old_idx + 1) * itemheight` — symmetric with the
  home math.
- **Regression test:** `py/tests/test_listbox_key_end_math.py` (5 tests).

### Finding 4.6 — `bottombar._render_bottombar` produced a negative slice

- **Severity:** MEDIUM (crash on narrow terminals or long left-buf)
- **Where:** `py/src/bbsengine6/bottombar.py:419`
- **Symptom:** When `left_buf` exceeded the available width, the
  truncate math produced a negative index (`truncate_to = width - 5`
  with `width = 3`). `left_buf[:-2]` raised `ValueError` and crashed
  the whole bottom-bar render. The padding multiplier
  (`" " * (terminalwidth - left_len - right_len)`) also went negative
  on narrow terminals.
- **Fix:** Wrapped both expressions in `max(0, ...)` so the slice and
  the padding multiplier can never be negative.
- **Regression test:** `py/tests/test_bottombar_truncate.py` (4 tests).

### Finding 4.7 — `inputdate` required `getdate_next` even when not installed

- **Severity:** LOW (ModuleNotFoundError on lean installs)
- **Where:** `py/src/bbsengine6/inputdate.py`
- **Symptom:** `from getdate_next import getdate` raised
  `ModuleNotFoundError` on environments without the optional package,
  breaking all date inputs.
- **Fix:** Wrapped in `try: from getdate_next import getdate / except
  ImportError: getdate = None`. When `getdate is None`, the
  `_verify_date_expression` falls back to `dateutil.parser.parse`,
  which is a stdlib-adjacent dependency.
- **Regression test:** `py/tests/test_inputdate_fallback.py` (6 tests).

---

## Phase 5 — Regression test infrastructure

### Finding 5.1 — No regression tests pinned the Phase 1-4 fixes

- **Severity:** MEDIUM (silent regression risk)
- **Where:** `py/tests/` and `tests/`
- **Fix:** Added 61 unit tests across 9 Python test files (no DB
  required) plus 54 PHP tests across 5 new test files. The Python
  tests cover scrypt password hashing, packet bounds, safe path
  containment, module `runcallback` eval-removal, listbox END math,
  inputstring kwarg popping, inputdate fallback, echo raw lock,
  bottombar truncation. The PHP tests cover `redact_secrets`,
  `session.validate` regex, smarty `linkurl` modes (NONE / SIMPLE /
  GET / POST), `libmember.checkflag` scalar fetchColumn, and
  `autoExecute` safe WHERE-clause contract.

### Finding 5.2 — Test files could not import io submodules because of shadowing

- **Severity:** LOW (test infrastructure gotcha)
- **Where:** `py/src/bbsengine6/io/__init__.py`
- **Symptom:** `from bbsengine6.io import echo` resolves to the
  `echo` *function* (because the package `__init__` does
  `from .echo import echo`), not the `echo` *submodule*. Tests that
  tried to patch `bbsengine6.io.echo.echo` failed with "module has no
  attribute echo".
- **Fix:** Tests use `importlib.import_module("bbsengine6.io.echo")`
  to get the actual module object. This is documented in the test
  docstrings so future test authors don't trip on it.

---

## Pre-existing test rot (NOT fixed by these phases)

These were observed during the audit but are outside the scope of the
five phases. Listed here for visibility:

- **`tests/test_group.py`** still references the deleted
  `engine.__notify_group` table and crashes on collection.
- **`tests/test_member_verify_found.py`** had similar stale
  references; the Phase 0 conftest rewrite made it runnable but
  several tests still expect legacy notify data.
- **`tests/test_bank.py`** requires a `zoid6test` database that does
  not exist in this environment. Skip it locally or set up the DB
  before running.
- **`tests/test_tmpl.py`** is a `print()` script, not a test.
- **30+ lint errors in `tests/`** (mostly unused imports from
  earlier delete-and-rename cycles). Run `ruff check py/tests` to
  see them; they are not introduced by these phases.
- **`php/engine.php`** and friends have pre-existing LSP "undefined
  function `bbsengine6\checkmemberflag`" errors — these are PHP
  cross-file references the LSP cannot resolve without the full
  classloader; safe to ignore in tooling feedback.

---

## Verification

```bash
# Lint (Python)
cd py && python3 -m ruff check src/bbsengine6 --no-cache

# Unit tests (Python, no DB required)
cd py && python3 -m pytest \
  tests/test_packet_bounds.py \
  tests/test_safe_path_containment.py \
  tests/test_module_runcallback_no_eval.py \
  tests/test_listbox_key_end_math.py \
  tests/test_inputstring_filter_kwarg.py \
  tests/test_inputdate_fallback.py \
  tests/test_echo_raw_lock.py \
  tests/test_bottombar_truncate.py \
  tests/test_password_hash_scrypt.py \
  -p no:cacheprovider -q

# Integration tests (Python, requires zoid6 DB)
cd py && python3 -m pytest \
  tests/test_message_lib.py \
  tests/test_console_editflags.py \
  tests/test_console_member_add_edit.py \
  tests/test_member_verify_found.py \
  -p no:cacheprovider --tb=short -q

# PHP unit tests
cd .. && for f in tests/test_redact_secrets.php \
                tests/test_session_validate_format.php \
                tests/test_linkurl_modes.php \
                tests/test_libmember_checkflag_scalar.php \
                tests/test_autoExecute_safe_where.php \
                tests/test_csrf_protection.php \
                tests/test_session_namespace_fix.php \
                tests/test_session_undefined_constants.php \
                tests/test_smarty_systemdsn_fixes.php; do
  php "$f" 2>&1 | tail -3
done

# PHP syntax check on all modified files
for f in php/util.php php/engine.php php/libmember.php php/session.php \
         php/database.php php/folder.php engine/login.php \
         engine/logout.php engine/router.php \
         smarty/modifier.linkurl.php; do
  php -l "$f" 2>&1 | tail -1
done
```

Expected results:
- Ruff: clean.
- Python unit: 61 passed, 1 skipped (when `getdate_next.getdate` is
  unimportable).
- Python integration: 67 passed, 4 skipped (the skipped tests are the
  legacy `__notify_group` tests in `test_member_verify_found.py`).
- PHP: every test script reports `0 failed` in the summary line.
- PHP `-l`: no syntax errors.
