# Per-Member PostgreSQL Roles — Deferred: Row-Level Security (RLS)

This document captures the RLS-related design from the per-member-PG-role plan
that the implementer has decided **not** to build in the first pass. Kept here
so the work is not lost.

## Why deferred

The initial goal is to let every approved member `psql -U <rolname>` into the
database directly. The application itself keeps using its single privileged
DSN user. That goal is achievable without enabling RLS on any table, and
shipping RLS in the same change would massively expand the blast radius (every
SELECT/INSERT/UPDATE/DELETE in the PHP and Python code paths would have to be
re-validated against the new policies, including the `www-data` service
role's existing grants). Deferring RLS keeps the first PR small and reviewable.

## What was deferred

From the original plan, the following items are out of scope until this doc is
picked back up.

### 1. `FORCE ROW LEVEL SECURITY` on member-owned tables

Tables that should eventually be RLS-protected (so that when a member connects
directly with their `m_<moniker>` role they only see their own rows):

- `engine.__member` / `engine.member`
- `engine.__session` / `engine.session`
- `engine.message` (each member's authored messages and their own inbox)
- `engine.folder` (per-member folders)
- `engine.__blurb` / `engine.blurb` if blurbs are per-member
- any future per-member tables added in `engine.*`

For each, the pattern is:

```sql
ALTER TABLE engine.<table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE engine.<table> FORCE ROW LEVEL SECURITY;  -- applies to table owner too
CREATE POLICY <table>_self_select ON engine.<table>
  FOR SELECT TO m_*
  USING (
    current_setting('app.memberid', true)::BIGINT = <owner-column>
  );
-- analogous INSERT / UPDATE / DELETE policies
```

The `app.memberid` GUC is set per-request (see #3 below).

### 2. Privileged DSN user stops being superuser-like

Once RLS is in place, the `web` / `sysop` / `term` roles that the PHP and Python
apps connect as will also be subject to RLS unless they are explicitly bypassed.
Two viable approaches, both deferred:

- **Bypass via `BYPASSRLS`**: grant `BYPASSRLS` to the app's DSN user so it
  continues to see everything.
- **No bypass, set `app.memberid` per request**: the app sets
  `SET LOCAL app.memberid = '<memberid>'` after authenticating the request, and
  the same RLS policies apply uniformly. The "sysop" path sets
  `app.memberid = -1` (or similar) and policies for sysops `USING (true)`.

The second is the principled answer; the first is the small-blast-radius
answer. Pick one when this is picked up.

### 3. `SET LOCAL app.memberid` per request

PHP side, in `php/database.php` `connect()` (or a new wrapper that the
authenticated code paths use):

```php
$pdo->exec("SET LOCAL app.memberid = " . intval($currentmemberid));
```

Python side, equivalent in the connection pool's `setup` callback so every
borrowed connection gets the GUC set when a request-scoped `app.memberid` is
provided.

### 4. The `pgrole` table's own RLS policy

The original plan had:

```sql
ALTER TABLE engine.pgrole ENABLE ROW LEVEL SECURITY;
CREATE POLICY pgrole_self_select ON engine.pgrole
  FOR SELECT TO web
  USING (memberid = current_setting('app.memberid')::BIGINT);
```

Without `app.memberid` being set by the app, this policy is effectively "no
rows visible" to the `web` role, which would break `psql_credentials.php`.
For the first pass, `engine.pgrole` is therefore read/written only by the
privileged DSN path, and this policy is **not** installed.

When RLS is picked up, install the policy and switch the PHP reader to
`SET LOCAL app.memberid` before querying.

### 5. Grant narrowing for `m_*` roles

In the first pass, `m_*` roles get whatever the
`engine.createpgrole(moniker, plaintext)` function grants — a conservative
default of `SELECT` on most things, write on `engine.__session` self-row and
authored messages. RLS work may need to revisit that grant set: if RLS is the
enforcement mechanism, the grants can stay broad ("USAGE on schema, SELECT on
all tables") and the *policies* do the filtering. If RLS is not used, the
grant set has to be hand-curated per table.

Pick one consistent approach when RLS is picked up; don't leave both partial.

## When to pick this back up

Triggers:

- The first time a member reports being able to see another member's data via
  direct psql.
- The first time a new per-member table is added to the schema (RLS should be
  enabled at table-creation time, not retrofitted).
- When the implementer wants to remove the `web`/`sysop`/`term` DSN users'
  effectively-superuser access.

## Acceptance criteria when picked up

- `psql -U m_jonez -d <db>` connected as a member sees only that member's
  rows in every per-member table.
- `psql -U m_jonez -d <db>` cannot `CREATE` / `DROP` / `ALTER` schema objects.
- The app's privileged DSN user can still see everything (either via
  `BYPASSRLS` or via a sysop policy).
- A new per-member table added to the schema gets `ENABLE ROW LEVEL SECURITY`
  and matching policies in the same migration.
- A regression test exists that connects as a member role and asserts it
  cannot read another member's row.
