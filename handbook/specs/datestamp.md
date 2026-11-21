# datestamp Specification

> Status: canonical. Updated 2026-11-21 (Python examples pinned; bed debug time form added).

## Summary

`datestamp` is the canonical date/time formatter for bbsengine6.
It is exposed in three surfaces:

- **Python** — `bbsengine6.util.datestamp(t, format)` for TUI / CLI / scripts.
- **PHP** — `\bbsengine6\util\datestamp($t, $format)` for any PHP code path
  (CLI scripts, web request handlers, library code).
- **Smarty** — `{$timestamp|datestamp}` (or `{$timestamp|datestamp:$format}`)
  for web templates. The Smarty modifier
  (`bbsengine6/smarty/modifier.datestamp.php` and
  `zoid6/smarty/modifier.datestamp.php`) is a thin wrapper around
  `\bbsengine6\util\datestamp()`. The function body is defined
  in `bbsengine6/php/smarty_modifier_datestamp.php`; both
  modifier files are 2-line stubs that require the canonical
  body via a `__DIR__`-relative path.

All three surfaces accept the same strftime vocabulary and produce
**byte-exact** output for any common-subset token on a server with
`LC_TIME=C`. The PHP modifier
extends the vocabulary with one opt-in token, `%O`, which
renders the per-user timezone offset (e.g. `-04:00`, `+05:30`)
when the session has set one.

## Public API

### Python — `bbsengine6.util.datestamp`

```python
from bbsengine6.util import datestamp

datestamp(t=None, format: str = "%Y-%m-%d %I:%M%P %Z (%a)") -> str
```

| Argument | Type | Description |
|----------|------|-------------|
| `t` | `None \| int \| float \| str \| datetime` | The value to format. `None` uses the current time. `int`/`float` are interpreted as Unix epoch seconds, in the server's local zone. `str` is parsed via `bbsengine6.io.input.getdate()`. `datetime` is used as-is: an aware datetime keeps its own zone, a naive one is printed without a zone name. |
| `format` | `str` | strftime format string. Default: `"%Y-%m-%d %I:%M%P %Z (%a)"`. Note `%P` is lowercase (`am`/`pm`). |

`datestamp` calls `time.tzset()` on every call, so the server's `TZ` is read fresh each time.

#### Examples

The examples below were run with `TZ` set as shown. The instant used throughout is
2026-11-21 13:49:07 UTC (the same instant the bed tests pin).

```python
>>> # TZ=America/New_York  (EST, UTC-5 in November)
>>> datestamp(0)                     # Unix epoch, in local time
'1969-12-31 07:00pm EST (Wed)'
>>> datestamp(utc_instant, format="%Y-%m-%d %H:%M:%S %Z")       # utc_instant: an aware UTC datetime
'2026-11-21 13:49:07 UTC'
>>> datestamp(utc_instant.astimezone(), format="%Y-%m-%d %H:%M:%S %Z")   # converted to local
'2026-11-21 08:49:07 EST'
>>> datestamp("2026-11-21 08:49", format="%Y-%m-%d %H:%M")      # string via getdate()
'2026-11-21 08:49'
```

The same UTC instant in other local zones (`datestamp(utc_instant.astimezone(), format="%Y-%m-%d %H:%M:%S %Z")`):

| `TZ` | Output | Offset |
|------|--------|--------|
| `America/Los_Angeles` | `2026-11-21 05:49:07 PST` | UTC-8 |
| `America/New_York` | `2026-11-21 08:49:07 EST` | UTC-5 |
| `Europe/London` | `2026-11-21 13:49:07 GMT` | UTC+0 |
| `Asia/Kolkata` | `2026-11-21 19:19:07 IST` | UTC+5:30 (half-hour) |
| `Pacific/Chatham` | `2026-11-22 03:34:07 +1345` | UTC+13:45 (numeric abbreviation; no letters) |
| `UTC` | `2026-11-21 13:49:07 UTC` | UTC |

Zone coverage is pinned by `bed/src/bed/tests/test_authenticate_time_other_zones.py`. Summer time (DST) on a transition
day is not covered by any test.

