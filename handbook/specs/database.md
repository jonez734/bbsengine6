# bbsengine6.database Specification

## Overview

`database.py` is a PostgreSQL database utility module providing connection pooling, CRUD operations, schema/role/extension management, and SQL execution helpers for the BBS engine.

## Core Architecture

### Connection Management

- **Connection Pool**: Uses `psycopg_pool.ConnectionPool` with configurable min/max size (default: 10/100)
- **DSN Construction**: `make_dsn()` builds connection string from args or kwargs
- **Context Managers**: `connect()` gets connection from pool; `cursor()` creates dict-row cursors

### Key Patterns

1. **Pool-first**: Most functions accept either `conn` or `pool` kwarg
2. **Nested cursors**: Uses `with cursor(conn) as cur:` pattern
3. **Debug logging**: Many functions support `mogrify=True` for SQL logging (reserved for future use)

### Error Handling

- Pool/connection errors: return `False`
- Database errors: return `False` with `echo_traceback()` for full stack trace
- Return types: consistent `bool` for success/failure operations

## Public API

### Connection Functions

```python
getpool(args: Any, **kwargs: Any) -> ConnectionPool
```
Create connection pool with DSN from args.

---

```python
@contextmanager
connect(args: Any, pool: Any = None, *, auto_commit: bool = True, wrapper: bool = False, **kwargs: Any)
```
Context manager that gets a connection from the passed `pool` using `pool.getconn()`
and returns it via `pool.putconn()` on exit. Raises `ValueError` if `pool is None`.
The `readonly` kwarg is stripped from kwargs (not supported by psycopg_pool). 

**Parameters:**
- `args` - Application args (optional, used for debug logging only)
- `pool` - ConnectionPool instance
- `auto_commit` (default: `True`) - Commit before returning connection to pool
- `wrapper` (default: `False`) - If `True`, yield DatabaseConnection wrapper with method-style API

**Note:** `args` parameter is optional and only used for debug logging. Can be `None` without affecting core functionality.

Use (original):
```python
with database.connect(args, pool=pool) as conn:
    database.cursor(conn)  # or pass conn to other database functions
```

Use (with wrapper):
```python
with database.connect(args, pool=pool, wrapper=True) as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM foo")
    conn.commit()
```

---

```python
cursor(conn: Any, row_factory: Any = dict_row, **kwargs: Any) -> Any
```
Create cursor with dict row factory.

---

```python
transaction(conn: Any, **kwargs: Any) -> Any
```
Context manager for transactions.

---

```python
commit(args: Any, conn: Any = None, **kwargs: Any) -> bool
```
Commit transaction on connection. Returns `True` on success, `False` if no connection.

---

```python
rollback(args: Any, conn: Any = None, **kwargs: Any) -> None
```
Roll back transaction on connection.

### CRUD Operations

```python
update(args: Any, table: str, pk: str, items: dict, **kwargs: Any) -> bool
```
Update rows. 

Kwargs:
- `primarykey` (default: `"id"`) - name of primary key column
- `mogrify` (default: `False`) - log SQL query for debugging
- `updatepk` (default: `False`) - if `True`, allows updating the primary key itself (use with care; required for moniker changes)
- `commit` (default: `True`) - if `True`, commits transaction immediately; if `False`, keeps transaction open

Uses `sql.Identifier()` for table/column names to prevent SQL injection.
Returns `True` on success, `False` on error.

**Note:** When changing a primary key (e.g., member moniker), the calling code must explicitly handle related table updates BEFORE calling this function, to avoid FK constraint violations. The `updatepk=True` parameter is only half the solution; proper transaction ordering is required.

---

```python
insert(args: Any, table: str, items: dict, **kwargs: Any) -> int | bool
```
Insert row.

Kwargs:
- `primarykey` (default: `"id"`) - name of primary key column for `RETURNING` clause
- `returnid` (default: `True`) - if `True`, return inserted ID; if `False`, return `True`
- `mogrify` (default: `True`) - log SQL query for debugging
- `commit` (default: `True`) - if `True`, commits transaction immediately; if `False`, keeps transaction open for caller

Uses `sql.Identifier()` for table/column names to prevent SQL injection.
Returns inserted ID if `returnid=True`, otherwise `True` on success, `False` on error.

**Note:** Pass `commit=False` when inserting as part of a multi-step transaction (e.g., when flags must also be inserted atomically with the parent record).

### Metadata Functions

```python
classexists(args: Any, name: str, **kwargs: Any) -> bool
```
Check if table/view exists via `to_regclass()`.

---

```python
schemaexists(args: Any, name: str, **kwargs: Any) -> bool
```
Check if schema exists in information_schema.

---

```python
functionexists(args: Any, name: str, **kwargs: Any) -> bool
```
Check if function exists in pg_proc.

---

