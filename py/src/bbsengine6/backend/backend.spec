# bbsengine6.backend Specification

## Overview

`bbsengine6.backend` is the bootstrap/initialization subsystem of the
BBS engine. It runs two ordered stages (`stage_zero` against the
`postgres` admin database, then `stage_one` against the target
database) to verify and create the schemas, roles, extensions,
classes (tables/views), functions, and security markers that the
running engine needs. Every module exposes the same four-call
contract consumed by the top-level `module.runmodule` dispatcher
(`init`, `buildargs`, `access`, `main`).

All modules in this package assume `psycopg`-style connections and
expect either a `conn=` (long-lived, autocommit-off) or a `pool=`
keyword argument. Output is via `bbsengine6.io.echo` with the
`{var:labelcolor}`, `{var:valuecolor}`, `{level.ok}`, and
`{level.fail}` formatters. All status output ends in a horizontal
rule emitted by `lib.hr(failcount)` whose color reflects success.

## Module Discovery Contract

Every submodule MUST expose the following four callables (the
package is invoked exclusively through `bbsengine6.module.runmodule`):

| Callable    | Signature                       | Returns          | Purpose |
|-------------|---------------------------------|------------------|---------|
| `init`      | `(args, **kwargs) -> bool`      | `bool`           | One-time module setup. All current modules return `True`. |
| `buildargs` | `(args, **kwargs)`              | `None` or `args` | Per-invocation arg adjustment. Most modules delegate to `lib.buildargs`. |
| `access`    | `(args, op, **kwargs) -> bool`  | `bool`           | Authorization gate. Most modules delegate to `lib.issysop`; the few public checks return `True`. |
| `main`      | `(args, **kwargs) -> bool`      | `bool`           | The actual work. `True` = success, `False` = failure. |

Calling any other function is undefined; only `main`, `init`,
`buildargs`, and `access` are routed by the dispatcher.

## `lib.py` - Shared Helpers