#### Summer and fall transitions: London and Dallas

London (`Europe/London`) and Dallas (`America/Chicago`, the zone Dallas keeps) change clocks on different dates, so their
offset is not constant through the year. The instants below come from the tz database (`zoneinfo`), and each is shown one
second either side of the switch. Built from aware datetimes, so they do not depend on the server's `TZ`.

| Switch | Instant | Local clock (before → after) |
|--------|---------|------------------------------|
| London spring forward | 2026-03-29 01:00 UTC | `2026-03-29 00:59:59 GMT` → `2026-03-29 02:00:00 BST` |
| Dallas spring forward | 2026-03-08 08:00 UTC | `2026-03-08 01:59:59 CST` → `2026-03-08 03:00:00 CDT` |
| London fall back | 2026-10-25 01:00 UTC | `2026-10-25 01:59:59 BST` → `2026-10-25 01:00:00 GMT` |
| Dallas fall back | 2026-11-01 07:00 UTC | `2026-11-01 01:59:59 CDT` → `2026-11-01 01:00:00 CST` |

The clocks are not in step:

- Dallas springs forward **three weeks before** London (March 8 against March 29).
- Dallas falls back **one week after** London (November 1 against October 25).

So the London–Dallas difference is 6 hours in winter, 5 hours from March 8 to March 29, 6 hours from March 29 to October
25 (both on summer time), 5 hours from October 25 to November 1 (London on GMT, Dallas still on CDT), and 6 hours after
November 1. The test `test_util_datestamp_dst_transitions.py` checks each switch and these offsets.

```python
>>> from zoneinfo import ZoneInfo
>>> from datetime import datetime, timezone
>>> instant = datetime(2026, 3, 8, 8, 0, 0, tzinfo=timezone.utc)
>>> datestamp(instant.astimezone(ZoneInfo("America/Chicago")), format="%Y-%m-%d %H:%M:%S %Z")
'2026-03-08 03:00:00 CDT'
>>> datestamp(instant.astimezone(ZoneInfo("Europe/London")), format="%Y-%m-%d %H:%M:%S %Z")
'2026-03-08 08:00:00 GMT'
```

The second line is London's clock at the instant Dallas springs forward: London is still on GMT, so the two zones read
5 hours apart for three weeks.

#### Switches at local midnight (other years)

Some zones switch clocks at midnight. Two cases matter for formatting, and both are tested in Python and PHP
(`test_util_datestamp_midnight_transitions.py` and `php/test_util_datestamp_midnight_transitions.php`, the same instants
and expected output):

- **Skipped midnight.** The clock jumps from `23:59:59` straight to `01:00:00`, so `00:00` never occurs that day.
- **Repeated midnight.** The clock goes back from `00:59:59` to `00:00:00`, so the hour from `00:00` to `00:59` occurs
  twice (the switch is at `00:00` local, so the second before it is `23:59:59` the previous day). The two occurrences are told apart only by the zone abbreviation and the fold: the second `00:30` on
  2027-11-07 is `00:30 CST`. A formatter that ignores the fold gives `00:30 CDT` for it, which is the wrong zone.

| Zone | Switch | Local clock, before → after |
|------|--------|------------------------------|
| `America/Havana` | 2026-03-08 05:00 UTC, skipped midnight | `2026-03-07 23:59:59 CST` → `2026-03-08 01:00:00 CDT` |
| `America/Santiago` | 2026-09-06 04:00 UTC, skipped midnight | `2026-09-05 23:59:59 -04` → `2026-09-06 01:00:00 -03` |
| `America/Havana` | 2027-11-07 05:00 UTC, repeated midnight | `2027-11-07 00:59:59 CDT` → `2027-11-07 00:00:00 CST` |
| `Asia/Gaza` | 2015-10-22 22:00 UTC, repeated midnight | `2015-10-23 00:59:59 EEST` → `2015-10-23 00:00:00 EET` |