```python
extensionavailable(args: Any, ext: str, **kwargs: Any) -> bool
```
Check if extension is available in pg_available_extensions.

---

```python
extensioninstalled(args: Any, ext: str, **kwargs: Any) -> bool
```
Check if extension is installed in pg_extension.

### Role Management

```python
createrol(args: Any, name: str, **kwargs: Any) -> bool
```
Create role. Uses `sql.Identifier()` for role name to prevent SQL injection.
Kwargs: `login`, `superuser`, `createdb`, `createrole`, `inherit`, `replication`, `password`, `expiration`.

---

```python
rolexists(args: Any, rolname: str, **kwargs: Any) -> bool
```
Check if role exists in pg_roles.

---

```python
get_role_privs(args: Any, rolname: str, cur: Any = None, **kwargs: Any) -> dict | bool
```
Get role privileges via `get_role_privs()` function.
Returns `dict` on success, `False` if pool is `None`.

---

```python
manage_role_privs(args: Any, role_name: str, action: str, priv: str, **kwargs: Any) -> Any
```
Manage role privileges via `manage_role_privs()` function.

---

```python
manage_secondary_role(args: Any, role_name: str, action: str, secondary: str, **kwargs: Any) -> Any
```
Manage secondary roles via `manage_secondary_role()` function.

---

```python
manage_database_priv(args: Any, action: str, priv: str, database_name: str, target_role: str, **kwargs: Any) -> bool
```
Manage database privileges.

---

```python
manage_schema_priv(args: Any, action: str, priv: str, database_name: str, target_role: str, **kwargs: Any) -> bool
```
Manage schema privileges.

### Database/Schema Operations

```python
exists(args: Any, databasename: str, **kwargs: Any) -> bool
```
Check if database exists in pg_catalog.

---

```python
create(args: Any, name: str, **kwargs: Any) -> bool
```
Create database using `CREATE DATABASE` with safe identifier.

---

```python
createschema(args: Any, name: str, **kwargs: Any) -> bool
```
Create schema using `CREATE SCHEMA`.

---

```python
creatextension(args: Any, ext: str, **kwargs: Any) -> bool
```
Create extension with error handling for permission/file issues.

### SQL Execution

```python
execute(cur: Any, query: Any, *params: Any) -> Any
```
Execute query with auto-converted params for safe JSONB encoding. Use this instead of
direct `cur.execute()` when params may contain dicts, lists, datetime objects, or type objects.

---

```python
executemany(cur: Any, operation: str, seq_of_params: list) -> None
```
Execute operation against all parameter sequences with auto-conversion through `convert_for_jsonb()`.
Consistent with `execute()` in handling complex types.

---

```python
importsql(args: Any, filename: str, **kwargs: Any) -> bool
```
Load and execute SQL file. Kwargs: `package` (for SQL directory), `conn`, `pool`.

---

```python
resultiter(cur: Any, arraysize: int = 1000, filterfunc: callable = None, **kwargs: dict) -> Iterator
```
Iterator for memory-efficient result fetching.

---

```python
query(sql_template: str, *params: Any, **kwargs: Any) -> sql.SQL
```
Build a parameterized SQL query from readable string.

**Purpose:** Allows natural-reading SQL like `SELECT * FROM $engine.member WHERE moniker = :moniker` instead of verbose `sql.SQL("...") + sql.Identifier("...")` chains.

**Security:** Table/column names use `sql.Identifier()` for SQL injection protection. Values use parameterized placeholders.

**Syntax:**
- `$schema.table` or `$table` - identifiers (becomes `sql.Identifier('schema', 'table')`)
- `$1, $2` - positional placeholders (passed through to psycopg)
- `:name` - named placeholders (converted to `%(name)s` for psycopg)

**Args:**
- `sql_template` - SQL string with `$identifiers` and placeholders
- `*params` - Positional values for `$1, $2` placeholders
- `**kwargs` - Named values for `:name` placeholders

**Returns:** `sql.SQL` (Composed) object ready for `cursor.execute()`

**Examples:**
```python
# Named placeholders (:name)
cur.execute(database.query("SELECT * FROM $engine.member WHERE moniker = :moniker", moniker="test"))

# Positional placeholders ($1, $2)
cur.execute(database.query("SELECT * FROM $engine.member WHERE moniker = $1", "test"))

# JOINs
cur.execute(database.query("SELECT * FROM $engine.member p JOIN $engine.room r ON p.room_id = r.id WHERE p.moniker = :moniker", moniker="test"))

# Cross-schema queries (e.g., empyre.player)
cur.execute(database.query("SELECT * FROM $empyre.player WHERE moniker = :moniker", moniker="test"))
```

