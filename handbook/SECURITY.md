# Security

> Status: canonical. Updated 2026-09-04.
> Full audit: [`../ROBUSTNESS_REVIEW.md`](../ROBUSTNESS_REVIEW.md)
> (Phase 0-5, 43 findings, 61 Python + 54 PHP regression tests).

## Overview

bbsengine6's security posture is documented in two layers:

1. **The Phase 0-5 hardening audit**
   ([`../ROBUSTNESS_REVIEW.md`](../ROBUSTNESS_REVIEW.md)) — 43
   findings across Python runtime, Python security, the PHP web
   layer, and the Python I/O / UI layer. Every finding is paired
   with the file/line that triggered it, the fix that was applied,
   and a regression test. This is the authoritative record.
2. **This document** — a high-level summary, plus the security
   guarantees of the canonical subsystems (session, CSRF, ident
   auth, router).

If a security detail is in dispute, the audit wins.

## Phase 2 — Python security (summary)

The Python half of the audit (Findings 2.1 – 2.9) covered nine
classes of issue. Highlights:

- **Password hashing migrated from SHA-256 to scrypt** (Finding
  2.1). SHA-256 with no salt was brute-forceable in seconds on
  commodity hardware. The new format is
  `$scrypt$n=<N>,r=<R>,p=<P>$<salt-b64>$<hash-b64>` with
  `BBSENGINE_SCRYPT_N/_R/_P` defaults (`n=2**14, r=8, p=1`) chosen
  to stay under the sandbox's 64 MiB envelope. Verification uses
  `hmac.compare_digest`. Legacy SHA-256 hashes are still
  recognised on read. 10 regression tests in
  `py/tests/test_password_hash_scrypt.py`.
- **`module.runcallback()` no longer calls `eval()`** (Finding
  2.2). The dotted-callback path used  `eval(f"{modpath}.{fname}")`
  — replaced with explicit
  `importlib.import_module(...)` + `getattr(...)`. A hostile
  configuration file could no longer execute arbitrary Python.
- **Bank transfers wrapped in `SELECT ... FOR UPDATE`** (Finding
  2.3). The old code did a balance read in Python, computed the new
  balance, and wrote it back — a TOCTOU race that let two
  concurrent transfers double-spend. The fix performs the
  increment inside the locked statement
  (`balance = balance + ?`).
- **`util.get_safe_path` rewrites** (Finding 2.9). The old
  `os.path.commonpath` containment check could be bypassed when the
  base was a relative path (sibling-prefix collision). The fix
  resolves both sides with `os.path.abspath(...)` and asserts the
  relative path doesn't start with `..`. 9 regression tests.
- **`Packet.decode` bounds check** (Finding 2.7). A peer could send
  `payload_len = 0xFFFFFFFF` (4 GB) and the decoder would either
  allocate gigabytes or raise `OverflowError`. Now rejects payloads
  larger than `MAX_PAYLOAD_SIZE` and truncated payloads.
- **`blurb.py` path containment + `psycopg3` migration** (Finding
  2.6). Path is checked with `pathlib.Path.resolve()` +
  `Path.is_relative_to()`. Approval now persists to the DB
  (`UPDATE engine.__blurb SET approved = TRUE`).
- **`pgrole.py` uses `psycopg.sql.Identifier`** (Finding 2.5).
  Schema and table names are no longer interpolated raw.
- **`verifyMemberFound` whitelist** (Finding 2.4). The column name
  was interpolated raw into `WHERE <column> = ?`; now restricted to
  `moniker`, `email`, `loginid`.
- **`folder.py` returns DB connection to the pool** (Finding 2.8).