```python
>>> instant = datetime(2027, 11, 7, 5, 0, 0, tzinfo=timezone.utc)
>>> datestamp(instant.astimezone(ZoneInfo("America/Havana")) - timedelta(seconds=1), format="%Y-%m-%d %H:%M:%S %Z")
'2027-11-06 23:59:59 CDT'
>>> datestamp(instant.astimezone(ZoneInfo("America/Havana")), format="%Y-%m-%d %H:%M:%S %Z")
'2027-11-07 00:00:00 CST'
```

Python and PHP agree on every case above. PHP's zone database matches zoneinfo for these instants, and the PHP walker
formats each epoch in the server zone (`date_default_timezone_set`). No code change was needed to match.

#### The local time with UTC in parentheses

bed's sign-in debug line (`bed.tools.authenticate.time_line`) shows the local time with its zone name and UTC in
parentheses. It is built from two `datestamp` calls with the 24-hour format `%Y-%m-%d %H:%M:%S`:

```python
local = datetime.now().astimezone()
utc = local.astimezone(timezone.utc)
f"{datestamp(local, format=FMT)} {local.tzname()} ({datestamp(utc, format=FMT)} UTC)"
# FMT = "%Y-%m-%d %H:%M:%S"
```

For `TZ=America/New_York` at the instant above:

```
2026-11-21 08:49:07 EST (2026-11-21 13:49:07 UTC)
```

#### Timestamps from the daemon

A value that comes from the daemon (for example the `timestamp` in a `pong`) is an ISO-8601 string with `+00:00`.
`datestamp` does not reformat it, since it is a value this process did not produce. Callers that want it in local time
parse it to a `datetime` first.

### Smarty — `|datestamp` modifier

```smarty
{$timestamp|datestamp}
{$timestamp|datestamp:"%Y-%m-%d"}
```

| Argument | Description |
|----------|-------------|
| `$timestamp` | Unix epoch (integer or numeric string). Non-numeric input renders as empty string. |
| `$format` (optional) | strftime format string. If omitted, the vhost's `DATEFORMAT` constant is used. Empty string and `null` both fall back to `DATEFORMAT`. |

The modifier reads `$_SESSION['localtimezoneoffset']` (integer
minutes, set by `ping.php` from the client ping payload) for the
`%O` token. When unset, `%O` renders as empty string.

```smarty
{* uses DATEFORMAT *}
{"config\n"}
<time datetime="{$timestamp|datestamp:"%Y-%m-%dT%H:%M:%S%:z"}">...</time>
```

### PHP — `\bbsengine6\util\datestamp()`

The canonical PHP date/time formatter, exposed alongside the
Smarty modifier. Mirrors the Python `bbsengine6.util.datestamp`
signature so the two surfaces produce identical output for the
same input.

```php
use function bbsengine6\util\datestamp;

datestamp(int|float|string|\DateTimeInterface|null $t = null, ?string $format = null): string
```

