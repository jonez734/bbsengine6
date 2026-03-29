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
connect(args: Any, pool: Any = None, **kwargs: Any)
```
Context manager that gets a connection from the passed `pool` using `pool.getconn()`
and returns it via `pool.putconn()` on exit. Raises `ValueError` if `pool is None`.
The `readonly` kwarg is stripped from kwargs (not supported by psycopg_pool). Use:
```python
with database.connect(args, pool=pool) as conn:
    database.cursor(conn)  # or pass conn to other database functions
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
importsql(args: Any, filename: str, **kwargs: Any) -> bool
```
Load and execute SQL file. Kwargs: `package` (for SQL directory), `conn`, `pool`.

---

```python
resultiter(cur: Any, arraysize: int = 1000, filterfunc: callable = None, **kwargs: dict) -> Iterator
```
Iterator for memory-efficient result fetching.

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