The full Python side is in
[`../ROBUSTNESS_REVIEW.md`](../ROBUSTNESS_REVIEW.md#phase-2--python-security-hardening).

## Phase 3 — PHP web layer (summary)

The PHP half of the audit (Findings 3.1 – 3.14) covered fourteen
classes of issue. Highlights:

- **`redact_secrets()` everywhere** (Finding 3.1). `engine.php` had
  `var_export($args, true)` in traceback handlers, dumping
  plaintext passwords from `$_POST["password"]` into logs and HTTP
  responses. The new helper walks arrays and replaces any key
  matching `/password|passwd|repeat|secret|token|api[_-]?key|credential|hash/i`
  with `"***"`. All `var_export` / `echo_traceback` calls now go
  through it. 11 regression tests.
- **No raw `PDOException` to clients** (Finding 3.2).
  `echo_traceback` logs the full exception to syslog and emits a
  generic error to the client — SQLSTATE codes and raw messages
  are scrubbed.
- **Session cookie hardening** (Findings 3.3 – 3.6):
  - `lifetime = 0` was deleted from the cookie on every request
    (literal `0` made the browser expire it immediately). Now
    `time() + $expire`.
  - `Secure` auto-derived from `$_SERVER['HTTPS']` and
    `HTTP_X_FORWARDED_PROTO` (works behind reverse proxies).
  - `HttpOnly = true`, `SameSite = Lax`.
  - Session id is rotated after validation; the new id is sent
    back via `setcookie()` (otherwise the rotation was lost on the
    next request).
  - Session id format is checked against
    `^[A-Za-z0-9,\-]{1,128}$` before DB lookup.
- **`autoExecute` safe WHERE clause** (Finding 3.8). Old signature
  accepted a raw `$where` string concatenated into the SQL. New
  signature: `autoExecute($dbh, $table, $data, $mode, ?string $where
  = null, array $whereParams = [])`. Empty `$where` is rejected for
  UPDATE/DELETE; callers are forced to bind values.
- **`libmember.checkflag` scalar fix** (Finding 3.7). Old code
  subscripted `$stmt->fetchColumn()` like an array and always
  returned null — every flag check silently failed. Now fetches the
  scalar.
- **`accesspost("add", ...)` auth check** (Finding 3.9). Unauthed
  callers could insert rows. Now requires a matching member id
  and feature flag.
- **Parsedown safe mode** (Finding 3.10). `engine/router.php` was
  rendering user Markdown with raw HTML enabled (`<script>` from a
  post would execute). Now `$Parsedown->setSafeMode(true)` +
  `setMarkupEscaped(true)`.
- **Logout actually destroys the session** (Finding 3.11). Old
  logout cleared `$_SESSION` and unset it but never called
  `session_destroy()`; reachable via GET (CSRF). Now POST-only,
  requires a CSRF token, calls `session_destroy()`, sets an
  expired `setcookie(...)`.
- **`smarty/modifier.linkurl` `preg_replace /e` removed**
  (Finding 3.12). The `/e` modifier was removed in PHP 7 and is a
  fatal error on PHP 8.4 — every page render broke. Now uses
  `preg_replace_callback`. 11 regression tests across the NONE,
  SIMPLE, GET, POST modes.
- **`php/folder.php` safe path** (Finding 3.13). User-supplied path
  is now validated with `bbsengine6\util\safe_path_web`.
- **Portable SQL timestamps** (Finding 3.14). The literal `"now()"`
  was PostgreSQL-specific; replaced with
  `date("Y-m-d H:i:s", time())` in PHP.

The full PHP side is in
[`../ROBUSTNESS_REVIEW.md`](../ROBUSTNESS_REVIEW.md#phase-3--php-web-layer-hardening).

## CSRF

The `csrfCheckRequest()` helper (`php/util.php`) is the single
entry point for state-changing requests. Default behavior is
backward-compatible (GET requests without a token are accepted).
For new endpoints, pass `requireOnGet: true`:

```php
csrfCheckRequest(requireOnGet: true);
```

The consolidated CSRF doc — token format, helper usage, every
endpoint that requires a token — lives at
[./csrf/README.md](./csrf/README.md).

## Session and authorization

The PHP session cookie is `Secure`, `HttpOnly`, `SameSite=Lax`. The
session id is format-checked before any DB lookup. Session
rotation on validation failure sends the new id back to the
client.

For the WebSocket / TUI auth flow (the `auth → bank` request
authorization model), see [./specs/auth-bank.md](./specs/auth-bank.md).
For the per-member PostgreSQL `ident` auth (every approved member
gets a `l_<loginid>` PG role), see [./specs/pg-ident-auth.md](./specs/pg-ident-auth.md).

## Router path safety

`engine/router.php` validates every user-supplied URI through
`bbsengine6\util\safe_path_web()` before any filesystem access. A
path traversal attempt returns 404. See [./ROUTER.md](./ROUTER.md)
for the full handler chain.

## Regression tests

The audit shipped 61 Python + 54 PHP regression tests pinning every
fix. The full test inventory is in
[`../ROBUSTNESS_REVIEW.md`](../ROBUSTNESS_REVIEW.md#phase-5--regression-test-infrastructure)
and [`../SPEC.md`](../SPEC.md#8-test-layout). Run them locally:

```bash
# Python unit tests (no DB)
cd py && python -m pytest tests/test_*.py -p no:cacheprovider -q

# PHP regression tests
cd .. && for f in tests/test_*.php; do php "$f" 2>&1 | tail -3; done

# Lint
cd py && python -m ruff check src/bbsengine6 --no-cache
```

## Reporting vulnerabilities

Open an issue on the project tracker. For sensitive disclosures,
contact the maintainers directly.