| Argument | Type | Description |
|----------|------|-------------|
| `$t` | `null \| int \| float \| string \| DateTimeInterface` | The value to format. `null` uses the current time. `int`/`float` are Unix epoch seconds. Numeric strings are interpreted as Unix epochs (the `@`-prefix convention used by PHP's `strtotime()` is applied internally). Other strings are parsed via `strtotime()`. `DateTimeInterface` is used as-is. Unparseable strings return `""`. |
| `$format` | `string \| null` | strftime format string. `null`/empty falls back to `\config\DATEFORMAT` → bare `DATEFORMAT` → `"%Y-%m-%d %I:%M%P %Z (%a)"` (the same default as Python's `datestamp()`). |

```php
>>> datestamp()  // Current time
'2026-10-13 14:30'
>>> datestamp(0)  // Unix epoch
'1970-01-01 00:00'
>>> datestamp(time(), '%Y-%m-%d %I:%M%P %Z (%a)')
'2026-10-13 02:30pm EDT (Tue)'
```

The function reads `$_SESSION['localtimezoneoffset']` (integer
minutes, set by `ping.php` from the client ping payload) for the
`%O` token, identical to the Smarty modifier.

Both Smarty modifiers (`bbsengine6/smarty/modifier.datestamp.php`
and `zoid6/smarty/modifier.datestamp.php`) are thin wrappers that
call this function. There is one implementation of the walker;
there are three callers (the helper itself, plus the two Smarty
modifiers).

## Supported format tokens

The PHP modifier and Python's `bbsengine6.util.datestamp` accept
the same strftime vocabulary. Output is identical for any token
both languages render; PHP-specific extensions are marked.

### Common subset (Python + PHP, output identical)

| Token | Output | Example |
|-------|--------|---------|
| `%Y` | 4-digit year | `2026` |
| `%y` | 2-digit year | `26` |
| `%m` | 2-digit month | `10` |
| `%b` | short month name | `Oct` |
| `%B` | full month name | `October` |
| `%d` | 2-digit day of month | `13` |
| `%j` | day of year, 1-indexed | `286` |
| `%H` | 24-hour | `14` |
| `%I` | 12-hour, zero-padded | `02` |
| `%l` | 12-hour, no padding | see above |
| `%M` | minute | `30` |
| `%S` | second | `00` |
| `%p` | AM/PM uppercase | `PM` |
| `%P` | am/pm lowercase | `pm` |
| `%Z` | server TZ abbreviation | `UTC`, `EDT`, `PDT` |
| `%z` | UTC offset `+HHMM` | `+0000` |
| `%:z` | UTC offset `+HH:MM` | `+00:00` |
| `%a` | short day name | `Tue` |
| `%A` | full day name | `Tuesday` |
| `%%` | literal `%` | `%` |

### Common extensions

| Token | Output | Notes |
|-------|--------|-------|
| `%O` | per-user TZ offset `±HH:MM` (or empty) | Renders empty string when offset is unset or zero. **PHP** (`|datestamp`): reads `$_SESSION['localtimezoneoffset']` (integer minutes) per request. **Python** (`bbsengine6.util.datestamp`): reads the module-level `_user_tz_offset_minutes` set via `bbsengine6.util.set_user_tz_offset(minutes)`. Same output format on both surfaces. |

### Type-semantic differences (not byte-exact by design)

The byte-exact parity claim is for `(int|float $t, string $format)`
inputs on a server with `LC_TIME=C`. The two surfaces diverge
intentionally for non-int input types because each language's
idiomatic type system differs:

- **`$t` is a `string`**: PHP calls `strtotime()` (or treats a
  numeric string as a Unix epoch). Python calls
  `bbsengine6.io.input.getdate()`, a BBS-specific parser. The
  same string input may produce different timestamps. Consumers
  who need cross-language string parsing should pre-parse to an
  epoch int and pass that instead.
- **`$t` is a `datetime`/`DateTimeInterface`**: PHP uses the
  `DateTimeInterface` instance's `getTimestamp()`. Python uses
  the `datetime` instance's `utcoffset()` for `%z`/`%:z` and its
  native `strftime()`. The two surfaces agree on the timestamp
  interpretation but differ in the date object's type API.
- **Default format string**: both surfaces default to
  `"%Y-%m-%d %I:%M%P %Z (%a)"` when no format is given and no
  `DATEFORMAT` constant is defined. PHP reads `DATEFORMAT` (the vhost
  constant) first, so a vhost that sets it changes PHP's default.
  Callers that need a fixed layout on both surfaces should pass the
  format string explicitly.
- **Failure modes**: PHP returns `""` on unparseable input or
  wrong type. Python raises `AssertionError` on wrong type and
  returns the original string from `getdate()` on unparseable
  string input.

### Resolved divergences (pre-2026-10-15)

- **`%l` (12-hour, unpadded/space-padded)**: Python's strftime
  `time.strftime("%l", t)` returns space-padded (`" 2"` for
  hours 1-9). PHP's `date('g', $ts)` returns unpadded (`"2"`).
  Resolved: the PHP walker now pads to width 2 with a leading
  space, so `%l` produces byte-exact output across both surfaces.
- **Day/month name locale**: PHP's `date('D')` and Python's
  strftime both read the C runtime's `LC_TIME`. Without a locale
  pin, a non-English server locale would produce locale-specific
  names. Resolved: the PHP walker calls `setlocale(LC_TIME, 'C')`
  at entry, matching Python's default `C` locale. The Python
  walker's `t.strftime()` already honors `LC_TIME`; with both
  pinned to `C`, day/month names are byte-exact.

### Out of scope (not implemented)

The following strftime tokens are **not** implemented by the PHP
modifier and would require explicit support:

- `%C` — century
- `%e` — day of month, space-padded
- `%h` — short month name (alias for `%b`)
- `%n` — percent number
- `%t` — percent tab
- `%U`, `%W` — week number (Sunday/Monday start; both differ from PHP `date('W')` which is ISO week)
- `%V`, `%G`, `%g` — ISO 8601 week-based year
- `%u`, `%w` — day of week (Monday/Sunday start)

Consumers should not depend on these. To request a token be added,
open an issue against `bbsengine6`.

## Configuration

### `DATEFORMAT` constant

The Smarty modifier reads the bare `DATEFORMAT` constant when
called without an explicit format argument. The default is set in
the vhost's `config.php`:

```php
define("DATEFORMAT", "%Y-%m-%d %I:%M%P %Z (%a)");
```

The zoid6 vhost overrides this in `zoid6/php/zoid6.php:22` with
the same value:

```php
define("DATEFORMAT", "%Y-%b-%d %l:%M%p %Z (%a)"); // @see https://php.net/strftime
```

When a vhost needs a different default, it can override either via
its own `config.php` or by passing the format string at the call site:

```smarty
{$timestamp|datestamp:"%Y-%m-%d"}
```

### Smarty plugin search order

The Smarty plugin search order is determined by `\bbsengine6\template\plugin\normalize()`
which merges three priority levels: `PRIORITY_APP` (the vhost's
`SMARTYPLUGINSDIR`), `PRIORITY_APP_INTEGRATION` (zoid6's
`\plugin_extra()`), and `PRIORITY_ENGINE` (bbsengine6's canonical
contribution, `bbsengine6/smarty/`).

Both `bbsengine6/smarty/modifier.datestamp.php` and
`zoid6/smarty/modifier.datestamp.php` are present in the search
path. The first match wins. zoid6-using vhosts (e.g. achilles)
load zoid6's modifier first via `PRIORITY_APP_INTEGRATION`. As of
2026-10-13, both modifiers implement the same vocabulary — the
search-order distinction is invisible to consumers.

### Per-user timezone offset (`%O`)

The `%O` opt-in token renders the per-user timezone offset as
`±HH:MM` (or empty string when unset). Both surfaces support it
identically.

**PHP** (`|datestamp`): reads `$_SESSION['localtimezoneoffset']`
(integer minutes) per request. The web framework sets this before
rendering — for example, bbsengine6/achilles populates from the
client ping payload in `ping.php`; other vhosts may use a
different mechanism.

**Python** (`bbsengine6.util.datestamp`): reads the module-level
state set via `bbsengine6.util.set_user_tz_offset(minutes)`.
Returns the integer offset via `bbsengine6.util.get_user_tz_offset()`.
The consumer (CLI tool, daemon, web framework integration) sets
this once per request/thread before calling `datestamp()`.

Behavior:

- Offset unset → `%O` renders as empty string.
- Offset `0` → renders as empty string.
- Offset positive (e.g. `+330` for IST) → renders as `+05:30`.
- Offset negative (e.g. `-240` for EDT) → renders as `-04:00`.
- Half-hour offsets (e.g. `+345` for Nepal) → renders as `+05:45`.

## Behavior parity

Given the same timestamp, format string, and server with
`LC_TIME=C`, Python `bbsengine6.util.datestamp(t, format)` and
`\bbsengine6\util\datestamp($t, $format)` (and the Smarty
modifier that wraps it) produce **byte-exact** output for every
common-subset token.

Example (server TZ = UTC, LC_TIME = C, ts = 1760365800 = 2025-10-13
14:30 UTC):

| Format string | Python output | PHP output |
|---------------|---------------|------------|
| `"%Y-%m-%d"` | `2025-10-13` | `2025-10-13` |
| `"%H:%M:%S"` | `14:30:00` | `14:30:00` |
| `"%Y-%m-%d %H:%M:%S %Z"` | `2025-10-13 14:30:00 UTC` | `2025-10-13 14:30:00 UTC` |
| `"%A, %B %d, %Y"` | `Monday, October 13, 2025` | `Monday, October 13, 2025` |
| `"day %j of %Y"` | `day 286 of 2025` | `day 286 of 2025` |
| `"%l"` (12-hour, padded) | ` 2` | ` 2` |
| `"%:z"` (offset with colon) | `+00:00` | `+00:00` |

The byte-exact contract is enforced by
`bbsengine6/test_parity_php_python.json`, a shared JSON fixture
read by both `bbsengine6/php/test_parity_php_python.php` and
`bbsengine6/py/tests/test_parity_php_python.py`. Either test
failing indicates the two surfaces have drifted.

## Test coverage

Regression coverage lives at:

- `bbsengine6/php/test_datestamp_modifier.php` — 40 tests covering
  every common-subset token, the default-format fallback, the
  `%O` opt-in (no session, zero, positive, negative, half-hour),
  edge cases (non-numeric, null, zero epoch, empty format), and
  the token-aware walker behavior (bare letters preserved, multi-char
  tokens like `%:z` matched before `%z`, unknown tokens passed
  through verbatim).
- `bbsengine6/php/test_util_datestamp.php` — 46 tests covering
  `\bbsengine6\util\datestamp()` directly (type coercion, format
  resolution, full token vocabulary, `%O` opt-in, walker edge
  cases).
- `zoid6/php/test_datestamp_modifier.php` — parallel coverage for
  the zoid6 modifier (38 tests).
- `bbsengine6/test_parity_php_python.json` + the two cross-language
  runners — 26 byte-exact parity cases (`test_parity_php_python.php`
  and `test_parity_php_python.py` both consume the same JSON).
- `py/tests/test_util_datestamp.py` — 38 tests covering
  `bbsengine6.util.datestamp` (per-token, %O, default format, edge
  cases).
- `py/tests/test_parity_php_python.py` — 27 Python-side cases
  pinned against the shared fixture.
- `py/tests/test_util_datestamp_dst_transitions.py` — 12 tests: London and Dallas
  (`America/Chicago`) at the 2026 spring and fall switches, one second either side; the
  London–Dallas offset through the year; a `TZ`/`tzset()` case.
- `py/tests/test_util_datestamp_midnight_transitions.py` — 5 tests: skipped midnight
  (Havana 2026, Santiago 2026) and repeated midnight (Havana 2027, Gaza 2015), and a
  fold-ignoring mutant check.
- `php/test_util_datestamp_midnight_transitions.php` — 11 checks: the same midnight
  instants and expected output as the Python file, plus a check that the real formatter
  differs from a fold-ignoring one.

Run with:

```bash
# PHP — modifier + util + parity
php bbsengine6/php/test_datestamp_modifier.php
php bbsengine6/php/test_util_datestamp.php
php bbsengine6/php/test_parity_php_python.php
php zoid6/php/test_datestamp_modifier.php
php php/test_util_datestamp_midnight_transitions.php

# Python — util + parity
cd bbsengine6/py
python3 -m pytest tests/test_util_datestamp.py tests/test_parity_php_python.py
```

## Implementation notes

### Token-aware walker (PHP modifier)

The PHP modifier walks the format string character-by-character
rather than running `str_replace` on the whole string and passing
the result to `date()`. This is necessary because PHP `date()`
interprets any ASCII letter in the format as a token, while
strftime only treats `%X`-prefixed sequences as tokens — bare
letters must be passed through literally.

The walker tries the longest known token prefix first (so
multi-character tokens like `%:z` match before single-letter `%z`),
then a single-letter `%X`, then a literal `%`.

### Translation table

| strftime token | PHP date() token | Notes |
|----------------|------------------|-------|
| `%Y`, `%y`, `%m`, `%d`, `%H`, `%I`, `%M`, `%S`, `%p`, `%P`, `%Z`, `%z`, `%:z`, `%a`, `%A`, `%b`, `%B`, `%l`, `%%` | `Y`, `y`, `m`, `d`, `H`, `h`, `i`, `s`, `A`, `a`, `T`, `O`, `P`, `D`, `l`, `M`, `F`, `g`, `%` | Direct translation. |

| strftime token | PHP equivalent | Notes |
|----------------|----------------|-------|
| `%j` | `(int)date('z', $ts) + 1` | Day-of-year, 1-indexed. PHP `date('z')` is 0-indexed. |

| strftime token | PHP equivalent | Notes |
|----------------|----------------|-------|
| `%O` | `$_SESSION['localtimezoneoffset']` (per-user, default 0) | Pre-computed; inserted inline. Not in PHP date() vocabulary. |

### Backward compatibility

- **No session offset**: `%O` renders empty string, behavior matches
  pre-2026-10-13 modifiers (which had no `%O`).
- **No format arg**: modifier reads `DATEFORMAT`, behavior matches
  pre-2026-10-13.
- **Old tokens still work**: `%Y`, `%m`, `%d`, etc. render the same
  output as before.
- **Previously-broken tokens now work**: `%a`, `%b`, `%B`, `%l`,
  `%P`, `%z`, `%:z`, `%j` previously rendered as literal tokens
  (e.g. `date("b", $ts)` returns nothing, `date("a", $ts)` returns
  lowercase am/pm). Now they render the correct strftime output.

## Historical

- **2026-11-21** — Python examples rewritten from runs, not from memory. The earlier `datestamp(0)` example
  (`1970-01-01 12:00AM EST (Thu)`) was wrong: the default `%P` is lowercase and the epoch is printed in the server's zone.
  Added the UTC-instant table across five local zones and the bed debug time form.
- **2026-10-15** — Extracted the Smarty modifier body to a single
  canonical source. The `|datestamp` modifier function is now
  defined in `bbsengine6/php/smarty_modifier_datestamp.php` and
  loaded by both `bbsengine6/smarty/modifier.datestamp.php` and
  `zoid6/smarty/modifier.datestamp.php` via `__DIR__`-relative
  `require_once`. Both modifier files are 2-line stubs (bootstrap
  + body require); the function body is no longer duplicated
  across the two plugins. Tests
  (`bbsengine6/php/test_datestamp_modifier.php` and
  `zoid6/php/test_datestamp_modifier.php`) now `require_once` the
  canonical body directly instead of `eval`-ing the modifier
  file with a `require_once("config.php")` stub.
- **2026-10-15** — Byte-exact parity with Python's strftime. The
  PHP walker now pins `LC_TIME=C` at entry so day/month names
  match Python's C-locale output byte-for-byte. The `%l` token
  is space-padded (`str_pad('g', 2, ' ', STR_PAD_LEFT)`) so it
  matches Python's strftime `%l` (which returns `" 2"` for
  hours 1-9). The Python walker explicitly handles `%:z` (which
  Python's strftime does not support natively) so the two
  surfaces agree on `+HH:MM` offset output. The bbsengine6 and
  zoid6 Smarty modifier files are now byte-identical (the
  VHOSTDOCROOT bootstrap moved to
  `\bbsengine6\util\smarty_plugin_bootstrap()` so both
  modifiers can share it). A shared JSON fixture
  (`test_parity_php_python.json`) plus two cross-language test
  runners (`test_parity_php_python.php` and
  `test_parity_php_python.py`) enforce the byte-exact contract
  on every CI run.
- **2026-10-13** — New spec document. PHP modifier walker rewritten
  to support the full Python strftime vocabulary; `%O` opt-in
  added for per-user timezone display via
  `$_SESSION['localtimezoneoffset']`. Eight previously-unmapped
  tokens (`%a`, `%b`, `%B`, `%l`, `%P`, `%z`, `%:z`, `%j`) now
  produce correct output. zoid6's modifier (previously a 3-line
  `date()` shim) extended to match.
- **2026-09-29** — VHOSTCONFIG fallback removed from bbsengine6
  modifier's defensive block (see `ROBUSTNESS_REVIEW.md` Phase 8).
- **2006-08-24** — `modifier.datestamp.php` created by jam. Used
  the strftime→date translation-table approach with 11 mapped
  tokens; remaining 9 strftime tokens rendered as literal characters.