# bbsengine6.console — admin CLI

> **Status:** canonical. The `bbsengine6.console` package is a small
> collection of admin UIs; the database-staging routines (the
> `check*.py` modules) live in `bbsengine6.backend`, with thin shims
> re-exported from `bbsengine6.console` for backward compatibility.
> The canonical home for engine init is `bbsengine6.backend` (per
> the Phase 0 backend refactor); the console package owns the
> admin menus only.

The `bbsengine6.console` package provides the interactive and
non-interactive admin tools for the BBS engine: an interactive menu
loop, member CRUD, member approval, session display, psql role
display, database creation, and a single-line `bbsengine6-msg`-style
subcommand dispatch.

## Contents

- [Architecture](#architecture)
- [Entry points](#entry-points)
- [Interactive menu](#interactive-menu)
- [Subcommand dispatch](#subcommand-dispatch)
- [Module shape](#module-shape)
- [Member management](#member-management)
- [Session display](#session-display)
- [PostgreSQL role display](#postgresql-role-display)
- [Database creation](#database-creation)
- [Database check routines](#database-check-routines)
- [Incomplete features](#incomplete-features)

## Architecture

The console is **not** a 2,200-line monolith. The actual package is
seven submodules:

| Module               | Lines | Role                                                                  |
|----------------------|-------|-----------------------------------------------------------------------|
| `__init__.py`        | 8     | `__all__` listing the public submodules                                |
| `__main__.py`        | 72    | `console <subcommand>` dispatch (argparse + module loader)             |
| `lib.py`             | 129   | subcommand parser + `runmodule` / `setbottombar` / `buildargs`        |
| `main.py`            | 87    | interactive menu (`M`embers / `S`essions / `A`pprovals / e`X`it)      |
| `member.py`          | 631   | member CRUD — list, add, edit, configurerole, editflags, editui       |
| `memberapproval.py`  | 197   | approval workflow for pending `engine.member` rows                     |
| `session.py`         | 78    | `engine.session` display                                               |
| `showpgrole.py`      | 180   | show psql `rolname` / `osuser` / connect-string for the current login  |
| `createdatabase.py`  | 30    | `console createdatabase` — invokes `bbsengine6.database.create`        |
| `Makefile`           | —     | test / install / lint targets                                          |

Database-staging routines (the 15 `check*.py` modules, the two
`stage_*.py` orchestrators, and the engine / bank bring-up
sequences) live in `py/src/bbsengine6/backend/`. The console
package keeps thin shims that re-export from `bbsengine6.backend`
so legacy callers that import `bbsengine6.console.checkroles`
keep working unchanged.

## Entry points

```bash
# Interactive menu (no subcommand)
python -m bbsengine6.console

# Subcommand dispatch
python -m bbsengine6.console member
python -m bbsengine6.console memberapproval
python -m bbsengine6.console session
python -m bbsengine6.console showpgrole
python -m bbsengine6.console createdatabase

# Backend utilities (re-exported shims)
python -m bbsengine6.console checkroles
python -m bbsengine6.console checkdatabase
python -m bbsengine6.console checkcreatedb
python -m bbsengine6.console checkextensions
python -m bbsengine6.console checkfunctions
python -m bbsengine6.console checkengine
python -m bbsengine6.console checkclasses
python -m bbsengine6.console checkmemberflag
python -m bbsengine6.console checkmessage
python -m bbsengine6.console checkbank
python -m bbsengine6.console checkwebserverrole
python -m bbsengine6.console checkloginid
python -m bbsengine6.console checksuperuser
python -m bbsengine6.console checknotify        # legacy, see Incomplete features
python -m bbsengine6.console checknotifyd       # legacy, see Incomplete features
```

`python -m bbsengine6.startup` is the recommended entry point for
engine bring-up; the console subcommands are operator tools, not
init plumbing.

## Interactive menu

`bbsengine6.console.main.main(args)` runs the interactive menu:

```
[M] Members
[S] Sessions
[A] Approvals
[X] Exit
```

The loop calls `bbsengine6.console.lib.runmodule(args, "member"|"session"|"memberapproval", pool=pool)`
for each selection. `pool` and `conn` are threaded through so the
called module reuses the same connection that `main` opened.

`--require-registration` (added in `console/lib.py`) calls
`bbsengine6.module.set_require_registration(True)` before any
module load — every `console` subcommand loaded thereafter must
have registered itself with `bbsengine6.module.register_module`,
or the call returns `False` from `module.check`.

## Subcommand dispatch

`bbsengine6.console.lib` defines two subcommand lists:

```python
CONSOLE_SUBCOMMANDS = (
    "createdatabase",
    "member",
    "memberapproval",
    "session",
    "showpgrole",
)

BACKEND_SUBCOMMANDS = {
    "bank",
    "checkclasses",
    "checkcreatedb",
    "checkdatabase",
    "checkengine",
    "checkextensions",
    "checkmemberflag",
    "checkfunctions",
    "checkloginid",
    "checknotify",        # legacy shim
    "checknotifyd",       # legacy shim
    "checkroles",
    "checksuperuser",
    "checkwebserverrole",
}
```

`build_subcommand_parser()` builds an `argparse.ArgumentParser` with
the union of both lists as subcommands. `handle_subcommand(args,
subcommand)` routes backend subcommands to
`bbsengine6.backend.<subcommand>` and console subcommands to
`bbsengine6.console.<subcommand>` via `module.runmodule(...)`.

`runmodule(args, submodule, *, package="bbsengine6.console",
**kwargs)` is a one-line wrapper around `module.runmodule(args,
f"{package}.{submodule}", **kwargs)`. The `package=` kwarg is the
extension point that `bbsengine6.startup.lib` reuses with
`package="bbsengine6.startup"`.

## Module shape

Every console module follows the standard four-function shape that
the bbsengine6 module loader expects:

```python
def init(args, **kwargs) -> bool: ...
def access(args, op: str, **kwargs) -> bool: ...
def buildargs(args, **kwargs) -> argparse.ArgumentParser | None: ...
def main(args, **kwargs) -> Any: ...
```

See `handbook/specs/module.md` for the full contract.

## Member management

`bbsengine6.console.member` is the admin member CRUD module. It
exposes:

| Function / behavior | Description                                                                   |
|---------------------|-------------------------------------------------------------------------------|
| `editflags(args, moniker=None, **kwargs)` | In-memory flag toggle; persists through the surrounding add/edit operation. Honors `mode="add"` to use a blank flag dict |
| `render_member(args, **kwargs)`           | Pretty-print a member dict with `[M]oniker`, `[L]oginid`, `[E]mail`, etc.    |
| Interactive `main` | `[A]dd`, `[E]dit`, `[F]lags`, `[U]i`, `[C]onfig`, `[L]ist`, `[X]it`           |

The module writes through `bbsengine6.member.libmember` (the
`bbsengine6.member.lib` facade), `bbsengine6.bank` for credits, and
`bbsengine6.pgrole` for the per-member psql role.

## Member approval

`bbsengine6.console.memberapproval` is the workflow for rows in
`engine.member` with `approvedbymoniker IS NULL`. The module:

1. `SELECT moniker FROM engine.member WHERE approvedbymoniker IS NULL`
   — uses `cur.fetchall()` (not `fetchmany`) because psycopg's
   `arraysize` defaults to 1.
2. For each pending moniker: show loginid, email, and verified
   state; prompt for the verified y/n and the approve y/n.
3. On approve: set `APPROVED`, stamp `approvedbymoniker` /
   `dateapproved`, and call
   `bbsengine6.pgrole.ensure_login_role(args, moniker, conn=conn)`
   to provision the `m_<moniker>` PG role.
4. On disapprove: clear `APPROVED` and the audit columns.
5. Any failure rolls back the transaction.

Access requires `member.checkflag(args, "SYSOP", member.getcurrentid(args))`.

## Session display

`bbsengine6.console.session` runs:

```sql
select * from engine.session order by datecreated
```

and prints each row with the moniker, created/expiry timestamps,
last-activity delta, and user agent. The `pool` must be present in
`kwargs` (passed by `console.main.main`); the module errors out
otherwise.

## PostgreSQL role display

`bbsengine6.console.showpgrole` shows psql access info for a
member — the `rolname`, the OS user (`osuser`), and the
`created_at` / `last_ack_at` audit columns. The flow:

1. If no `engine.pgrole` row exists for the member: tell the user to ask a
   sysop to approve them.
2. If `last_ack_at IS NULL`: render the welcome block, prompt for
   ENTER, update `last_ack_at`.
3. If `osuser` is blank: prompt for the OS username they connect
   from. The welcome flow is skipped on non-TTY stdin.

See [`./pg-ident-auth.md`](./pg-ident-auth.md) for the `bbbsmap` /
`pg_ident.conf` setup the output expects.

## Database creation

`bbsengine6.console.createdatabase` wraps `bbsengine6.database.create`:

```python
database.create(args, args.databasename, **kwargs)
```

The engine `BBSENGINE6_DBNAME` (default `zoid6`) is the default
target.

## Database check routines

The 15 `check*.py` modules live under `py/src/bbsengine6/backend/`.
Console keeps thin shims that re-export from `backend`:

| Backend module                  | Role                                                                       |
|---------------------------------|----------------------------------------------------------------------------|
| `checkroles`                    | Verify the `web` / `sysop` / `term` PG roles exist                          |
| `checkextensions`               | Ensure `pgcrypto`, `ltree`, `citext` extensions are installed                |
| `checkdatabase`                 | Verify / create the BBS database                                            |
| `checkcreatedb`                 | Verify CREATEDB privilege on the bootstrap role                             |
| `checksuperuser`                | Verify the current role is PG superuser                                     |
| `checkfunctions`                | Install `engine.*` `SECURITY DEFINER` helpers                               |
| `checkengine`                   | Install the `engine` schema with `AUTHORIZATION zoid6`                      |
| `checkclasses`                  | Verify `engine.__*` tables                                                  |
| `checkmemberflag`               | Verify `engine.member_flag` / `map_member_flag`                              |
| `checkmessage`                  | Verify `engine.__message*` tables / views; install `message_enum.sql`        |
| `checkbank`                     | Verify `engine.__bank_*` tables                                             |
| `checkwebserverrole`            | Verify the `www-data` role exists                                            |
| `checkloginid`                  | Verify system login (`/etc/login.defs` probe via DBus)                      |
| `checkpasswordformat`           | Install `chk_member_password_bcrypt` CHECK constraint                       |
| `checkzoid6role`                | Create the dedicated `zoid6` role (`NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN INHERIT`) |
| `checkzoid6owner`               | Reassign the 5 `SECURITY DEFINER` helpers to `zoid6` if ownership drifted   |

`bbsengine6.console.lib.checkroles(args, **kwargs)` (and similar)
delegates to `bbsengine6.backend.lib.checkroles` which delegates to
`module.runmodule(args, "bbsengine6.backend.checkroles")`. The
console side is intentionally one-line so the engine bring-up path
can call the same function from either package.

## Incomplete features

**Email stub.** `bbsengine6/console/email.py` is referenced in some
old docs as an SMTP-configuration admin module. The current
package does not ship it; that functionality is unimplemented and
should be added as a new `bbsengine6.console.email` module when
needed.

**Messaging CLI.** The operator CLI for the messaging subsystem
lives at `python -m bbsengine6.message` (subcommands `list-types`,
`pending`, `unread`, `mark-read`, `mark-delivered`, `expunge`,
`register-type`, `resolve`, `send`). It is **not** a console
subcommand — see `handbook/specs/messaging.md` §CLI.

**Notify subsystem (deleted).** `bbsengine6.console.notify` and the
`bbsengine6.console.checknotify` / `checknotifyd` shims were part
of the legacy notify-based console flow. The notify package was
deleted 2026-07-22 (Phase 7 of `bbsengine6/TODO-message-migration.md`).
The shim modules still exist for backward compatibility (so
`python -m bbsengine6.console checknotify` does not raise
`ModuleNotFoundError`), but they are no-ops that return success
without checking anything. Use the message CLI for messaging
operations.