`bbsengine6.backend.lib` is the internal support library. It
contains no top-level side effects beyond one `util.logentry` call
that records the in-use status of `{level.fail}` (see "Historical
Notes" below).

### `buildargs(args, **kwargs)`

Returns `None`. No-op shim; the dispatcher tolerates a `None`
return.

### `runmodule(args, submodule, **kwargs)`

Thin wrapper around `bbsengine6.module.runmodule` that prefixes
`bbsengine6.backend.` onto `submodule` before dispatch. This is the
only way `stage_zero`/`stage_one` invoke their child modules.

### `setbottombar(args, left, **kwargs)`

Sets the screen bottom bar. The right-hand side reads `con` plus
optional ` | debug` (when `args.debug` is `True`) plus optional
` | F1: Help` (when called with `help=True`). Delegates to
`bbsengine6.screen.setbottombar`.

### Module Runners

Each is a one-line `runmodule` shim used as a stable, documented
entry point:

| Function                | Routed module            |
|-------------------------|--------------------------|
| `checkroles`            | `bbsengine6.backend.checkroles` |
| `checkextensions`       | `bbsengine6.backend.checkextensions` |
| `checkdatabase`         | `bbsengine6.backend.checkdatabase` |
| `checkcreatedb`         | `bbsengine6.backend.checkcreatedb` |
| `checksuperuser`        | `bbsengine6.backend.checksuperuser` |
| `createdatabase`        | `bbsengine6.backend.database` |
| `checkfunctions`        | `bbsengine6.backend.checkfunctions` |
| `checkmemberflag`       | `bbsengine6.backend.checkmemberflag` |
| `checkmessage`          | `bbsengine6.backend.checkmessage` |
| `checkwebserverrole`    | `bbsengine6.backend.checkwebserverrole` |
| `checkbank`             | `bbsengine6.backend.checkbank` |

### `ok()` / `fail()`

Status emitters used by per-row checks:

- `ok()` prints `{{level.ok}}  ok  {{/all}}`.
- `fail()` prints `{{level.fail}} fail {{/all}}`.

`{level.fail}` is referenced from `io/specs/echo_commands.spec`
(via commit `7115e77`) and is in live use by `checkdatabase`,
`checkroles`, `checkwebserverrole`, `checkmemberflag`, `checksuperuser`,
and `checkbank`. Any future removal of `{level.fail}` MUST also remove
`lib.fail()` and migrate those callers to `io.echo(level="error")`
first.

### `hr(failcount: int = 0) -> None`

Emits a horizontal rule via `bbsengine6.util.hr`. Color is
`{boxcolor}` on success (failcount==0) and `{/all}{red}` on
failure. Every bootstrap `main()` that accumulates `failcount`
ends with one of these.

### `retry_on_transient(fn, *, attempts=3, backoff_seconds=0.1, retry_on=(...))`

Bounded retry wrapper for the DDL import path. `fn` is invoked up
to `attempts` times; on a `psycopg.errors.LockNotAvailable` or
`psycopg.errors.DeadlockDetected` it sleeps `backoff_seconds * (i+1)`
(seconds, linear) and retries. The final exception is re-raised if
all attempts fail. `fn` MUST NOT commit or release savepoints; the
caller owns the transaction.

`retry_on` is a tuple of **string** class names looked up lazily in
`psycopg.errors` at call time. This avoids `import psycopg` at
module load (a layering violation for `backend.lib`). If a name
does not exist in the imported module it is silently skipped.

### `_sanitize_sp(name: str, prefix: str = "") -> str`

Builds a savepoint identifier: `"sp_" + prefix + <sanitized>`. The
sanitized form keeps alphanumerics and replaces everything else
with `_`. Result is truncated to 60 characters. Used by the
savepoint-wrapped modules (see "Savepoint Protocol" below).

### `_ensure_autocommit_off(conn) -> None`

Defensively forces `conn.autocommit = False` only when:

1. The connection is currently in `autocommit=True` mode, AND
2. `pgconn.transaction_status` is `psycopg.pq.TransactionStatus.IDLE`.

In every other state (already `autocommit=False`, `INTRANS`,
`INERROR`, or status-lookup failure) it is a no-op. The reason:
psycopg raises `ProgrammingError` if `autocommit` is flipped while
the conn is `INTRANS`, and the long-lived outer conn passed to
the savepoint modules is almost always `INTRANS` by the time
they run. The savepoint machinery that follows works because
the next DDL/DQL statement opens a new transaction; the explicit
`conn.commit()` / `conn.rollback()` at the end of `_work()` closes
it.

### `issysop(args, **kwargs) -> bool`

Authorization gate. Returns `True` if EITHER:

- The current DB role is a member of the `sysop` role
  (`pg_auth_members` joined with `pg_roles` on `rolname='sysop'`,
  `member=current_user::regrole`), OR
- The current DB role has `rolsuper`.

The superuser fallback exists for the bootstrap window before
per-role `sysop` membership is granted. This function is
deliberately `engine.*`-table-free: it can run against a brand-new
database that has not yet been bootstrapped.

If neither `conn=` nor `pool=` is supplied, prints
`"bbsengine6.backend.lib.issysop: no conn or pool"` at `level="error"`
and returns `False`.

## Savepoint Protocol

Three modules wrap each row in a savepoint and roll back to it on
failure rather than aborting the whole transaction:

- `checkfunctions`
- `checkmessage`

The protocol is uniform across all three:

1. At the top of `_work(conn)` call `lib._ensure_autocommit_off(conn)`.
2. For each row, take a savepoint named `lib._sanitize_sp(row_key)`
   (functions/classes use the qualified name; enum types in
   `checkmessage` use the qualified name with `prefix="enum_"`).
3. If the work fails, call `database.importsql(...)` with
   `rollback=False` and wrap the call in `lib.retry_on_transient`.
4. On `False`, `ROLLBACK TO SAVEPOINT <sp>`, print
   ` fail ` at `level="error"`, and increment `failcount`.
5. On `True`, `RELEASE SAVEPOINT <sp>`, print `ok` at `level="ok"`.
6. After the loop, `conn.commit()` if `failcount==0` else
   `conn.rollback()`.

This pattern is required: a DDL import failure inside the bootstrap
transaction must not poison the outer transaction, and it must not
cause retries of imports that have already partially succeeded.

## `stage_zero.py` - Admin-Database Bootstrap

Runs against the `postgres` admin database. Module order is
fixed and significant:

1. `checkcreatedb` - abort early with a clear error if the
   connecting role lacks `CREATEDB` (or is not a superuser).
2. `checkdatabase` - verify the target database exists.
3. `checkextensions` - `pgcrypto`, `ltree`, `citext` (in
   `postgres`, even though extensions are normally per-database;
   extensions installed in `postgres` are NOT inherited by other
   databases, so `checkextensions` is also run in `stage_one`).
4. `checkroles` - `member`, `web`, `sysop`, `term`.
5. `checkfunctions` (stage=0) - the five `public.*` privilege
   helpers: `get_role_privs`, `manage_secondary_role`,
   `manage_role_privs`, `manage_database_priv`, `manage_schema_priv`.
6. `checksuperuser` - verify the OS login id has `rolsuper`.
7. `checkwebserverrole` - `www-data` with `login=True`, plus
   `GRANT member TO "www-data"` for `SET LOCAL ROLE` support.
8. `checkengine` - bootstrap the `engine` schema, its
   `USAGE`/`CREATE` grants, and its core classes.

The pool is built against `dbname="postgres"`. A `None` pool is a
hard failure (returns `False` with `"could not connect to 'postgres'"`
at `level="error"`). The pool context is exited via
`with pool:` (closes the pool on completion), and the connection
is closed via `with database.connect(...) as conn:`. Any exception
inside the body is reported via `io.echo_traceback`; the
`finally` clause prints `complete` (level=`ok`) on success or
`{failcount=}` (level=`error`) on failure.

`stage_zero.main` returns `True` iff `failcount == 0` after the
module loop.

## `stage_one.py` - Target-Database Bootstrap

Runs against the target database (`args.databasename`, e.g.
`zoid6`). Module order is fixed and significant:

1. `checkextensions` - install `pgcrypto`, `ltree`, `citext` in
   the target database.
2. `checkengine` - idempotent re-check of the `engine` schema.
3. `checkfunctions` (stage=1) - `engine.getflags`,
   `engine.checkmemberflag`.
4. `checkmemberflag` - `engine.member_flag`, `engine.map_member_flag`,
   and the `flagdata.sql` seed.
6. `checkbank` - `bank` schema + bank classes.

The pool is built via `database.getpool(args, database=args.databasename)`.
A single `with database.connect(args, pool=pool) as conn:` wraps
the entire module loop, with a single `conn.commit()` or
`conn.rollback()` at the end. This is why every child module's
`main()` is required to return `True`/`False` cleanly without
committing; a child that committed on its own would short-circuit
the rest of the stage.

`stage_one.main` returns `True` iff every child returned `True`
AND the final commit succeeded.

## `checkcreatedb.py`

Probes `pg_roles` for the current user and verifies that EITHER
`rolcreatedb` OR `rolsuper` is set. Acceptance:

- Accepts a `pool=` (preferred) or a `conn=` from `kwargs`. If
  neither is supplied, prints
  `"checkcreatedb: neither pool nor conn supplied; cannot check privs"`
  at `level="error"` and returns `False`.
- Looks up `rolcreatedb, rolsuper, rolname` from
  `pg_roles WHERE rolname = current_user`.
- If neither flag is set, prints two error lines naming the
  missing privilege and the target database, and returns `False`.
- On success, prints one `level="ok"` line reporting whether the
  user is a superuser or simply has `CREATEDB`.
- Returns `True` on success.

This module must run before `checkdatabase`, because
`checkdatabase` may need to `CREATE DATABASE` (which requires
CREATEDB or superuser); running it first would surface the
privilege gap as a raw `psycopg.errors.InsufficientPrivilege`
traceback.

## `checkdatabase.py`

Creates the main BBS database if it does not exist. Behavior:

1. Requires `pool=`. Returns `False` with
   `"database pool not available"` (level=`error`) if missing.
2. Opens a connection from the pool. If
   `database.exists(args, args.databasename, pool=pool)` returns
   `True`, prints ` ok ` (level=`ok`) and returns `True`.
3. Otherwise opens a second connection with
   `conn.autocommit = True` (CREATE DATABASE cannot run inside a
   transaction block) and calls `database.create(...)`. On
   success prints ` ok ` (level=`ok`); on failure prints `fail`
   (level=`error`), calls `conn.rollback()`, and returns `False`.
4. The post-creation role-grant loop (`term`, `web`, `sysop`
   `CONNECT` grants) is currently **dead code** in the shipped
   file: the `return True` after a successful create sits
   **before** the loop. Treat those grants as TODO; the module
   is functionally a "create-if-missing" check. Callers that
   need the grants should run `checkengine` instead, which
   performs the schema-level grants via `manage_schema_priv`.

## `checkengine.py`

The schema and class bootstrap, runnable in both stage 0 and
stage 1.

### SECURITY DEFINER helpers

Before creating the `engine` schema, this module:

1. Idempotently installs `public.manage_schema_priv` from
   `manage_schema_priv.sql` if not already present. (`stage_zero`
   `checkfunctions` already installs it, but `stage_one`
   `checkfunctions` only installs `engine.*` functions, so this
   module is the only place the helper reaches the target DB.)
2. Verifies the owner of every SECURITY DEFINER helper it will
   invoke against an allow-list before calling any of them:
   - `public.manage_schema_priv`
   - `public.manage_database_priv`
   - `public.manage_role_privs`
   - `public.manage_secondary_role`
   - `public.get_role_privs`
   The allow-list is `(args.databaseuser, "postgres")` (deduped;
   `args.databaseuser` defaults to `getpass.getuser()` then
   `"postgres"`). If a helper is missing it is skipped (it will
   be installed by `checkfunctions`); if it is present but owned
   by anyone else, the module prints
   `"checkengine: refusing to use {fn} (owner mismatch); see error above"`
   at `level="error"` and returns `False` without making any
   grant. This is a defense against privilege escalation via a
   replaced helper.

### Schema bootstrap

Creates the `engine` schema if missing (printing `create` on
create, `ok` on skip), then issues (via
`database.manage_schema_priv`):

- `GRANT USAGE ON SCHEMA engine TO web,term,sysop,member`
  (loop short-circuits on first failure)
- `GRANT CREATE ON SCHEMA engine TO sysop`

### Class bootstrap

Imports the following classes in dependency order from the named
SQL files. Each is checked with `database.classexists` first;
existing classes are skipped with `ok`. New ones are imported
via `database.importsql` and reported `import` + `ok` (or `fail`
on error):

| Class                       | SQL file             |
|-----------------------------|----------------------|
| `engine.__member`           | `member.sql`         |
| `engine.member`             | `memberview.sql`     |
| `engine.member_flag`        | `member_flag.sql`    |
| `engine.map_member_flag`    | `map_member_flag.sql`|
| `engine.__session`          | `session.sql`        |
| `engine.session`            | `session_view.sql`   |
| `engine.__folder`           | `folder.sql`         |
| `engine.__refcode`          | `refcode.sql`        |
| `engine.refcode`            | `refcode.sql`        |
| `engine.map_refcode_use`    | `refcode.sql`        |

The notify-related classes (`__notify`, `__notify_recipient`,
`__notify_block`, `__notify_group`, `__notify_type`,
`__notify_rate_limit`) have been **migrated to the unified message
system** in `checkmessage.py`. The `__message*` tables and views
provide equivalent functionality and are the canonical schema going
forward.

Returns `True` iff `failcount == 0` after the class loop.

## `checkextensions.py`

Iterates `("pgcrypto", "ltree", "citext")`. For each:

- If the extension is **not available**, prints `not available`
  and returns `False` immediately.
- If the extension is available but not installed, calls
  `database.creatextension` and prints `created` (or `fail` on
  failure, returning `False`).
- If the extension is already installed, prints ` ok `
  (level=`ok`).

After the loop, commits the conn. Output is via a single
`with database.cursor(conn) as cur:` block, so all three checks
share the same cursor. The conn is required (`conn=`) but no
`pool=` is used.

## `checkmemberflag.py`

Bootstrap for the flag system. Steps:

1. Check `engine.member_flag`; import `member_flag.sql` if
   missing. (Note: `checkengine` no longer imports this class; it
   was removed to avoid duplicate loading.)
2. Check `engine.map_member_flag`; import `map_member_flag.sql`
   if missing.
3. Run `SELECT count(name) FROM engine.member_flag`:
   - `rowcount == 0` is treated as a query failure (`fail`,
     `failcount += 1`).
   - `rowcount == 1` with `count == 0` triggers
     `import flagdata.sql` (the seed data); `ok` on success.
   - `rowcount == 1` with `count > 0` is treated as already
     seeded (`ok`).

Returns `True` iff `failcount == 0`. Requires `conn=` and
optionally uses `pool=` for `importsql` calls.

## `checkfunctions.py`

Installs SECURITY DEFINER helpers. Accepts a `stage=` kwarg
(default 0) and a `conn=`. Function set is stage-dependent:

- **stage 0** (admin DB): `public.get_role_privs`,
  `public.manage_secondary_role`, `public.manage_role_privs`,
  `public.manage_database_priv`, `public.manage_schema_priv`.
- **stage 1** (target DB): `engine.getflags`,
  `engine.checkmemberflag`.

For each function:

- If it exists, prints `exists` (level=`ok`).
- Otherwise derives the SQL file by stripping the schema prefix
  (`engine.` or `public.`) and appending `.sql` if not already
  present. The savepoint protocol above is used; failures are
  retried with `lib.retry_on_transient` and rolled back to the
  savepoint.

Returns `True` iff `failcount == 0` after the loop.

## `checkmessage.py`

Bootstrap for the unified message system (`engine.__message*` classes
and views). Replaces the legacy `checknotify.py`.

| Class                              | SQL file             |
|------------------------------------|----------------------|
| `engine.__message`                 | `message.sql`        |
| `engine.__message_recipient`       | `message.sql`        |
| `engine.__message_group`           | `message_groups.sql` |
| `engine.__message_group_member`    | `message_groups.sql` |
| `engine.__message_block`           | `message_groups.sql` |
| `engine.__message_type`            | `message_groups.sql` |
| `engine.__message_rate_limit`      | `message_groups.sql` |
| `engine.message`                   | `messageview.sql`    |
| `engine.message_unread`            | `messageview.sql`    |
| `engine.message_urgent`            | `messageview.sql`    |
| `engine.message_blocked`           | `messageview.sql`    |

Also installs the enum `engine.notify_urgency_enum` from
`message_enum.sql` (with savepoint prefix `enum_`).

Uses the savepoint protocol. Requires `conn=`.

**Server-push integration:** `message.sql` also installs the
`engine.__message_recipient_notify()` PL/pgSQL function and two
triggers on `engine.__message_recipient`:

- `trg_message_recipient_insert` (AFTER INSERT) — fires
  `pg_notify('engine_message_recipient', json payload)` with
  `message_id`, `recipient_id`, `recipient_moniker`, `status`,
  `urgency`, `datestamp`.
- `trg_message_recipient_update` (AFTER UPDATE of
  status/datedelivered/dateread) — same payload, fires only when
  one of those columns actually changes.

The `bed.api.message.MessageService` LISTENs on this channel via a
dedicated `psycopg.AsyncConnection` and fans out to subscribed
WebSocket clients by `recipient_moniker`. The bbsengine6 TUI
subscribes during `bbsengine6.startup.main()` via
`startup.message_subscription.subscribe_to_bed_sync()`.

## `checkroles.py`

Verifies that the four engine roles exist: `member`, `web`,
`sysop`, `term`. For each, if `database.rolexists` returns
`False`, creates it via
`database.createrol(..., superuser=False, login=False, createdb=False, createrole=False)`.
All four are NOLOGIN group-like roles by design. On success
prints ` ok `; on create failure prints ` fail ` (level=`error`),
increments `failcount`, and breaks out of the loop. Returns
`True` iff `failcount == 0`.

Requires `conn=`. Note: this module does NOT create
`www-data`; that is `checkwebserverrole`'s job.

## `checksuperuser.py`

Verifies that the OS login id is a PostgreSQL superuser. Steps:

1. Resolve the current login id via
   `bbsengine6.util.getcurrentloginid(args)`.
2. If `database.rolexists(args, currentloginid, conn=conn, mogrify=True)`
   is `False`, print
   `"role '{currentloginid}' does not exist"` and return `False`.
3. Call `database.get_role_privs(args, currentloginid, conn=conn, pool=pool)`.
4. If the result is falsy, print
   `"'{currentloginid}' does not have correct privs (or lookup failed)"`
   and return `False`.
5. If `privs["rolsuper"]` is `True`, print
   `"'{currentloginid}' has correct privs (superuser)"` and
   return `True`.
6. Otherwise print
   `"'{currentloginid}' is not a superuser; the BBS engine bootstrap requires rolsuper. Run 'ALTER ROLE {currentloginid} WITH SUPERUSER;' and retry."`
   at `level="error"` and return `False`.

The previous version of this check accepted any role with
CREATEDB + CANLOGIN + CREATEROLE as superuser-equivalent; that
was over-broad and could be escalated by creating additional
roles, so the check now requires `rolsuper` only.

## `checkwebserverrole.py`

Ensures the `www-data` database role exists. If missing,
creates it via `database.createrol(args, "www-data", conn=conn, login=True)`.
The previous version also issued a second
`manage_role_privs(..., "grant", "login", ...)` call after
creation; that was removed because the post-creation grant
expanded the credential attack surface (the role could then
authenticate with a password in addition to peer auth). The
`login=True` flag at creation time is the minimum needed.

After ensuring the role exists, grants `www-data` membership in
the `member` group role (`GRANT member TO "www-data"`). This
allows `SET LOCAL ROLE member` to succeed when the connection is
held by `www-data`, enabling the `set_role` parameter in
`database.connect()`.

Returns `True` iff `failcount == 0`. Requires `conn=`.

## `database.py`

Lower-level "create the database" check. Distinct from
`checkdatabase.py`:

- Requires `conn=`; takes the conn's prior `autocommit` value,
  flips it to `True` for the `CREATE DATABASE` call, then
  restores it. This is necessary because
  `database.create()` (which issues `CREATE DATABASE`) cannot
  run inside a transaction block, and the helper here is
  designed to be called from contexts where the conn may be
  in autocommit-off mode.
- If the database already exists, prints `ok` and returns
  `True`.
- If it does not exist, prints ` create ` and calls
  `database.create(...)`. On success `ok` and `True`; on
  failure `fail` and `False`.
- Always emits `lib.hr(failcount)` at the end.

The `createdatabase` runner in `lib.py` dispatches to this
module (NOT to `checkdatabase`).

## `checkbank.py`

Bootstrap for the `bank` schema. Steps:

1. If the `bank` schema does not exist, create it. On failure
   `lib.fail()`, `failcount += 1`, then `lib.hr(1)` and return
   `False`.
2. For each of `web`, `term`, `sysop`, `member`: `GRANT USAGE ON
   SCHEMA bank TO <role>` via `manage_schema_priv`. On the
   first failure `lib.fail()` and break.
3. `GRANT CREATE ON SCHEMA bank TO sysop` via
   `manage_schema_priv`. On failure `lib.fail()`, increment
   `failcount`, and return `False`.
4. Import the six bank classes (each in savepoint-free
   straight-line; this module predates the savepoint protocol):

   | Class                       | SQL file                |
   |-----------------------------|-------------------------|
   | `bank.__account`            | `bank_account.sql`      |
   | `bank.account`              | `bank_account_view.sql` |
   | `bank.__transaction`        | `bank_transaction.sql`  |
   | `bank.transaction`          | `bank_transaction_view.sql` |
   | `bank.__transfer`           | `bank_transfer.sql`     |
   | `bank.transfer`             | `bank_transfer_view.sql` |

5. Emit `lib.hr(failcount)` and return
   `True if failcount == 0 else False`.

The `checkbank` `access()` gate is `lib.issysop`; `init` is a
no-op `return True`; `buildargs` delegates to `lib.buildargs`.

## `__init__.py`

Empty. The package is exposed only through its submodules
dispatched via `bbsengine6.module.runmodule` /
`bbsengine6.backend.lib.runmodule`.

## `Makefile`

```
all:

clean:
	-rm *~ *.pyc
```

`make` does nothing; `make clean` removes editor backups and
compiled Python files from this directory.

## Historical Notes

### `{level.fail}` is in live use

Commit `8a5d1c0` removed `{level.fail}` and the `level="fail"`
example from `io/specs/echo_commands.spec` on the assumption that
no caller used them. `backend.lib.fail()` emits
`{{level.fail}} fail {{/all}}` and is called by `checkdatabase`,
`checkroles`, `checkwebserverrole`, `checkmemberflag`, `checksuperuser`,
and `checkbank`. Commit `7115e77` restored both lines in the spec. If
you ever consider removing `{level.fail}` again, also remove
`backend.lib.fail()` and migrate those callers to
`io.echo(level="error")` first; otherwise the spec will be out of
sync with the live API. `backend.lib` records this constraint in
the import-time log entry
`"backend.lib: {level.fail} is in use by fail(); spec lists it"`
via `bbsengine6.util.logentry(action="level_fail_in_use")`.

### Security tightening history

- `checksuperuser`: previous version accepted any role with
  CREATEDB + CANLOGIN + CREATEROLE as superuser-equivalent.
  Narrowed to require `rolsuper` only.
- `checkwebserverrole`: previous version issued a separate
  `manage_role_privs(..., "grant", "login", ...)` call after
  creation. Removed; the `login=True` creation-time flag is
  the minimum needed. Now also grants `GRANT member TO "www-data"`
  to support `SET LOCAL ROLE member` from web-side connections.
- `checkengine`: introduced the SECURITY DEFINER helper owner
  allow-list check before invoking any `manage_*` helper, to
  defend against privilege escalation via a replaced helper.
- `checkcreatedb`: previous version required `pool=` and
  silently failed when only `conn=` was supplied. Now accepts
  `conn=` (used as-is) as well as `pool=`.
