# bbsengine6 zoid6 role — next-release follow-up

This TODO captures the items that the dedicated `zoid6` owner role
introduces but does not complete in the current release. Track
each item and close them in the next release that touches this
area.

## Status of items shipped this release

- `zoid6` role created in `stage_zero.checkzoid6role`
  (`NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN INHERIT`).
- Ownership of the five `public.*` SECURITY DEFINER helpers
  reassigned to `zoid6` in `stage_zero.checkzoid6owner` (idempotent,
  verbose on first run).
- `engine` schema owned by `zoid6` (created with `AUTHORIZATION
  zoid6`; existing schemas reassigned inline in `checkengine`).
- `backend.checkengine` allow-list is `("zoid6", "postgres")` —
  `"postgres"` is intentionally kept for this release to cover
  databases where the helpers were created via the previous
  `SET ROLE postgres` SQL pattern.

## Open items

### 1. Drop `"postgres"` from `acceptable_owners`

**Where:** `bbsengine6/py/src/bbsengine6/backend/checkengine.py:57`
(`acceptable_owners = ("zoid6", "postgres")`).

**Why:** the `"postgres"` entry is a transition aid only. Including
the cluster superuser in the SECURITY DEFINER owner allow-list
weakens the gate — anyone able to replace or alter a helper owned
by `postgres` inherits full superuser. Once all in-the-wild
databases have been bootstrapped through `stage_zero` at least
once (and thus had their helpers reassigned to `zoid6`), drop
`"postgres"` so the allow-list is `("zoid6",)`.

**How to verify it's safe to drop:** run
`SELECT proname, pg_get_userbyid(proowner) FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname='public' AND proname IN ('manage_schema_priv',
'manage_database_priv','manage_role_privs',
'manage_secondary_role','get_role_privs');`
on every known production DB and confirm every row's owner is
`zoid6`. If any are still `postgres`, re-run the bootstrap
(`make reassign-bootstrap-owners` in zoid6, or just re-run
`stage_zero`).

### 2. Drop `SET ROLE postgres` / `RESET ROLE` from
`manage_schema_priv.sql`

**Where:** `bbsengine6/py/src/bbsengine6/sql/manage_schema_priv.sql`
(top of file).

**Why:** with `zoid6` as the canonical owner, the
`SET ROLE postgres` block is dead code. It was originally used to
make `postgres` the immediate creator/owner of the function; that
role is no longer the canonical owner. The block also creates a
chicken-and-egg dependency: `CREATE FUNCTION` is performed by
whichever role is `current_user` after the `SET ROLE`, and
`postgres` is required to be a superuser for that to succeed. Once
item 1 is closed, delete the `SET ROLE postgres` and
`RESET ROLE` lines and the explanatory comment, and let the
connecting bootstrap superuser (e.g. `jam`) create the function —
`checkzoid6owner` will reassign ownership to `zoid6` immediately
after.

**Marker comment:** the SQL file already carries a
`TODO(remove-after-postgres-drop)` block at the top of the file.
Remove the lines under that marker once item 1 is closed.

### 3. ~~Consider extending `checkzoid6owner.py` to also reassign
the `bank` schema~~ DONE — now handled by `checkbank.py`

**Where:** `bbsengine6/py/src/bbsengine6/backend/checkbank.py`
(new `_ensure_zoid6_owner` block).

**Why this was originally deferred:** `bank` schema grants live
in `bank_schema.sql` and are issued by the bootstrap superuser
directly, so `bank` did not strictly need to be `zoid6`-owned for
the existing grant path.

**Why it landed anyway:** per the operator directive ("we should
be using `zoid6`, not `opencode`"), all BBS-owned schemas should
have `zoid6` as their canonical owner. The block mirrors the
engine schema block in `checkengine` and the casino schema block
in `casino.startup.checkcasino`. It is idempotent (no-op when
`bank` is already `zoid6`-owned) and runs after `bank_schema.sql`
is imported, so the schema exists by the time the ALTER runs.

**Done in:** bbsengine6 submodule commit
`fix(bbsengine6): reassign SECURITY DEFINER helpers AND bank
schema to zoid6 in stage_one`.

### 4. Cross-module schema ownership pattern

**Where:** every BBS submodule whose `sql/schema.sql` is executed
by `manage_schema_priv` (or any other `zoid6`-owned SECURITY
DEFINER helper) under NOSUPERUSER — currently `casino`, plus any
future submodule that follows the same pattern.

**Why:** once `manage_schema_priv` is owned by `zoid6`
(NOSUPERUSER), it can only `GRANT` on objects that `zoid6` owns.
For a `<module>.sql` that runs `GRANT USAGE ON SCHEMA <module>
TO ...`, the schema itself must be owned by `zoid6`. Without
this, the helper fails with `permission denied for schema <name>`
during `stage_zero` / the module's startup.

**Pattern:** each submodule ships its own mirror of
`bbsengine6.backend.checkengine`'s schema-ownership block, named
`<module>.startup.check<module>` (see `casino.startup.checkcasino`
for the reference implementation). The mirror:

1. Issues `CREATE SCHEMA IF NOT EXISTS <name> AUTHORIZATION zoid6`
   for fresh installs.
2. Falls back to `ALTER SCHEMA <name> OWNER TO zoid6` for
   existing schemas owned by someone else.
3. Is idempotent (no-op when the schema is already `zoid6`-owned).

The mirror is invoked from the submodule's startup `main` after
extension install and before the schema.sql import.

**Bootstrap interaction (casino-specific, but illustrative):**
`casino/sql/bootstrap_zoid6.sql` (formerly `bootstrap_opencode.sql`)
issues `ALTER SCHEMA ... OWNER TO zoid6` for the `bank`, `engine`,
and `casino` schemas (`bootstrap_zoid6.sql:60-95`). It is therefore
complementary to the `<module>.startup.check<module>` mirrors
above, not in conflict with them: running the bootstrap after
`casino.startup.main` no longer undoes `checkcasino`'s reassignment,
because both target `zoid6`. The historical re-run-on-bootstrap
fallback documented in `casino/TODO.md` is no longer required.

## Out of scope (do not touch)

- The `engine` schema `AUTHORIZATION zoid6` change is intentional
  and stays. `zoid6` is NOSUPERUSER and can only GRANT on objects
  it owns; without this, every grant in the loop fails with
  `permission denied for schema engine` once the helpers are
  owned by `zoid6`.
- The `import getpass` line that was in `checkengine.py` was
  removed because the new allow-list is hard-coded. Do not
  reintroduce it; `getpass.getuser()` makes the trusted owner
  non-deterministic.
