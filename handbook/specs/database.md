# bbsengine6.database Specification

> Status: canonical. Updated 2026-09-04.

`bbsengine6.database` owns the PostgreSQL connection pool, DSN handling,
schema/role/extension inspection, and the helper API that every other module
uses to talk to the database. This document merges the canonical spec with
the `handbook/database.md` function index.

## Contents

- [Connection pool](#connection-pool)
- [DSN parsing](#dsn-parsing)
- [Metadata checks](#metadata-checks)
- [Role management](#role-management)
- [Connection helpers](#connection-helpers)
- [DDL helpers](#ddl-helpers)
- [Result helpers](#result-helpers)
- [JSON bridge](#json-bridge)
- [SECURITY DEFINER ownership](#security-definer-ownership)
- [DB-API 2.0 wrapper classes](#db-api-20-wrapper-classes)
- [Argument parsing](#argument-parsing)
- [Reference: function index](#reference-function-index)

## Connection pool

```python
getpool(args, **kwargs) -> ConnectionPool
```

Create a connection pool from the DSN implied by `args`. Internally calls
`parse_dsn` and `make_dsn`. The pool is process-local and cached; repeated
calls return the same object until `reset_pool_cache()` is called.

The default pool is `min_size=10`, `max_size=100`; both bounds are
overridable through `args` or kwargs.

```python
@contextmanager
connect(args, pool=None, *, auto_commit=True, wrapper=False, set_role=None, **kwargs)
```

Context manager that borrows a connection from `pool` via `pool.getconn()`
and returns it via `pool.putconn()` on exit. `auto_commit=False` is required
for multi-statement transactions.

`set_role` is the per-transaction role-switch entry point: when supplied,
`connect` validates the role exists in `pg_roles`, then runs
`SET LOCAL ROLE <set_role>` after acquiring the connection. The role
reverts automatically at transaction end. The DSN user must be a member of
the target role (or a superuser). This is the path used for the
`SET LOCAL ROLE member` request-scoped role switch documented in
[`pg-ident-auth.md`](./pg-ident-auth.md).

```python
with database.connect(args, pool=pool, set_role="member") as conn:
    cur = conn.cursor(row_factory=dict_row)
    cur.execute("SELECT * FROM engine.member ...")
```

If `pool` is `None`, `connect` raises `ValueError`. The optional `args`
parameter is used only for debug logging; the function tolerates `args=None`.

## DSN parsing

```python
parse_dsn(dsn: str) -> dict[str, str]
```

Parse a DSN string into a dict of `key=value` pairs. Skips parts that
lack an `=` (so libpq URI-style prefixes like `postgres://` pass through
intact).

```python
make_dsn(args, **kwargs) -> str
```

Build a DSN string from `args` attributes (or supplied kwargs). Handles
missing `args` attributes gracefully by omitting them from the result.

```python
mogrifysql(cur, query, params) -> str
```

Render a query with params for display in debug output. Uses manual
escaping so the rendered string is safe to print in logs but is **not**
safe to re-execute.

## Metadata checks

All checks return `bool`. They run against the catalog (`pg_*` and
`information_schema`) and require either a `conn` or `pool` kwarg.

| Function | Catalog probe |
| --- | --- |
| `classexists(args, name)` | `to_regclass()` on a table or view |
| `schemaexists(args, name)` | `information_schema.schemata` |
| `typeexists(args, name)` | `pg_type` |
| `tableexists(args, schema, table)` | `information_schema.tables` |
| `functionexists(args, name)` | `pg_proc` |
| `constraintexists(args, ...)` | `pg_constraint` |
| `extensionavailable(args, ext)` | `pg_available_extensions` |
| `extensioninstalled(args, ext)` | `pg_extension` |
| `exists(args, databasename)` | `pg_database` |

The four `*exists` helpers short-circuit when no `conn`/`pool` is
supplied and return `False` with an `io.echo_traceback()` log line.

## Role management

```python
createrol(args, name, **kwargs) -> bool
```

Create a role. Identifier-safe via `sql.Identifier()`. Recognized kwargs:
`login`, `superuser`, `createdb`, `createrole`, `inherit`, `replication`,
`password`, `expiration`.

```python
rolexists(args, rolname) -> bool
```

Check `pg_roles`.

```python
set_current_role(role)        # process-wide role for subsequent connects
get_current_role() -> str | None
```

Module-level helpers used by `connect()` when `set_role=` is not passed
explicitly.

```python
switch_role(args, role_name, **kwargs) -> bool
```

Persistent role switch across statements (uses `SET ROLE`, not `SET LOCAL ROLE`).
Most callers should pass `set_role=` to `connect()` instead so the role
reverts at transaction end.

```python
set_role(args, role_name, **kwargs) -> bool
```

Apply `SET ROLE` on the supplied connection. Returns `True` on success.

The remaining helpers in this section are SECURITY DEFINER and are
discussed under [SECURITY DEFINER ownership](#security-definer-ownership):

- `get_role_privs`
- `manage_role_privs`
- `manage_secondary_role`
- `manage_database_priv`
- `manage_schema_priv`

## Connection helpers

```python
cursor(conn=None, row_factory=dict_row, **kwargs) -> Cursor
```

Return a cursor with `dict_row` factory by default. If `conn=None`,
attempts to acquire from `pool=` or fall back to `getpool(args)`.

```python
transaction(conn, **kwargs)
```

Context manager wrapping `conn.transaction()`. Provided so callers can
use the same keyword in both `with database.connect(...)` and
`with database.transaction(conn)` blocks.

```python
execute(cur, query, *params)
executemany(cur, operation, seq_of_params)
```

Execute with auto-conversion of params through `convert_for_jsonb`. Use
these instead of raw `cur.execute()` whenever params may contain dicts,
lists, datetimes, or type objects. `executemany` is consistent with
`execute` for complex types.

```python
query(sql_template, *params, **kwargs) -> sql.SQL
```

Build a parameterized `sql.SQL` (Composed) object from a readable template.

| Token | Meaning |
| --- | --- |
| `$schema.table` or `$table` | Identifier (becomes `sql.Identifier('schema', 'table')`) |
| `$1`, `$2` | Positional placeholders, passed through to psycopg |
| `:name` | Named placeholders, converted to `%(name)s` for psycopg |

Example:

```python
cur.execute(
    database.query(
        "SELECT * FROM $engine.member WHERE moniker = :moniker",
        moniker="alice",
    )
)
```

The PHP-side equivalent is `\bbsengine6\database\query($dbh, '...', $params)`
with identical syntax.

```python
getoid(args, typ, cur=None) -> int | None
```

Look up a type's OID. Pass a cursor for use inside an existing transaction.

## DDL helpers

```python
create(args, name, **kwargs) -> bool
exists(args, databasename) -> bool
createschema(args, name, **kwargs) -> bool
creatextension(args, ext, **kwargs) -> bool
importsql(args, filename, **kwargs) -> bool
verify_function_owner(args, name, expected_owners, **kwargs) -> bool
```

`importsql` loads a file from the engine SQL package (default) or the
package named in `package=`, splits on `;`, and executes each statement.
`kwargs` accepts `conn=` and `pool=`; if both are missing, `importsql`
raises `ValueError`.

`verify_function_owner` is the runtime guard for SECURITY DEFINER
helpers: it checks `pg_proc.proowner` against the supplied
`expected_owners` (a string or a tuple) and returns `False` (with an
`io.echo` error log) if the function is missing or owned by another
role. See [SECURITY DEFINER ownership](#security-definer-ownership) for
the canonical allow-list.

## Result helpers

```python
commit(args, conn=None, **kwargs) -> bool
rollback(args, conn=None, **kwargs) -> None
update(args, table, pk, items, **kwargs) -> bool
upsert(args, table, conflict_target, items, **kwargs) -> bool
insert(args, table, items, **kwargs) -> int | bool
```

`update`/`insert`/`upsert` apply `convert_for_jsonb` to each value
internally; callers pass plain Python dicts. See
[`bestpractices.md`](./bestpractices.md) for the boundary rules.

`update` kwargs:

| Key | Default | Meaning |
| --- | --- | --- |
| `primarykey` | `"id"` | Name of the primary key column |
| `mogrify` | `False` | Reserved for debug SQL logging |
| `updatepk` | `False` | Allow updating the PK itself (required for moniker changes; transaction ordering is the caller's responsibility) |
| `commit` | `True` | Commit immediately; pass `commit=False` for multi-step transactions |

`insert` returns the inserted ID when `returnid=True` (default) and `True`
when `returnid=False`. `commit=False` keeps the transaction open so the
caller can roll back on error.

`upsert` requires a `conflict_target=` argument naming the columns of a
unique constraint; on conflict it sets the listed columns to the supplied
values and returns `True`.

## JSON bridge

```python
convert_for_jsonb(v, *, wrap: bool = True) -> Any
```

Convert Python objects to psycopg3 types for safe JSONB encoding. The
top-level dict/list is wrapped in `psycopg.types.json.Jsonb`; inner
dicts/lists are returned as plain Python objects so psycopg's dumper
can serialize the outer `Jsonb` without tripping the `Object of type
Jsonb is not JSON serializable` error. `wrap=False` is intended for
internal recursion; callers should use the default.

Datetimes become ISO strings. Unknown non-serializable types are
converted via `str()` and logged at debug level.

For end-to-end examples of the layer responsibilities (application
keeps dicts as dicts, `database.update` calls `convert_for_jsonb`
internally), see
[`bestpractices.md`](./bestpractices.md#json-handling-at-the-database-boundary).

## SECURITY DEFINER ownership

The five privilege-management helpers are `SECURITY DEFINER` functions
installed in the `public` schema by the engine SQL package:

| Function | SQL file |
| --- | --- |
| `get_role_privs` | `sql/get_role_privs.sql` |
| `manage_role_privs` | `sql/manage_role_privs.sql` |
| `manage_secondary_role` | `sql/manage_secondary_role.sql` |
| `manage_database_priv` | `sql/manage_database_priv.sql` |
| `manage_schema_priv` | `sql/manage_schema_priv.sql` |

They are owned by the dedicated unprivileged PostgreSQL role `zoid6`:

```sql
NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN INHERIT
```

`zoid6` is created by `backend.checkzoid6role` and enforced at bootstrap
by `backend.checkzoid6owner`, which runs `ALTER FUNCTION ... OWNER TO
zoid6` against the five helpers if ownership has drifted.

`database.verify_function_owner` is the runtime guard. It rejects
bootstrap if any of the five is owned by a role outside the hard-coded
allow-list `("zoid6", "postgres")`. The `postgres` entry is a one-release
transition aid; it will be dropped in a subsequent release. See
`bbsengine6/TODO_zoid6_role.md`.

Because the helpers are now NOSUPERUSER-owned, the `engine` schema is
created with `AUTHORIZATION zoid6` on fresh installs and reassigned via
`ALTER SCHEMA engine OWNER TO zoid6` on BC upgrades. The `bank` schema
is unaffected: its grants live in `bank_schema.sql`, executed by the
bootstrap superuser.

For per-member role provisioning (the `l_<loginid>` pattern used by the
ident-based psql flow), see [`pg-ident-auth.md`](./pg-ident-auth.md).
The `l_<loginid>` and `m_<moniker>` patterns are distinct: `zoid6` is
the SECURITY DEFINER ownership role, the per-member roles are
LOGIN-capable end-user identities.

## DB-API 2.0 wrapper classes

The module provides optional DB-API 2.0 (PEP 249) wrapper classes
exposing a method-style API. The wrapper coexists with the
function-based API; set `wrapper=False` (default) to use the original
behaviour.

### DatabaseConnection

Wraps a psycopg connection with method-style access. Yields from
`connect(..., wrapper=True)`.

| Member | Meaning |
| --- | --- |
| `autocommit` (property) | Connection autocommit mode |
| `_set_role` (attr) | The role name passed via `set_role=` (or `None`) |
| `_conn` (attr) | The raw psycopg connection |
| `cursor(row_factory=dict_row)` | Return a `DatabaseCursor` |
| `commit()` | Commit pending transaction |
| `rollback()` | Roll back current transaction |
| `close()` | Return connection to pool |

### DatabaseCursor

Wraps a psycopg cursor with auto-conversion and DB-API extensions.

| Member | Meaning |
| --- | --- |
| `description` | Column metadata (read-only) |
| `rowcount` | Rows affected by last execute (read-only) |
| `arraysize` | Rows per `fetchmany` (read/write) |
| `rownumber` | Current 0-based index (DB-API extension, read-only) |
| `connection` | Reference to parent `DatabaseConnection` |
| `execute(op, params=None)` | Execute with auto-conversion |
| `executemany(op, seq_of_params)` | Execute against all sequences with auto-conversion |
| `fetchone()` | Next row |
| `fetchmany(size=None)` | Next set of rows |
| `fetchall()` | All remaining rows |
| `scroll(value, mode="relative")` | Reposition cursor (`"relative"` or `"absolute"`) |
| `nextset()` | Advance to next result set |
| `close()` | Close cursor |
| `__iter__()` | Iterate |
| `_cursor` | The raw psycopg cursor |

Example:

```python
with database.connect(args, pool=pool, wrapper=True) as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM foo WHERE id = %s", (1,))
    row = cur.fetchone()
    cur.scroll(0, mode="absolute")
    conn.commit()
```

## Argument parsing

```python
buildargs(parentparser, defaults=None, label="database options", suppress=False)
```

Add the database argparse arguments (`--dbhost`, `--dbport`, `--dbname`,
`--dbuser`, ...) to `parentparser`. `defaults` defaults to `None`
(sentinel), avoiding the Python mutable-default gotcha.

## Constants

| Name | Value |
| --- | --- |
| `DEFAULTDATABASE` | `"postgres"` |

## Security

- All user-provided identifiers (table names, column names, role names)
  use `sql.Identifier()` to prevent SQL injection.
- Passwords, expirations, and `convert_for_jsonb` payloads are passed
  as parameterized values.
- `verify_function_owner` is the runtime guard against owner drift on
  SECURITY DEFINER helpers.

## Reference: function index

The following names are exported from `bbsengine6.database`. This
duplicates the short index in `handbook/database.md` for in-doc
lookup.

| Function | Purpose |
| --- | --- |
| `getpool()` | Acquire the process-local `ConnectionPool` |
| `connect()` | Context manager: borrow connection from pool |
| `cursor()` | Dict-row cursor factory |
| `transaction()` | Transaction context manager |
| `commit()`, `rollback()` | Transaction terminators |
| `update()`, `insert()`, `upsert()` | CRUD on a single row |
| `execute()`, `executemany()` | Auto-converting parameter execution |
| `query()` | `$ident` / `:name` template builder |
| `getoid()` | Type OID lookup |
| `resultiter()` | Memory-efficient row iterator |
| `buildargs()` | Argparse integration |
| `parse_dsn()`, `make_dsn()`, `mogrifysql()` | DSN helpers |
| `classexists()`, `schemaexists()`, `typeexists()`, `tableexists()` | Catalog probes |
| `functionexists()`, `constraintexists()` | Catalog probes |
| `extensionavailable()`, `extensioninstalled()` | Extension probes |
| `create()`, `exists()` | Database lifecycle |
| `createschema()`, `creatextension()`, `importsql()` | Schema/extension/SQL-file DDL |
| `createrol()`, `rolexists()`, `set_role()`, `switch_role()` | Role lifecycle |
| `set_current_role()`, `get_current_role()` | Process-wide role tracking |
| `get_role_privs()`, `manage_role_privs()`, `manage_secondary_role()`, `manage_database_priv()`, `manage_schema_priv()` | SECURITY DEFINER helpers (owned by `zoid6`) |
| `verify_function_owner()` | Runtime owner allow-list gate |
| `convert_for_jsonb()` | JSONB bridge |
