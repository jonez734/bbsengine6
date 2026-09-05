# bbsengine6.member Specification

> Status: canonical. Updated 2026-09-04.

`bbsengine6.member` is the member subsystem: identity lookups,
authentication, credits, flags, groups, and CRUD against the `engine`
namespace. The implementation lives in
`py/src/bbsengine6/member/lib.py` (1802 lines) with a small WebSocket
service in `py/src/bbsengine6/member/api/handler.py`.

The historical `notify` recipient-validation helpers
(`moniker_exists`, `group_exists`, `get_group_members`) now live here
as part of the member subsystem. They were originally written to
validate `@recipient` messaging syntax in the deleted `notify`
package; after Phase 7-10 of the message migration they were kept in
place but relocated from notify to member. See
[`../../TODO-message-migration.md`](../../TODO-message-migration.md) for
the full historical context.

## Database namespace

| Table / function | Purpose |
| --- | --- |
| `engine.member` | Public read view |
| `engine.__member` | Writable base table |
| `engine.map_member_flag` | Member-to-flag mapping |
| `engine.checkflag(membermoniker, flag)` | SQL helper: check one flag |
| `engine.getflags(membermoniker)` | SQL helper: all flags for a member |
| `engine.__notify_group` | Group definitions for recipient expansion |

## Core architecture

### Thread-local caching

`_threadlocal = threading.local()` caches the current member's `id` and
`moniker` per thread to avoid repeated database queries during a
request. Cached in `getcurrentid()` and `getcurrentmoniker()`; cleared
by `clear_current_id_cache()` / `clear_current_moniker_cache()`.

### Pool-first pattern

Most functions accept either `conn=` or `pool=` as a kwarg. If only
`pool` is provided, a connection is acquired via
`database.connect(args, pool=pool)`. This lets callers participate in
an open transaction (pass `conn`) or run a one-shot operation (pass
`pool`).

### Allowed columns

`ALLOWED_MEMBER_COLUMNS` is the 18-column frozenset used by field
validation in the read helpers:

```
id, loginid, moniker, name, email, password, credits, attrs, flags, ui,
refcode, datecreated, createdbyid, dateupdated, updatedbyid,
approvedbyid, dateapproved, lastlogin, lastloginfrom
```

## Public API

### Identity

```python
getcurrentid(args, **kwargs) -> int | None
getcurrentmoniker(args, **kwargs) -> str | None
getcurrent(args, fields="*", **kwargs) -> dict | None
getbyid(args, memberid: int, fields: str = "*", **kwargs) -> dict | None
getbymoniker(args, moniker: str | None = None, fields: str = "*", **kwargs) -> dict | None
count(args, **kwargs) -> int | None
clear_current_id_cache() -> None
clear_current_moniker_cache() -> None
```

`getcurrentid` and `getcurrentmoniker` consult the thread-local cache
before hitting the database. `getbyid` validates the supplied `fields`
list against `ALLOWED_MEMBER_COLUMNS`. `getbymoniker` applies the
timezone conversion to `lastlogin` and falls back to the current
member's moniker when none is supplied.

### Flags

```python
getflags(args, moniker=None, **kwargs) -> dict
checkflag(args, flag: str, moniker: str | None = None, mogrify: bool = False, **kwargs)
setflag(args, name, value, **kwargs) -> bool
_update_member_flags(args, moniker, flags_dict, conn, commit=False) -> bool
```

`getflags` returns a dict mapping flag name to
`{"description": ..., "value": ...}`. `setflag` deletes any existing row
in `engine.map_member_flag` and inserts the new one. Pass `conn=` to
participate in a caller's transaction, `pool=` for standalone use.

`checkflag` raises `KeyError` on unknown flag names and returns `None`
for members with no row in `map_member_flag`.

### Credits

```python
getcredits(args, membermoniker: str | None = None, **kwargs) -> int
setcredits(args, amount: int, moniker: str | None = None, **kwargs)
```

