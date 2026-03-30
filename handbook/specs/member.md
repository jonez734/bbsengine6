# bbsengine6.member Specification

## Overview

`member.py` provides member (user) management for the BBS engine, including identity lookups, authentication, credits, flags, and CRUD operations against PostgreSQL.

Database namespace: `engine`
- Primary table: `engine.member` (public view)
- Internal table: `engine.__member` (writable)
- Flags mapping: `engine.map_member_flag`
- Flag functions: `engine.checkflag()`, `engine.getflags()`

## Core Architecture

### Thread-Local Caching

`_threadlocal` (threading.local) caches the current member's `id` and `moniker` per thread to avoid repeated database queries during a request:

```python
_threadlocal = threading.local()
```

Cached in: `getcurrentid()`, `getcurrentmoniker()`

### Pool-First Pattern

Most functions accept either `conn` or `pool` as a kwarg. If only `pool` is provided, a connection is acquired temporarily. This allows both connection-reuse (pass `conn`) and standalone operation (pass `pool`).

### Member Fields

`ALLOWED_MEMBER_COLUMNS` defines the 18 allowed columns for field validation:

```
id, loginid, moniker, name, email, password, credits, attrs, flags, ui,
refcode, datecreated, createdbyid, dateupdated, updatedbyid, approvedbyid,
dateapproved, lastlogin, lastloginfrom
```

## Public API

---

```python
getcurrentid(args, **kwargs) -> int | None
```
Get the current member's numeric ID. Checks thread-local cache first, then queries `engine.member` by `loginid`.

---

```python
getcurrentmoniker(args, **kwargs) -> str | None
```
Get the current member's moniker. Checks thread-local cache first, then queries `engine.member` by `loginid`.

---

```python
getcurrent(args, fields="*", **kwargs) -> dict | None
```
Get the full current member record. Calls `getcurrentid()`, then `getbyid()`.

---

```python
getbyid(args, memberid: int, fields: str = "*", **kwargs) -> dict | None
```
Get a member record by numeric ID. Validates fields against `ALLOWED_MEMBER_COLUMNS`. Returns `None` if no row found.

---

```python
getbymoniker(args, moniker: str | None = None, fields: str = "*", **kwargs) -> dict | None
```
Get a member record by moniker. Applies timezone conversion to `lastlogin`. Falls back to current moniker if none provided.

---

```python
getflags(args, moniker=None, **kwargs) -> dict
```
Retrieve all flags for a member via `engine.getflags()`. Returns `dict` mapping flag name to `{"description": ..., "value": ...}`.

---

```python
checkflag(args, flag: str, moniker: str | None = None, mogrify: bool = False, **kwargs)
```
Check if a specific flag is set for a member via `engine.checkflag()`. Returns the flag value or `None`.

---

```python
_update_member_flags(args, moniker, flags_dict, conn, commit=False) -> bool
```
Helper function to manage member flags in `engine.map_member_flag`. For each flag in `flags_dict`, calls `setflag()` to delete existing entry (if any) and insert new one. Returns `True` on success, `False` on error (with traceback logging). Pass `commit=False` to keep transaction open for caller; `commit=True` to commit immediately.

Used internally by `insert()` and `update()` to handle flag operations as part of a transaction.

---

```python
setflag(args, name, value, **kwargs)
```
Set a flag for a member by inserting/updating `engine.map_member_flag`. Deletes existing row then inserts new one. Kwargs: `moniker`, `mogrify`, `conn`. Pass `conn` to participate in caller's transaction; pass `pool` for standalone operation.

---

```python
getcredits(args, membermoniker: str | None = None, **kwargs) -> int | None
```
Get a member's credits balance. Falls back to current member if moniker not provided.

---

```python
setcredits(args, amount: int, moniker: str | None = None, **kwargs)
```
Set a member's credits balance. Amount must be non-negative integer. Falls back to current member if moniker not provided.

---

```python
checkpassword(args, plaintextpassword: str, membermoniker: str | None = None, **kwargs)
```
Verify a plaintext password against the stored bcrypt hash. Uses `crypt()` comparison.

---

```python
setpassword(args, plaintextpassword: str, moniker: str, **kwargs)
```
Set or change a member's password. Hashes using `crypt(gen_salt('bf'))`.

---

```python
setattrs(args, attrs: dict, moniker=None, **kwargs)
```
Update member attributes (JSONB). By default merges with existing attrs (`||`). Pass `reset=True` to replace entirely.