```php
// PHP - Named placeholders (use single quotes to avoid escaping $)
$stmt = \bbsengine6\database\query($dbh, 'SELECT * FROM $engine.member WHERE moniker = :moniker', [":moniker" => "test"]);

// PHP - Positional placeholders
$stmt = \bbsengine6\database\query($dbh, 'SELECT * FROM $engine.member WHERE moniker = $1', ["test"]);

// PHP - DELETE/UPDATE
\bbsengine6\database\query($dbh, 'DELETE FROM $engine.__session WHERE id = :id', [":id" => $sessionid]);

// PHP - JOINs
$stmt = \bbsengine6\database\query($dbh, 'SELECT * FROM $engine.member p JOIN $engine.room r ON p.room_id = r.id WHERE p.moniker = :moniker', [":moniker" => "test"]);
```

### Utility Functions

```python
mogrifysql(cur: Any, query: str, params: tuple) -> str
```
Format query with params for debugging (safe for display only). Uses manual escaping to prevent SQL injection in logs.

---

```python
parse_dsn(dsn: str) -> dict[str, str]
```
Parse DSN string into dict. Skips parts without `=`.

---

```python
make_dsn(args: Any, **kwargs: Any) -> str
```
Build DSN string from args or kwargs. Handles missing args attributes gracefully.

---

```python
getoid(args: Any, typ: str, cur: Any = None) -> int | None
```
Get OID for a PostgreSQL type.

### Argument Parsing

```python
buildargs(parentparser: Any, defaults: dict | None = None, label: str = "database options", suppress: bool = False) -> None
```
Add database arguments to argparse parser. Note: `defaults` uses `None` default to avoid Python mutable default gotcha.

## Constants

- `DEFAULTDATABASE = "postgres"` - Default database for connection checks

## Security

- All user-provided identifiers (table names, column names, role names) use `sql.Identifier()` to prevent SQL injection
- Passwords and expirations are passed as parameterized values

## Known Issues / TODOs

1. `mogrify` kwargs in several functions are reserved for future debug logging use

---

## DB-API 2.0 Compatible Wrapper Classes

The module provides optional wrapper classes that expose a method-style API compatible with Python's DB-API 2.0 specification (PEP 249).

### DatabaseConnection

```python
class DatabaseConnection:
    """Wrapper around psycopg Connection providing DB-API compatible method interface."""
```

A context manager that wraps a psycopg connection with method-style API.

**Properties:**
- `autocommit` (get/set) - Connection autocommit mode

**Methods:**

```python
cursor(row_factory: Any = dict_row) -> DatabaseCursor
```
Return a new cursor using this connection.

```python
commit() -> None
```
Commit pending transaction.

```python
rollback() -> None
```
Roll back current transaction.

```python
close() -> None
```
Return connection to the pool.

**Access to raw connection:**
- `_conn` - The underlying psycopg connection object for advanced use

---

### DatabaseCursor

```python
class DatabaseCursor:
    """Wrapper around psycopg Cursor with auto-conversion and DB-API methods."""
```

Wraps a psycopg cursor with auto-conversion for JSONB and DB-API compatible methods.

**Properties:**

- `description` - Result set column metadata (read-only)
- `rowcount` - Number of rows affected by last execute (read-only)
- `arraysize` - Number of rows to fetch with fetchmany (read/write)
- `rownumber` - Current 0-based index in result set (DB-API extension, read-only)
- `connection` - Reference to parent DatabaseConnection

**Methods:**

```python
execute(operation: str, params: Any = None) -> None
```
Execute operation with auto-conversion of params through `convert_for_jsonb()`.

```python
executemany(operation: str, seq_of_params: list) -> None
```
Execute operation against all parameter sequences with auto-conversion.

```python
fetchone() -> Any
```
Fetch next row.

```python
fetchmany(size: int = None) -> Any
```
Fetch next set of rows. Defaults to arraysize if size not specified.

```python
fetchall() -> Any
```
Fetch all remaining rows.

```python
scroll(value: int, mode: str = "relative") -> None
```
Scroll cursor in result set (DB-API extension). Modes: `"relative"` (default) or `"absolute"`.

```python
nextset() -> bool | None
```
Advance to next result set (optional DB-API).

```python
close() -> None
```
Close cursor.

```python
__iter__()
```
Make cursor iterable.

**Access to raw cursor:**
- `_cursor` - The underlying psycopg cursor object for advanced use

---

### Using Wrapper Classes

```python
# With wrapper=True, connect() yields DatabaseConnection
with database.connect(args, pool=pool, wrapper=True) as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM foo WHERE id = %s", (1,))
    row = cur.fetchone()
    
    # DB-API extensions
    cur.scroll(0, mode='absolute')  # reposition to start
    cur.rownumber  # current position
    
    # Commit via connection method
    conn.commit()

# Or use raw psycopg connection via _conn
with database.connect(args, pool=pool, wrapper=True) as conn:
    raw_conn = conn._conn  # access psycopg connection directly
```

**Note:** The wrapper API coexists with the function-based API. Set `wrapper=False` (default) to use the original behavior.