Both fall back to the current member when `moniker` is omitted.
`setcredits` requires a non-negative integer.

### Password

```python
checkpassword(args, plaintextpassword: str, membermoniker: str | None = None, **kwargs)
setpassword(args, plaintextpassword: str, moniker: str, **kwargs)
rehashpassword(args, moniker: str, plaintext: str, **kwargs)
audit_password_hash(args, moniker: str, **kwargs)
audit_password_column(args, **kwargs)
has_password(args, moniker: str, **kwargs) -> bool
_verify_any(plaintext: str, stored: str) -> bool
```

Hashing goes through [`bbsengine6.util.encryptpassword`](./util.md#password-hashing).
`setpassword` writes a fresh bcrypt hash via `database.update(...)`
with `commit=True` (it is the canonical write path). `checkpassword`
verifies a plaintext against the stored hash. `audit_password_hash`
checks whether a stored hash uses an acceptable cost factor; see
`bbsengine6.password.BCRYPT_PREFIX_RE`. `has_password` is `True` iff a
non-empty password is present on the row.

### Attributes

```python
setattrs(args, attrs: dict, moniker=None, **kwargs)
```

Update `engine.__member.attrs` (JSONB). By default merges with
existing attrs (`||`); pass `reset=True` to replace entirely. The
JSONB boundary rules are documented in
[`bestpractices.md`](./bestpractices.md#json-handling-at-the-database-boundary).

### CRUD

```python
build(args, row={}, **kwargs) -> dict
buildrec(member) -> dict
insert(args, member, **kwargs) -> str | False
update(args, member, moniker: str | None = None, **kwargs) -> None
```

`build` applies defaults (credits=100, ui=["term"], flags, ...) and
parses the comma-separated `ui` string into a sorted list.
`buildrec` strips internal fields (`datecreatedepoch`, etc.),
serializes dict/list fields to JSON, and joins the `ui` list to a
string. `buildrec` is the canonical record transformer that callers
hand to `database.update(...)` / `database.insert(...)` -- it must
keep dicts as dicts and never pre-serialize.

`update` and `insert` keep the transaction open (`commit=False`) when
called with `conn=`, then commit atomically after all flag operations
complete. Exceptions propagate so the caller can `conn.rollback()`.

### Validation helpers

```python
verifyMemberNotFound(args, name, *, column: str = "loginid", conn=None, pool=None)
verifyMemberFound(args, name, *, column: str = "loginid", conn=None, pool=None)
```

Both require `pool=` (CONN_POOL_PATTERN). They return `True`/`False` for
the existence check and `None` if no pool was supplied. Default column
is `"loginid"`; pass `column="moniker"` to look up by moniker.

### Moniker and group validation (notify-era, retained)

These three functions were originally written for `@recipient`
messaging syntax validation in the now-deleted `notify` package. They
are retained in `member` because the validation logic is about
identifying members and groups, not about transport.

```python
moniker_exists(args, moniker: str, **kwargs) -> bool | None
```

Validate moniker format and check existence in `engine.member`.

Validation rules:

- Non-empty string.
- No `@` prefix (reserved for messaging syntax).
- No spaces.
- Max 50 characters.
- Printable ASCII only (`0x20`-`0x7E`).

Returns `True` if the moniker exists, `False` if not, `None` on
database error. Raises `ValueError` on invalid format with a
descriptive message.

```python
group_exists(args, group_name: str, **kwargs) -> bool | None
```

Validate group name format and check existence in
`engine.__notify_group`. Same rules as `moniker_exists` but with a
100-character limit instead of 50.

```python
get_group_members(args, group_name: str, **kwargs) -> list[str] | None
```

Recursively expand `group_name`, returning a sorted, unique list of
member monikers.

- Recurses through nested groups.
- Removes duplicates.
- Detects circular references via an internal `_visited` set and
  raises `ValueError("Circular group reference detected: X is already
  being expanded")`.
- Returns `[]` for an empty group (exists but has no members).
- Returns `None` on database error.

Example:

```python
# Expand "ops" which contains alice, bob, charlie
members = member.get_group_members(args, "ops", pool=pool)
# Returns: ["alice", "bob", "charlie"]

# Nested expansion of "all" (contains ops, devs, managers)
members = member.get_group_members(args, "all", pool=pool)
# Returns: flattened unique list of every member under those groups
```

See `handbook/specs/NOTIFY_MESSAGING.md` (the original messaging-system
spec) for the historical context; the live API surface is what is
documented here.

### Security notes

The validation rules in `moniker_exists` and `group_exists` block
several attack patterns:

- `@`-prefixed names like `@alice` cannot be created; this prevents
  abusing `@alice`-style messaging syntax by registering a moniker that
  collides with a recipient prefix.
- Spaces in names would make `alice bob` ambiguous to parse as a single
  recipient; the validation rejects them.
- Printable-ASCII-only prevents encoding tricks (`café`, `alice🎉bob`,
  control characters).
- Length limits block DoS via very long names.

Circular group references are caught early (in the recursive expansion
of `get_group_members`) so a malformed group structure cannot infinite-
loop the messaging layer.

## Transaction management

`insert` and `update` both keep the transaction open when called with
`conn=`, perform all flag operations in order, then commit atomically.
Exceptions propagate so the caller can roll back.

### Moniker-change special case

When `update` is called with a new moniker that differs from the
supplied `moniker` argument:

1. `engine.map_member_flag` is updated to the new moniker explicitly
   (so the FK target exists before `__member` is rewritten).
2. `database.update(..., updatepk=True)` rewrites `engine.__member`
   with the new primary key.
3. PostgreSQL `ON UPDATE CASCADE` propagates the change to all related
   tables.
4. `_update_member_flags` re-applies any flag value changes against the
   new moniker.
5. Single `conn.commit()` makes the whole sequence atomic.

If the moniker is not changing, steps 1 and 2 collapse to a single
`database.update` against the existing PK.

## MemberServiceHandler (WebSocket)

`py/src/bbsengine6/member/api/handler.py` provides the WebSocket surface
for member profile, tier, and referral messages:

| Wire message | Action |
| --- | --- |
| `member_profile` | Look up a member profile |
| `member_update` | Update profile attrs |
| `member_tier` | Get or set the member's tier |
| `member_referral_code` | Return the referral code |
| `member_referrals` | Return referrals made by this member |

`MemberServiceHandler` extends `BaseService` and is registered with the
WebSocket server via the message router. The session id is supplied by
the transport and resolved through `SessionManager`
(see [`auth-bank.md`](./auth-bank.md)).

The integration in `bed` registers the message types from this handler
through `server.register_service(...)`; the actual `bed` registration
code lives in `bed/` and is outside this repo.

## Error handling

- All database operations are wrapped in `try/except` blocks.
- Failures are logged via `io.echo_traceback()` with a location tag
  such as `bbsengine6.member.getcurrentid.180`.
- Pool/connection validation returns `None` or logs an error if
  missing.
- Most functions return `None` on error, `False` for authentication
  failures, or a result on success.

## Constants

| Name | Purpose |
| --- | --- |
| `ALLOWED_MEMBER_COLUMNS` | 18-column frozenset for field validation |
| `_threadlocal` | `threading.local` for per-thread cache |

## Tests

The historical notify-era recipient-validation tests live under
`py/tests/`; the relevant files are:

```bash
pytest bbsengine6/py/tests/test_notify_message_demo_recipient_validation.py -v
pytest bbsengine6/py/tests/test_group_recipient_resolution.py -v
```

These cover moniker and group validation, recursive expansion,
circular-reference detection, and `@`-prefix/space/UTF-8 rejection.

For the migration history of `notify` -> `member.moniker_exists` /
`member.group_exists` / `member.get_group_members`, see
[`../../TODO-message-migration.md`](../../TODO-message-migration.md).
