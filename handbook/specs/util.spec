# bbsengine6.util Specification

## Summary

`util.py` provides general-purpose utility functions for the BBS engine: display formatting, date/time operations, logging, input helpers, file/directory verification, range operations, SQL resource loading, password hashing, and ANSI stripping.

## Brief Description

A catch-all module of ~30 utility functions used across the BBS engine. Functions fall into categories: UI helpers, date/time utilities, logging, file operations, password handling, and string manipulation.

## Thread Safety

### Safe

- **`logentry()`** -- Thread-safe. Handler registration is guarded by a `threading.Lock` (`_log_lock`). Default SysLogHandler is lazily initialized on first call to avoid import-time failure on systems without `/dev/log`.
- **`diceroll()`** -- Thread-safe. Uses `random.SystemRandom()` (`_dice_rng`), which is thread-safe and cryptographically strong.
- **`hr()`**, **`heading()`**, **`oxfordcomma()`**, **`pluralize()`** -- Pure functions with no shared state. Safe.
- **`expandrange()`**, **`collapserange()`**, **`rangestr()`** -- Pure functions. Safe.
- **`checksum()`** -- Pure function with no shared state. Safe.
- **`ltree_to_path()`**, **`chop_last_element()`**, **`strip_ansi()`** -- Pure string functions. Safe.
- **`serialize_datetimes()`**, **`tobool()`** -- Pure functions. Safe.
- **`getremoteaddr()`**, **`getcurrentloginid()`** -- Read from process environment, no shared state. Safe.
- **`verifyDirExistsWritable()`**, **`verifyFileExistsReadable()`**, **`verifyFileExistsReadableWritable()`** -- Stateless filesystem checks. Safe.
- **`timedelta_()`** -- Pure function. Safe.

### Not Thread-Safe

- **`init()`** -- Calls `locale.setlocale()` and `time.tzset()`, which mutate global process state. **Must be called at application startup from the main thread only.** Call once, never from multiple threads.

## Public API

```python
hr(acs=True, width=None, end="\n") -> bool
heading(title: str, **kwargs) -> None
pluralize(amount: int, singular="singular", plural="plural", quantity=True, emoji="", determiner="a", **kw) -> str
datestamp(t=None, format="%Y-%m-%d %I:%M%P %Z (%a)") -> str
inputpassword(prompt="password: ", mask="X", **kwargs) -> str
oxfordcomma(seq, conjunction="and") -> Optional[str]
logentry(message: str, *, level=logging.INFO, handler=None, formatter=None, logger_name="bbsengine6") -> None
collapserange(lst: list)
expandrange(txt: str) -> list
rangestr(ranges)
printr(ranges)
filedisplay(res, **kw) -> None
diceroll(sides=6, count=1, mode="single")
verifyDirExistsWritable(dirname: str, **kw) -> bool
verifyFileExistsReadable(filename: str, **kw) -> bool
verifyFileExistsReadableWritable(filename, **kw) -> bool
timedelta_(delta)
getencryptedpassword(args, plaintextpassword: str) -> Optional[str]
init(args=None, **kw)
checksum(data: bytes) -> str
ltree_to_path(ltree: str) -> str
chop_last_element(ltree: str) -> str
tobool(value) -> bool
getremoteaddr() -> Optional[str]
getcurrentloginid(args, **kwargs) -> str
get_safe_path(args, *components, **kwargs) -> str
load_sql(args, resource_name: str, *, package: Optional[str] = None) -> str
serialize_datetimes(data) -> dict
strip_ansi(s: str) -> str
```

## Dependencies

- `logging`, `logging.handlers` -- Syslog logging
- `os`, `re`, `random`, `threading` -- Standard library utilities
- `datetime` -- Date/time handling
- `dateutil` -- Timezone-aware datetime parsing
- `.io`, `.database`, `.input` -- Internal BBS engine modules

## Known Issues / TODOs

1. `datestamp()` calls `time.tzset()` on every invocation. This is redundant and modifies global state. Should be called once in `init()` instead.
2. `logentry()` string level aliases (`"debug"`, `"info"`, etc.) could use an enum for type safety.
3. `timedelta_()` is named with trailing underscore because `timedelta` shadows the `datetime.timedelta` class name.
