# bbsengine6.auth — BBS auth backend for IMAP / PAM

`bbsengine6.auth` is the BBS auth backend for IMAP and PAM. It exposes:

- **`bbsengine6.auth.verify.verify_member(username, password)`** — the
  single source of truth for the BBS auth decision. Returns
  `(ok, outcome)` where `outcome` is a short canonical string
  (`ok`, `no-user`, `not-approved`, `mailbox-disabled`, `sasl-expired`,
  `wrong-password`, `db-error`, `mail-no-user`). Read-only: opens a
  `BEGIN READ ONLY` transaction, never writes.

- **`bbsengine6-auth-checkpassword`** — the
  [Dovecot checkpassword protocol](https://doc.dovecot.org/configuration_manual/authentication/checkpassword/)
  entry point. Reads `<password>\0<userinfo>\0` from stdin; reads the
  username from `AUTH_USER` (Dovecot sets it). On success prints the
  userdb-style lines (`home=`, `mail=`, `uid=`, `gid=`, plus their
  `userdb_*` mirrors) and exits 0. On failure prints nothing, exits 1.
  On DB error exits 2 (Dovecot treats as transient).

- **`bbsengine6-auth-pam`** — the `pam_exec.so` helper. Reads
  `PAM_USER` and `PAM_AUTHTOK` from the environment (the latter
  requires `expose_authtok` on the rule line). On `PAM_TYPE=account`
  passes through with exit 0 (the BBS gate is enforced in `auth`).
  On auth success exit 0; on auth failure exit 1; on DB error exit 2.

## Dispatch

`verify_member` dispatches on `@` in the username:

- `alice` (no `@`) → **per-user path**. Looks up
  `engine.__member.password` (bcrypt), checks `approved = true` and
  `accountexpires IS NULL OR > now()`.
- `alice@bbsengine.org` (with `@`) → **per-mailbox path**. Looks up
  `postoffice.mailbox_password` (bcrypt / crypt) joined to
  `engine.__member` and `postoffice.mailbox`, checks the same gate
  plus `mailbox_password.enabled` and `mailbox.enabled`.

The dispatch is what makes a single verifier serve both Dovecot (per-
user, where the BBS web password is the credential) and Cyrus (per-
mailbox, where the per-mailbox password set via the postoffice TUI is
the credential).

## Authorization gate

Every successful auth requires:

1. `engine.__member.approved = true` (member is approved; the default
   is `false` for new members).
2. `engine.__member.accountexpires IS NULL OR > now()` (account not
   expired; `NULL` means never expires).
3. The relevant password column verifies against the supplied
   plaintext via `crypt.crypt()` (handles `$1$`, `$5$`, `$6$`, and
   `$2[aby]$` bcrypt in one call) with a `bcrypt.checkpw` fallback.

For the per-mailbox path, additionally:
4. `postoffice.mailbox_password.enabled = true`.
5. `postoffice.mailbox.enabled = true`.

The migration `sql/008_add_member_accountexpires.sql` adds the
`accountexpires` column. The canonical schema
`bbsengine6/py/src/bbsengine6/sql/member.sql` includes it for fresh
builds.

## Algorithm coverage

`crypt.crypt(plaintext, stored_hash)` (stdlib, glibc) handles every
`crypt(3)` variant glibc supports:

- `$1$` — MD5-crypt (legacy, BBS web 2011-2014 era).
- `$5$` — SHA-256-crypt.
- `$6$` — SHA-512-crypt (postoffice.sasl_password default).
- `$2a$ / $2b$ / $2y$` — bcrypt (BBS web login and
  postoffice.mailbox_password default).

If `crypt.crypt` returns `None` (algorithm not in this glibc), the
verifier falls back to `bcrypt.checkpw` for bcrypt hashes. This is
defensive — Jammy's glibc 2.35 handles all four `$2$` prefixes.

## Read-only enforcement

`verify_member` opens a Postgres transaction with `BEGIN READ ONLY`.
Any future bug that tries to `INSERT` / `UPDATE` / `DELETE` during
auth will get `psycopg.errors.ReadOnlySqlTransaction` from Postgres
and the test `test_read_only_transaction_blocks_writes` pins this
contract.

## Security model: `pam_exec.so` env-var exposure

The `bbsengine6-auth-pam` helper runs as a child of `pam_exec.so`,
which forks it with the password in the `PAM_AUTHTOK` environment
variable. This is the documented behavior of `pam_exec.so
expose_authtok`; the alternative (a real `.so` in C) is out of scope
per the operator decision to keep the auth backend pure-Python.

Mitigations applied to the helper:

1. **Immediate scrub**: `os.environ.pop("PAM_AUTHTOK")` is called
   microseconds after the read. After this line, no code in the
   process can see the value from the env.

2. **No password in logs**: the helper's outcome log line includes
   the user and an outcome class (e.g. `user=alice outcome=ok`) but
   never the password. The `BBSENGINE6_AUTH_LOG=DEBUG` setting does
   not change this — `DEBUG` logs the timing, not the password.

3. **Read-only DB transaction**: even if a SQL-injection-style
   username somehow subverted the parameterized query, the
   transaction is `BEGIN READ ONLY` and Postgres rejects writes.

Threat model: an attacker who can read `/proc/<pid>/environ` of a
root-owned process on merlin or falcon already has root on the host.
The env-var exposure does not increase the attack surface
meaningfully beyond "operator has root on merlin or falcon."

The `bbsengine6-auth-checkpassword` entry point (Dovecot) does
**not** have this exposure: the password is read from stdin (the
Dovecot checkpassword protocol) and the script's env does not
contain it. The user-supplied `userinfo` field in stdin is
**ignored** — the username always comes from `AUTH_USER` which
Dovecot sets.

## DSN resolution

The verifier uses `bbsengine6.database.getpool()` to obtain a
connection pool. The DSN chain is:

1. `args.databasename` / `args.databasehost` / `args.databaseport` /
   `args.databaseuser` (explicit override at the call site).
2. `BBSENGINE6_DBNAME` / `BBSENGINE6_DBHOST` / `BBSENGINE6_DBPORT` /
   `BBSENGINE6_DBUSER` / `BBSENGINE6_DBPASSWORD` env vars.
3. The DSN chain's defaults: `localhost:5432`, no user.

The `bbsengine6-auth-checkpassword` and `bbsengine6-auth-pam`
entry points use the env-var chain (option 2) because they have no
caller-supplied `args`. The DSN is typically set in the operator's
`/etc/postoffice/mcfeely-authd.conf` (or equivalent) and inherited
from the systemd unit's `EnvironmentFile=`.

## Test matrix

`bbsengine6/auth/test_auth.py`:

Unit tests (no DB required):
- `test_verify_hash_bcrypt` — `$2b$06$...` round-trip.
- `test_verify_hash_md5_crypt` — `$1$...` round-trip.
- `test_verify_hash_sha512_crypt` — `$6$...` round-trip.
- `test_verify_hash_empty_inputs` — edge cases.
- `test_dispatch_per_user_no_at_sign` — `_dispatch()` unit.
- `test_empty_inputs` — `verify_member("")` / `verify_member(..., "")`.

Integration tests (require a DB with the migration applied):
- `test_no_member_returns_no_user`
- `test_approved_with_bcrypt_returns_ok`
- `test_approved_with_wrong_password_returns_wrong`
- `test_not_approved_returns_not_approved`
- `test_accountexpires_past_returns_expired`
- `test_accountexpires_future_returns_ok`
- `test_accountexpires_null_returns_ok`
- `test_null_password_column_rejects`
- `test_md5_crypt_hash_returns_ok`
- `test_sha512_crypt_hash_returns_ok`
- `test_read_only_transaction_blocks_writes` — pins the read-only
  contract via direct psycopg probe.

Dovecot protocol tests (planned for a follow-up): the test
harness spawns the entry point as a subprocess and pipes
`pw\0user\0\n` on stdin.

PAM helper tests (planned for a follow-up): the test harness sets
`PAM_USER` / `PAM_AUTHTOK` env vars and asserts the exit code
matches the expected outcome, and asserts the env-var scrub
(reads `os.environ` after the call and asserts `PAM_AUTHTOK` is
gone).

## Operator deployment

The Makefile target `install-bbsengine6-auth-helper` in
`bbsengine6/Makefile` (Phase 4) installs both entry points to a
system venv at `/opt/bbsengine6-auth-venv/` and symlinks them into
`/usr/local/bin/`. The PAM service file `/etc/pam.d/bbsengine6`
(Phase 5) wires `pam_exec.so` to `bbsengine6-auth-pam` for the
auxprop-pam and Dovecot `auth-system.conf.ext` paths.
