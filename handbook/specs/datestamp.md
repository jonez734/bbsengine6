# datestamp Specification

> Status: canonical. Updated 2026-10-15.

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
| `t` | `None \| int \| float \| str \| datetime` | The value to format. `None` uses the current time. `int`/`float` are interpreted as Unix epoch seconds. `str` is parsed via `bbsengine6.io.input.getdate()`. `datetime` is used as-is. |
| `format` | `str` | strftime format string. Default: `"%Y-%m-%d %I:%M%P %Z (%a)"`. |

```python
>>> datestamp()  # Current time
'2026-05-19 02:30PM EDT (Mon)'
>>> datestamp(0)  # Unix epoch
'1970-01-01 12:00AM EST (Thu)'
```

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
| `$format` | `string \| null` | strftime format string. `null`/empty falls back to `\config\DATEFORMAT` → bare `DATEFORMAT` → `"%Y-%m-%d %H:%M"`. |

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
- **Default format string**: PHP reads `DATEFORMAT` (the vhost
  constant) with a fallback chain. Python's `datestamp(t, format)`
  has a hardcoded default of `"%Y-%m-%d %I:%M%P %Z (%a)"`. To
  pin a specific default across both surfaces, callers should
  pass the format string explicitly.
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

Run with:

```bash
# PHP — modifier + util + parity
php bbsengine6/php/test_datestamp_modifier.php
php bbsengine6/php/test_util_datestamp.php
php bbsengine6/php/test_parity_php_python.php
php zoid6/php/test_datestamp_modifier.php

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