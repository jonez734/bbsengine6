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
setflag(args, name, value, **kwargs)
```
Set a flag for a member by inserting/updating `engine.map_member_flag`. Deletes existing row then inserts new one.

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
update(args, member, moniker: str | None = None, **kwargs)
```
Update a member record in `engine.__member`. Also updates individual flags via `setflag()`. Removes `password` and `flags` from record before writing.

---

```python
insert(args, member, **kwargs)
```
Insert a new member. Removes `flags`, `attrs`, and `id` from record before inserting. Uses `engine.__member` by default.

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

## Known Issues / TODOs

None currently.
