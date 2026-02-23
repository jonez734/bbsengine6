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
3. **Debug logging**: Many functions support `mogrify=True` for SQL logging

## Public API

### Connection Functions

```python
getpool(args, **kwargs) -> ConnectionPool
```
Create connection pool with DSN from args.

---

```python
connect(args, **kwargs) -> psycopg.Connection
```
Get connection from pool. Requires `pool` kwarg.

---

```python
cursor(conn, row_factory=dict_row, **kwargs) -> psycopg.Cursor
```
Create cursor with dict row factory.

---

```python
transaction(conn, **kwargs) -> psycopg.Transaction
```
Context manager for transactions.

---

```python
commit(args, **kwargs) -> bool
```
Stub function (currently returns False).

---

```python
rollback(args, conn=None, **kwargs)
```
Roll back transaction on connection.

### CRUD Operations

```python
update(args, table:str, pk:str, items:dict, **kwargs) -> int
```
Update rows. Kwargs: `primarykey`, `mogrify`, `updatepk`, `commit`.

---

```python
insert(args, table:str, items:dict, **kwargs)
```
Insert row. Kwargs: `primarykey`, `returnid`, `mogrify`. Returns ID if `returnid=True`.

### Metadata Functions

```python
classexists(args, name, **kwargs) -> bool
```
Check if table/view exists via `to_regclass()`.

---

```python
schemaexists(args, name, **kwargs) -> bool
```
Check if schema exists in information_schema.

---

```python
functionexists(args, name, **kwargs) -> bool
```
Check if function exists in pg_proc.

---

```python
extensionavailable(args, ext, **kwargs) -> bool
```
Check if extension is available in pg_available_extensions.

---

```python
extensioninstalled(args, ext, **kwargs) -> bool
```
Check if extension is installed in pg_extension.

### Role Management

```python
createrol(args, name, **kwargs) -> bool
```
Create role. Kwargs: `login`, `superuser`, `createdb`, `createrole`, `inherit`, `replication`, `password`, `expiration`.

---

```python
rolexists(args, rolname, **kwargs) -> bool
```
Check if role exists in pg_roles.

---

```python
get_role_privs(args, rolname:str, cur=None, **kwargs) -> dict
```
Get role privileges via `get_role_privs()` function.

---

```python
manage_role_privs(args, role_name, action, priv, **kwargs)
```
Manage role privileges via `manage_role_privs()` function.

---

```python
manage_secondary_role(args, role_name, action, secondary, **kwargs)
```
Manage secondary roles via `manage_secondary_role()` function.

---

```python
manage_database_priv(args, action, priv, database_name, target_role, **kwargs) -> bool
```
Manage database privileges.

---

```python
manage_schema_priv(args, action, priv, database_name, target_role, **kwargs) -> bool
```
Manage schema privileges.

### Database/Schema Operations

```python
exists(args, databasename, **kwargs) -> bool
```
Check if database exists in pg_catalog.

---

```python
create(args, name, **kwargs) -> bool
```
Create database using `CREATE DATABASE` with safe identifier.

---

```python
createschema(args, name, **kwargs)
```
Create schema using `CREATE SCHEMA`.

---

```python
creatextension(args, ext, **kwargs) -> bool
```
Create extension with error handling for permission/file issues.

### SQL Execution

```python
importsql(args, filename, **kwargs) -> bool
```
Load and execute SQL file. Kwargs: `package` (for SQL directory), `conn`, `pool`.

---

```python
resultiter(cur, arraysize:int=1000, filterfunc:callable=None, **kwargs) -> Iterator
```
Iterator for memory-efficient result fetching.

### Utility Functions

```python
mogrifysql(cur, query, params) -> str
```
Format query with params for debugging.

---

```python
parse_dsn(dsn) -> dict
```
Parse DSN string into dict.

---

```python
make_dsn(args, **kwargs) -> str
```
Build DSN string from args or kwargs.

---

```python
getoid(args, typ, cur=None)
```
Get OID for a PostgreSQL type.

### Argument Parsing

```python
buildargs(parentparser:object, defaults:dict={}, label="database options", suppress=False)
```
Add database arguments to argparse parser.

## Constants

- `DEFAULTDATABASE = "postgres"` - Default database for connection checks

## Known Issues / TODOs

1. `commit()` function is a stub returning False - not implemented
2. Some functions return `None` on error instead of raising exceptions
3. `mogrify` kwargs in several functions are reserved for future debug logging use
