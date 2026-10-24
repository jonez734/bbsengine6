# Per-member psql access (ident auth)

> Status: canonical. Updated 2026-10-24.

Each approved member can connect to PostgreSQL with `psql` as their own
OS account. Two PostgreSQL roles are involved per member:

- **Login role** `<osuser>`: the OS username. `ident` logs the connection
  in as this role. It is `LOGIN NOINHERIT`, holds no privileges of its
  own, and is granted the data role.
- **Data role** `m_<moniker>`: holds the member's privileges. It is
  `NOLOGIN`, so it cannot be connected to directly. The login role reaches
  it with `SET ROLE`.

No password is ever set, displayed, or stored.

## Current model

| Layer | Detail |
| --- | --- |
| Data role | `m_<moniker>`, `NOLOGIN`, granted `member`. Chosen by the sysop on new members (default `m_<moniker>`). An existing member's data role is not renamed from the console |
| Login role | The member's OS username (`engine.pgrole.osuser`). `LOGIN NOINHERIT`, granted the data role so `SET ROLE` works |
| Group role | `member` (NOLOGIN, NOINHERIT). Granted to every data role. Schema usage and SELECT come from `member` |
| Tracking | `engine.pgrole(membermoniker, rolname, osuser, ...)`. `rolname` is the data role; `osuser` is the login role's name |
| Provisioning | `bbsengine6.pgrole`: `ensure_login_role` (data role), `ensure_os_login_role` (login role), `remove_os_login_role` (old login), `preview_nologin_migration` and `run_nologin_migration` (migration) |
| Console | `console/member.py`: `configurerole` provisions both roles. The edit menu's `[O]` (OS login) and `[X]` (data role) options check existence right after input and write only when the menu exits |
| Migration | Run from the console. See "Migrating existing roles" |

Only `SET ROLE` reaches member privileges. A login role without
membership in its data role can connect and do nothing with it.

## Authentication method

**Current method: `ident`.** The connecting OS account must match a
login role name exactly. No `pg_ident.conf` map is used in this setup.

**Planned: other methods.** Other authentication methods are planned.
The candidates are peer authentication over a Unix socket, and
`scram-sha-256` with a password. Neither is implemented. Choosing one
means changing `pg_hba.conf` and the login-role setup, and deciding how
credentials are stored (none are, under ident).

## Configuration

### `pg_hba.conf`

The TCP localhost rules must use `ident`:

```
host    all    all    127.0.0.1/32    ident
host    all    all    ::1/128         ident
```

Do not use `0.0.0.0/0` for ident. It is meaningful only on trusted,
controlled networks.

## First-time setup

1. Confirm the `ident` lines above in `pg_hba.conf`.
2. Create the member through the console (`[N]` New Member). The
   `configurerole` step creates both roles and records them in
   `engine.pgrole`. Answer the OS-login question with the member's OS
   username.
3. The console asks before creating a missing login role. Accept the
   default to create it.
4. The member connects with `psql -h 127.0.0.1 -U <osuser> -d <dbname>`.

## Migrating existing roles

Data roles created before the NOLOGIN rule may still be `LOGIN`. A
`LOGIN` data role lets an OS account of the same name connect and skip
the login role. The migration removes that login.

**Run it from the console.** Open the main console as a sysop and press
`[K]` (Migrate data roles to NOLOGIN).

- The console lists the roles it will change, then asks `[yN]`.
  Declining changes nothing.
- It excludes `jam` (the legacy owner mapping) and superusers.
- It runs `sql/migrate_nologin.sql` in one transaction. On error it
  rolls back and reports the message.
- It re-checks afterward and reports any roles still able to log in.

**Startup warning.** When a sysop opens the console and login-capable
data roles exist, the console prints one line: how many roles can still
log in, and to press `[K]`. The warning never blocks startup.

**Why it is not automatic.** `checkclasses` imports a table's SQL only
when the table is missing, so it never re-runs `pgrole.sql` on an
existing database. The migration is a separate, explicit action.

**Effect.** A member who connects directly as `m_<name>` is locked out
after the migration. They must connect as their login role instead.

## The `member` group

Granted to `member`:

- `USAGE` on `engine` and `bank` schemas.
- `SELECT` on all existing tables in `engine` and `bank`, and default
  privileges so future tables inherit it.
- `SELECT` on `engine.pgrole`.

Not granted (intentionally):

- `INSERT` / `UPDATE` / `DELETE` on `engine.__session` or `engine.__invite`.
- `CREATEROLE`, `CREATEDB`, `SUPERUSER`.
- `USAGE` on any other schema. New schemas need their own grants.

## Operations

### Adding a member

1. Create the member with `[N]` (New Member). This is the complete path:
   it creates the data role and, with an OS username, the login role.
2. In the edit menu, `[O]` sets the OS username. It defaults to the
   stored value or the loginid. If the login role does not exist, the
   console asks whether to create it on exit.
3. `[X]` sets the data role. The default is `m_<moniker>`. An existing
   data role is not renamed.
4. Exit the menu. The console creates the roles, grants them, and
   records `osuser` in `engine.pgrole`.

### Changing a member's OS username

Press `[O]` and enter the new name. If the stored name changes, the
console asks whether to remove the old login role (default No). Yes
revokes the old login's access to the data role, and drops the role if
nothing else uses it. Removal happens on exit, with the other writes.

**Known gap:** `[A] Approvals` creates only the data role. It does not
ask for an OS username, so it creates no login role, and the member
cannot connect until the sysop sets one with `[O]`. Its message still
tells the sysop to add a `bbbsmap` line to `pg_ident.conf`, which is no
longer used.

### Removing a member

Use the member console. Removing a login role revokes its access to
the data role. Jam and superusers are never removed.

## Previous design (historical)

Earlier versions named the login role `l_<loginid>`, mapped the OS user
to it with a `bbbsmap` line in `pg_ident.conf`, and created data roles
as `LOGIN`. That design is replaced. The `l_` names and `pg_ident.conf`
are not used now.

## Deferred work

- **Other authentication methods** (see "Authentication method").
- **Password fallback** for deployments without stable OS accounts per
  member. Would need credential storage, rotation, and redaction.
- **PHP web surface** (`engine/psql_credentials.php`). Blocked on the
  web machine running on the same host as the database.
- **Per-request `SET LOCAL ROLE`** for the web path. Per-member data
  isolation still requires row-level security; see `TODO_RLS.md`.
- **Audit table** (`engine.pgrole_event`) for role and grant changes.
