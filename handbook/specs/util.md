# bbsengine6.util Specification

> Status: canonical. Updated 2026-09-04.

`bbsengine6.util` is the catch-all utility module: display formatting,
date/time operations, logging, input helpers, file/directory verification,
range operations, SQL resource loading, password hashing, and ANSI
stripping. This document merges the canonical spec with the
`handbook/util.md` function index.

## Thread safety

### Safe

| Function | Notes |
| --- | --- |
| `logentry()` | Handler registration guarded by `threading.Lock` (`_log_lock`). Default `SysLogHandler` lazily initialized on first call. |
| `diceroll()` | Uses `random.SystemRandom()` (`_dice_rng`); thread-safe. |
| `hr()`, `heading()`, `oxfordcomma()`, `pluralize()` | Pure functions. |
| `expandrange()`, `collapserange()`, `rangestr()`, `printr()` | Pure functions. |
| `checksum()` | Pure function. |
| `ltree_to_path()`, `chop_last_element()`, `strip_ansi()`, `path_to_ltree()` | Pure string functions. |
| `serialize_datetimes()`, `tobool()` | Pure functions. |
| `getremoteaddr()`, `getcurrentloginid()` | Read from process environment; no shared state. |
| `verify_dir_exists_writable()`, `verify_file_exists_readable()`, `verify_file_exists_readable_writable()` | Stateless filesystem checks. |
| `timedeltastr()` | Pure function. |
| `encryptpassword()` | Pure (no I/O; bcrypt is internally thread-safe). |

### Not thread-safe

| Function | Notes |
| --- | --- |
| `init()` | Calls `locale.setlocale()` and `time.tzset()`, which mutate global process state. Call once at application startup from the main thread. |

## Locales

`init()` calls `locale.setlocale(locale.LC_ALL, "")`, which reads the
user's locale from `LC_ALL` / `LC_CTYPE` / `LANG`. This drives:

- Date and time formatting via `strftime()` codes like `%x` and `%X`.
- Number formatting (decimal separators, thousands separators).
- Locale-aware string sorting and comparison.

Set the locale **before** any date/time formatting that relies on
locale-specific codes.

On Debian/Ubuntu, install locale packages with:

```bash
apt install locales
dpkg-reconfigure locales
```

## Public API

### Display and formatting

```python
hr(acs=True, width=None, end="\n", color="{boxcolor}") -> bool
heading(title: str, **kwargs) -> None
pluralize(amount: int, singular: str, plural: str, quantity=True, emoji="", determiner="a", **kw) -> str
oxfordcomma(seq, conjunction="and") -> Optional[str]
filedisplay(res, **kw) -> None
```

### Date and time

```python
datestamp(t=None, format="%Y-%m-%d %I:%M%P %Z (%a)") -> str
timedeltastr(delta) -> str
```

`timedeltastr` (formerly `timedelta_`) converts a `datetime.timedelta`
to a compact duration string with only the non-zero units, zero-padded
to two digits:

```python
>>> from datetime import timedelta
>>> timedeltastr(timedelta(days=2, hours=3, minutes=15, seconds=30))
'02d03h15m30s'
```

### Logging

```python
logentry(message, *, level=logging.INFO, handler=None, formatter=None, logger_name="bbsengine6") -> None
```

The default handler is a lazily-initialized `SysLogHandler`. The first
call from a given thread may pay the setup cost; subsequent calls are
fast. String level aliases (`"debug"`, `"info"`, `"warning"`,
`"error"`) are accepted for convenience.

### Input

```python
inputpassword(prompt="password: ", mask="X", **kwargs) -> str
```

### Range operations

```python
collapserange(lst: list) -> list
expandrange(txt: str) -> list
rangestr(ranges) -> str
printr(ranges) -> None
```

`expandrange("1-3,5,7-9")` returns `[1, 2, 3, 5, 7, 8, 9]`. The
`collapserange` / `rangestr` round-trip is the canonical wire format
for page ranges and similar.

### Filesystem

```python
verify_dir_exists_writable(dirname, **kw) -> bool
verify_file_exists_readable(filename, **kw) -> bool
verify_file_exists_readable_writable(filename, **kw) -> bool
```

The legacy camelCase aliases (`verifyDirExistsWritable`,
`verifyFileExistsReadable`, `verifyFileExistsReadableWritable`) remain
as `DeprecationWarning`-emitting shims that call the snake_case forms.

### Password hashing

```python
encryptpassword(plaintextpassword: str) -> str
```

