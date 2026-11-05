# bbsengine6.io.terminal Specification

## Overview

`terminal.py` reports the terminal's size and sets the window title.

## Dependencies

- `const.py`: `FALLBACK_TERMINAL_WIDTH`, `OSC`, `ST`
- `common.py`: `write_current_output_stream`, used by `title()`

## Functions

### `size() -> os.terminal_size`

Returns `shutil.get_terminal_size()`. Its fields are `columns` and `lines`.

---

### `columns() -> int`

Returns the terminal width in columns, capped.

**Behaviour:**
- Reads the width with `size()`.
- The result is `min(width, cap)`. The cap is `MAX_WIDTH`, which is 120, unless the
  environment variable `BBSENGINE_MAX_WIDTH` holds an integer, which replaces it.
  A value that is not an integer falls back to 120.
- If `size()` raises `OSError`, the result is `FALLBACK_TERMINAL_WIDTH` (100).

**Observed:** `shutil.get_terminal_size()` returns 80 columns when it cannot read the
terminal and no `COLUMNS` variable is set, so `columns()` returns 80 in that case,
not 100. The 100 fallback applies only to an `OSError` from `size()`.

Examples, with `COLUMNS` set to force the width:

| Terminal width | `BBSENGINE_MAX_WIDTH` | Result |
|---|---|---|
| 150 | unset | 120 |
| 150 | `100` | 100 |
| 60 | unset or `100` | 60 |

---

### `lines() -> int`

Returns the terminal height in lines (`size().lines`). Not capped.

---

### `title(t: str) -> None`

Sets the window title with `OSC 0 ; t ST`, written to the current output stream.

Use this to set the title. `echo("{settitle:...}")` is not a command: it writes the
text as-is (see `io_echo.md`).

---

### Aliases

- `width` is `columns`
- `height` is `lines`

## ANSI detection

Config block (bed.json / zoid6.json, under `terminal`):

```json
"terminal": { "ansi_probe": { "enabled": true, "timeout_seconds": 0.5 } }
```

`configure_ansi_probe(cfg)` applies it at startup. `cfg` is the `terminal` object, or `None`
for the defaults. Bad values raise `ValueError`.

```python
probe_da(timeout=None, block=True) -> str | None
has_ansi(block=True) -> bool
ansi_reply() -> str | None
```

- `block=True` (default) waits up to the timeout for a reply, as above.
- `block=False` sends DA1 and returns at once (`probe_da` returns `None`; `has_ansi` returns
  `False`, meaning "not known yet", not "no ANSI"). The reply is taken by the input reader,
  which keeps it in the session. `ansi_reply()` returns the oldest kept reply and removes it.
  A reply the reader has not yet taken is not visible to `ansi_reply()`.

- `probe_da` sends DA1 (`ESC[c`). If there is no reply it sends DA2 (`ESC[>c`). It returns the
  raw reply, or `None`. It returns `None` without writing anything when `enabled` is false. The
  reply is logged at debug level, for debugging.
- `has_ansi` returns `True` when the reply is an approved DA1 (`ESC[?...c`) or DA2 (`ESC[>...c`)
  response. It returns `False` for `None`, empty text, or anything else.

Calling `probe_da` again sends a fresh query each time. Each call waits up to the timeout, then
`query_terminal` keeps reading for 0.25 s (`QUERY_SETTLE_SECONDS`). A reply inside that window
is matched and consumed. A reply that arrives after it is not consumed: the tty is restored, the
kernel echoes the bytes, and the next input read may see them. That case is known and accepted as
rare. Removing it needs no-echo mode and discarding DA-shaped sequences in the key reader.

```python
decode_da(reply) -> dict | None
```

Splits a `probe_da()` reply. Returns `None` for anything that is not an approved DA1 or DA2 reply
(the same rule `has_ansi` uses). For DA1 the dict has `kind` (`"DA1"`), `params`, `class` (the
conformance class, for example 62 for VT220), and `features` (the rest). For DA2 it has `kind`
(`"DA2"`), `params`, `terminal_type`, and `firmware` (either may be None). Non-numeric parameters
make the reply invalid.

Example DA1 replies: `ESC[?6c` (VT102), `ESC[?1;2c` (VT100 with AVO),
`ESC[?62;1;2;6;8;9;15;22c` (VT220). The rule accepts any digits and `;` between the marker and `c`.

## Terminal report (color and capabilities)

```python
terminal_report(timeout=None) -> dict
```

Describes the terminal this process runs in. It is blocking only. It runs the DA probe
(DA1, then DA2 if DA1 is silent), then the XTGETTCAP `RGB` query. A silent terminal costs up to
three timeouts. Returns `source: "unknown"` with no tty.

Returned keys:

- `term`: the TERM used.
- `colors`: terminfo `colors` for that TERM, or None.
- `true_color`: True, False, or None (unknown).
- `color_256`: True if `colors >= 256` or `true_color`; False if `colors` is known and smaller;
  None if neither is known.
- `source`: `"query"`, `"colorterm"`, or `"unknown"`. It says which step gave `true_color`.
- `ansi`: the DA reply text, or None.

Order for `true_color`:

1. The XTGETTCAP `RGB` query. The reply is `ESC P 1 + r <hex name> = <hex value> ESC \`
   (valid) or `ESC P 0 + r ESC \` (invalid). The name and value are hex-encoded. A value of 8 or
   more means direct color. Verified on VTE (`524742=38`, value 8).
2. `COLORTERM` set to `truecolor` or `24bit`.
3. Unknown (None). Silence is not evidence of no color.

Other terminals may not answer the query. xterm in the test sessions answered DA1 but not the
RGB query, so on xterm the color answer comes from `COLORTERM` or is unknown.

Late replies: a DCS XTGETTCAP reply that arrives after its query is read as one sequence through
its ST, and the input queue drops it (recording it in the session). It is never typed as keys.

```python
parse_xtgettcap_reply(reply) -> dict | None   # {"valid", "name", "value"}
rgb_from_reply(parsed) -> bool | None
```

## Usage

```python
from bbsengine6.io import terminal

w = terminal.columns()
h = terminal.lines()
terminal.title("Main menu")
```