---

```python
update(args, member, moniker: str | None = None, **kwargs) -> None
```
Update a member record in `engine.__member`. Handles moniker changes as a special case:
- If moniker is being changed (old moniker parameter ≠ new moniker in member dict):
  * Explicitly UPDATE `engine.map_member_flag` records to new moniker FIRST
  * Then update `engine.__member` with `updatepk=True` to allow primary key change
  * PostgreSQL CASCADE constraints automatically handle other related tables
- If moniker is NOT changing:
  * Updates `engine.__member` normally
- Always calls `_update_member_flags()` after updating member record to handle any flag value changes

Removes `password` and `flags` from record before writing. Requires `conn` kwarg. Always commits transaction (commit=False is used internally). Returns `None` on success, `None` on error (with traceback logging).

---

```python
insert(args, member, **kwargs) -> str | False
```
Insert a new member. Removes `flags`, `attrs`, and `id` from record before inserting. Uses `engine.__member` by default.

If `conn` is provided, keeps transaction open (`commit=False`) and explicitly commits after flags are inserted, allowing caller to rollback on error. If no `conn` is provided, auto-commits per default `database.insert()` behavior.

Calls `_update_member_flags()` after member insert to handle flag creation. Returns new moniker on success, `False` on error.

---

```python
verifyMemberNotFound(args, name, column: str = "loginid", **kwargs)
```
Return `True` if no member exists with the given name/column. Used for validation before creation.

---

```python
verifyMemberFound(args, name, **kwargs)
```
Return `True` if a member exists with the given name. Column defaults to `loginid`.

---

```python
count(args, **kwargs) -> int | None
```
Return the total number of members in `engine.member`.

---

```python
build(args, row={}, **kwargs) -> dict
```
Build a normalized member record from a database row. Applies defaults (credits=100, ui=["term"], flags, etc.) and parses `ui` string into sorted list.

---

```python
buildrec(member) -> dict
```
Convert a member dict to insert/update format. Strips internal fields (`datecreatedepoch`, etc.), serializes dict/list fields to JSON, joins `ui` list to string.

## Constants

- `ALLOWED_MEMBER_COLUMNS` -- frozenset of 18 allowed member columns for field validation
- `_threadlocal` -- threading.local instance for thread-local caching

## Error Handling

- All database operations are wrapped in try/except
- Failures log via `io.echo_traceback()` with a location tag (e.g., `bbsengine6.member.getcurrentid.180`)
- Pool/connection validation returns `None` or logs an error
- Most functions return `None` on error, `False` for authentication failures, or a result on success

## Transaction Management

### Overview

Member operations (`insert()` and `update()`) maintain database consistency through atomic transactions:
- Both functions keep transactions open when `conn` is provided (use `commit=False` internally)
- Both functions explicitly commit after ALL operations complete (member + flags)
- Exceptions propagate to caller, allowing rollback on error
- All foreign key constraints on `__member.moniker` are set to `ON UPDATE CASCADE`

### Moniker Changes (Special Case)

When changing a member's moniker via `update()`:

1. **Explicit map_member_flag cascade**: Before updating `__member`, explicitly UPDATE `engine.map_member_flag` records to new moniker
   - Prevents FK constraint violation that would occur if flags were updated after the `__member` record
   - Uses properly quoted SQL with `psycopg.sql.SQL()` for safety

2. **Primary key update**: Call `database.update()` with `updatepk=True` to allow updating the moniker PK

3. **Flag value changes**: Call `_update_member_flags()` for any flag value changes using the new moniker

4. **Atomic commit**: Single `conn.commit()` at end ensures all operations (flag cascade + member update + flag value changes) complete together or roll back together

### Example Transaction Flow

**For moniker change `"alice" → "alicia"`:**
```
1. UPDATE map_member_flag SET moniker='alicia' WHERE moniker='alice'
2. UPDATE __member SET moniker='alicia', ... WHERE moniker='alice'
   (CASCADE ON UPDATE automatically updates all other related tables)
3. (Optional) INSERT/UPDATE flags for new moniker if values changed
4. conn.commit()
```

All four steps are atomic. If any step fails, caller can `conn.rollback()`.

### Non-Moniker Updates

For updates that don't change moniker:
```
1. UPDATE __member SET ... WHERE moniker=X
2. (Optional) INSERT/UPDATE flags if values changed
3. conn.commit()
```

All steps are atomic.

## Known Issues / TODOs

None currently.
