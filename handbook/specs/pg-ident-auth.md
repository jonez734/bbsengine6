# per-member psql access (ident auth)

Every approved `engine.member` gets a PostgreSQL `LOGIN` role so they
can connect with `psql` directly. Authentication is by `ident` — the
member connects as their own OS account, and `pg_ident.conf` on the
DB host maps that OS user to the member's `l_<loginid>` PG role. No
password is ever set, displayed, or stored.

## Architecture

- **PG role**: `l_<loginid>`, derived from the member's `loginid`
  (lowercased, non-alnum → `_`, numeric suffix on collision with any
  existing `pg_roles.rolname`).
- **Group role**: `member` (NOLOGIN, NOINHERIT). Every `l_<loginid>`
  is GRANTed membership. The baseline schema usage and SELECT
  privileges are granted to `member`, not to each `l_<loginid>`.
- **Group sync**: `engine.syncpgrolegroups(memberid)` brings a
  member's `l_<loginid>` role's `sysop` / `term` / `web` group
  memberships in line with the member's current flags. Called from
  the sysop console (`console/member.py:edit()`, `add()`) and from
  the approvals flow (`console/memberapproval.py`).
- **Tracking**: `engine.pgrole(memberid, rolname, osuser, created_at,
  last_ack_at)`. `osuser` is the OS username the member connects
  from; `last_ack_at` records that the member has seen the welcome
  screen.
- **Provisioning**: `engine.createpgrole(loginid, osuser)` is the
  single entry point. It derives the rolename, collision-suffixes,
  runs `CREATE ROLE ... LOGIN INHERIT` (no password), `GRANT member
  TO`, and INSERTs the tracking row.
- **Removal**: `engine.deletepgrole(rolname)` runs `DROP ROLE IF
  EXISTS` and removes the `engine.pgrole` row.

## Configuration

### `pg_hba.conf`

The DB host needs an `ident` line that uses the `bbbsmap` map for
local connections:

```
host    all    all    127.0.0.1/32    ident    map=bbbsmap
```

If members also need to connect from a specific subnet (e.g. a
terminal-server LAN), add additional `host` lines scoped to that
subnet. Do **not** use `0.0.0.0/0` for ident — ident is meaningful
only for trusted, controlled networks.

### `pg_ident.conf`

One line per member, mapping the OS user to the PG role:

```
bbbsmap    l_jonez    jonez
```

The OS user is what the member `su`s to (or is logged in as) on the
client host. It does not have to be unique globally — it just has to
be unique per client host. The PG role name on the left side must
match the `l_<loginid>` value stored in `engine.pgrole.rolname`.

After editing, reload PostgreSQL:

```
sudo systemctl reload postgresql
```

(or `SELECT pg_reload_conf();` from a SQL session as a superuser.)

## First-time setup checklist

1. Add the `ident` line to `pg_hba.conf`.
2. Run `\i bbsengine6.sql` so the `engine.pgrole` table, the
   `member` group role, and the `engine.createpgrole` /
   `engine.syncpgrolegroups` / `engine.deletepgrole` functions are
   created.
3. Run `py/src/bbsengine6/sql/backfill_pgrole.sql` to provision
   `l_<loginid>` roles for all currently-approved members. Their
   `osuser` is left NULL — to be filled in by the member on first
   `[P] psql credentials` visit, or by the sysop.
4. For each backfilled member (and each new member going forward),
   add a `bbbsmap` line to `pg_ident.conf` and reload PG.
5. Members run `[P]` from the `member:` console menu. The first
   visit prompts for `osuser` and acknowledges the welcome. The
   `psql` connect command is printed.

## Member flow (the `[P]` menu entry)

`py/src/bbsengine6/console/showpgrole.py:main()`:

- If no `engine.pgrole` row exists for the member: tell them to ask
  a sysop to approve them.
- If a row exists: print the rolname, osuser, and the `psql`
  connect command. If `last_ack_at` is NULL, require an ENTER to
  acknowledge, then capture `osuser` if blank.
- No password, no regenerate, no re-show. Auth is by ident; the
  only secret the member needs is their own OS account.

## What the `member` group grants (and doesn't)

Granted to `member`:

- `USAGE` on `engine` and `bank` schemas.
- `SELECT` on all existing tables in `engine` and `bank`.
- `ALTER DEFAULT PRIVILEGES` so future tables inherit the same
  SELECT grant.
- `SELECT` on `engine.pgrole` (so a future `SET LOCAL ROLE` flow
  can read the tracking row).

**Not** granted (intentionally):

- `INSERT` / `UPDATE` / `DELETE` on `engine.__session` or
  `engine.__invite`. Members don't write to these via psql. If
  that becomes a need, add it explicitly.
- `CREATEROLE`, `CREATEDB`, `SUPERUSER`. Members connect read-only.
- `USAGE` on any schema other than `engine` and `bank`. New schemas
  (e.g. a future `games` schema) need their own grants.

## Operations

### Adding a new member

1. The new member submits `join.php` (no PG role is created here).
2. A sysop runs `[A] Approvals` from the `member:` menu and approves
   the application. The console hook calls
   `engine.createpgrole(loginid, NULL)`. The console prints the new
   rolname and reminds the sysop to add the `bbbsmap` line to
   `pg_ident.conf`.
3. The sysop edits `pg_ident.conf` and reloads PG.
4. The member logs in and runs `[P] psql credentials`. The welcome
   flow records `osuser` and sets `last_ack_at = now()`.

### Removing a member

- `engine.deletepgname(rolname)` drops the PG role and the
  `engine.pgrole` row.
- The sysop should also remove the corresponding `bbbsmap` line
  from `pg_ident.conf` and reload PG.

### Flag changes

Whenever a member's flags change (e.g. they become a sysop), the
`engine.syncpgrolegroups(memberid)` SQL function is called from
`console/member.py:edit()` to bring the `l_<loginid>` role's
`sysop` / `term` / `web` group memberships in line. This is
idempotent and cheap; safe to call on every edit.

## Deferred work (see `bbsengine6/TODO.md`)

- **Password fallback**: add a password to `engine.createpgrole` for
  deployments without stable OS accounts per member. Would also
  require `engine.rotatepgrole`, a regenerate UI in `showpgrole.py`,
  and a redaction list in the logging helpers.
- **PHP web surface**: `engine/psql_credentials.php` plus helpers
  in `php/libmember.php`. Blocked on the web machine being on the
  same host as the DB.
- **`SET LOCAL ROLE member` per request**: implemented in
  `database.connect()` / `database.async_connect()` via the
  `set_role` keyword argument. The `www-data` DSN user has been
  granted membership in `member` (`checkwebserverrole.py`). Call
  `database.connect(args, pool=pool, set_role="member")` to run a
  transaction as the `member` group role. Per-member data isolation
  still requires RLS — see `bbsengine6/TODO_RLS.md`.
- **`SET LOCAL ROLE l_<loginid>` per request**: would switch to the
  specific member's role. Requires RLS for meaningful privacy
  enforcement, plus `GRANT l_<loginid> TO "www-data"` per member
  (or a superuser DSN user).
- **Email notification** on psql access provisioning.
- **Audit table**: `engine.pgrole_event` for tighter tracking of
  every `CREATE ROLE` / `ALTER ROLE` / `DROP ROLE` / `GRANT` /
  `REVOKE`.
- **Re-show the current osuser** would require no extra work
  (it's already shown). Re-show a *password* is impossible without
  persisting it, which contradicts the design.