Compute a bcrypt hash locally. Thin wrapper around
`bbsengine6.password.hash_password`. Returns a `$2b$06$...` string of
length 60. This is the single source of truth for new password hashes;
both `member.setpassword` and the legacy alias route through it.

```python
getencryptedpassword(args, plaintextpassword) -> Optional[str]
```

Compatibility wrapper kept as a thin shim over `encryptpassword`. The
`args` parameter is accepted but ignored; new code should call
`encryptpassword` directly.

### Random

```python
diceroll(sides=6, count=1, mode="single")
```

Backed by `random.SystemRandom()`; cryptographically strong.

### Locale init

```python
init(args=None, **kw) -> None
```

Set locale from environment. Call once at application startup, before
any locale-dependent formatting.

### Hashing and string ops

```python
checksum(data: bytes) -> str
tobool(value) -> bool
strip_ansi(s: str) -> str
serialize_datetimes(data: dict) -> dict
```

### ltree helpers

```python
ltree_to_path(ltree: str) -> str
path_to_ltree(path: str) -> str
chop_last_element(ltree: str) -> str
pathToLtree(path: str) -> str
```

`pathToLtree` is a legacy camelCase alias for `path_to_ltree` and is
scheduled for removal; new code should use `path_to_ltree`.

### Environment / runtime

```python
getremoteaddr() -> Optional[str]
getcurrentloginid(args, **kwargs) -> str | None
```

### Path and SQL resource loading

```python
get_safe_path(args, *components, **kwargs) -> str
load_sql(args, resource_name, *, package: Optional[str] = None) -> str
```

`load_sql` reads a `.sql` resource from `bbsengine6.sql` (default) or
the package named in `package=`.

### Encryption (at-rest helpers)

```python
get_encryption_key() -> bytes
encrypt_password(plaintext: str) -> str
decrypt_password(ciphertext_b64: str) -> str
```

These are the at-rest encryption helpers used by the message queue and
similar subsystems; they are distinct from the bcrypt password hashing
above.

### Argv sanitization

```python
sanitize_args(argv)
safe_main(...)
```

`safe_main` wraps `main()` with the canonical argv sanitization pass
that strips DB credentials from `--psql-*` and similar arguments before
they appear in process listings.

## Reference: function index

The names exported from `bbsengine6.util`, mirroring the short index in
`handbook/util.md` (with current names; legacy aliases noted where they
appear in the public surface).

| Function | Purpose |
| --- | --- |
| `hr()`, `heading()`, `pluralize()`, `filedisplay()` | Display formatting |
| `datestamp()`, `timedeltastr()` | Date/time |
| `inputpassword()` | Masked password prompt |
| `oxfordcomma()` | List-to-prose join |
| `logentry()` | Syslog logging |
| `collapserange()`, `expandrange()`, `rangestr()`, `printr()` | Range operations |
| `diceroll()` | Cryptographically strong dice rolls |
| `timedeltastr()` | Human-readable `timedelta` rendering |
| `encryptpassword()` | bcrypt hash (canonical) |
| `init()` | Locale init |
| `checksum()` | Byte-level hash |
| `ltree_to_path()`, `path_to_ltree()`, `chop_last_element()` | ltree conversions |
| `tobool()` | Coerce truthy strings to `bool` |
| `getremoteaddr()`, `getcurrentloginid()` | Environment reads |
| `get_safe_path()`, `load_sql()` | Path / SQL resource loading |
| `serialize_datetimes()` | JSON-friendly datetime flattening |
| `strip_ansi()` | ANSI escape stripping |
| `getencryptedpassword()` | Legacy alias of `encryptpassword` |
| `verify_dir_exists_writable()`, `verify_file_exists_readable()`, `verify_file_exists_readable_writable()` | Filesystem checks |
| `get_encryption_key()`, `encrypt_password()`, `decrypt_password()` | At-rest encryption |

## Dependencies

- `logging`, `logging.handlers` -- Syslog logging
- `os`, `re`, `random`, `threading` -- Standard library utilities
- `datetime` -- Date/time handling
- `dateutil` -- Timezone-aware datetime parsing
- `bcrypt` -- Password hashing (via `bbsengine6.password`)
- `.io`, `.database`, `.input`, `.password` -- Internal BBS engine modules

## Known issues

1. `datestamp()` calls `time.tzset()` on every invocation, which is
   redundant and modifies global state. The init path should set the
   timezone once.
2. `logentry()` string level aliases (`"debug"`, `"info"`, etc.) are
   accepted but an enum would be more type-safe.
