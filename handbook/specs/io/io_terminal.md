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

`probe_da` is the raw probe. `report()` and `has_ansi()` do not call it again once a session has a
cached report (see Terminal report). Each `probe_da` call waits up to the timeout, then
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
report(timeout=None, refresh=False) -> dict
```

Renamed from `terminal_report()`. Callers use `report()`.

Describes the terminal this process runs in. It is blocking only. It runs the DA probe
(DA1, then DA2 if DA1 is silent), then the XTGETTCAP `RGB` query, unless `COLORTERM` already says
truecolor (see below). A silent terminal costs up to three timeouts. Returns `source: "unknown"`
with no tty.

Probed once per session. The result is cached on the current `Session` (`terminal_report`), so a
second `report()` and `has_ansi()` send nothing. `report(refresh=True)` probes again and replaces
the cache. A bed connection has its own session, so each connected client is probed for itself.

Returned keys:

- `term`: the terminal type this process uses, from `resolve()`: the client TERM when it has a
  terminfo entry, else the default (`xterm`). `dumb` (and an empty TERM) is reported as itself.
- `color`: the colour level this terminal can use, as one value: `"truecolor"`, `"256"`, or None.
  - `"truecolor"`: the terminal gave a 24-bit answer (the RGB query, or a trusted `COLORTERM`).
  - `"256"`: the terminfo palette for that TERM has at least 256 colours (8-bit colour), and no
    truecolor answer was given.
  - None: unknown, a palette smaller than 256, or GNU screen (see below). Silence is not evidence
    of no colour.
  The three older fields (`colors`, `true_color`, `color_256`) are gone: they could disagree with
  each other, so they were collapsed into this one.
- `source`: `"query"`, `"colorterm"`, `"screen"`, or `"unknown"`. It says which step gave the
  truecolor answer. `"screen"` means the process runs under GNU screen (see below).
- `ansi`: the DA reply text (DA1, else DA2), or None. Kept for compatibility.
- `da`: one record per command, nested: `da1`, `da2`, and `rgb`. Each record has:
  - `sent`: whether that request was written. DA2 is sent only when DA1 got no reply. RGB is not
    sent when `COLORTERM` says truecolor or 24bit. With the ANSI probe disabled, DA1 and DA2 are
    not sent.
  - `reply`: the reply text, or None when there was no reply, it timed out, or it was not sent.
  - `timed_out`: True when it was sent and no reply came in time.
  - `late`: True when a reply for that request arrived after it timed out and was dropped from
    the keys (see Late replies). The reply text is then in `reply`.

Order for `true_color`:

1. The XTGETTCAP `RGB` query. The reply is `ESC P 1 + r <hex name> = <hex value> ESC \`
   (valid) or `ESC P 0 + r ESC \` (invalid). The name and value are hex-encoded. A value of 8 or
   more means direct color. Verified on VTE (`524742=38`, value 8).
2. `COLORTERM` set to `truecolor` or `24bit`.
3. Unknown (None). Silence is not evidence of no color.

Under GNU screen `color` is always None, whatever terminfo says (`source: "screen"`). screen
passes the outer terminal's `COLORTERM` through but has no 24-bit colour, and it does not answer
the RGB query, so neither step is used and the RGB query is not sent. screen is detected by `STY` being set, or a
`TERM` named `screen`, `screen.*`, or `screen-*` (`in_screen()`).

`COLORTERM` is decided first. When it says truecolor or 24bit the RGB query is not sent, so the
query does not run and its echo cannot reach the keys. Terminals that do not answer the query
echo its text back; that echo is removed from the input (see Echo of our requests).

Other terminals may not answer the query. xterm in the test sessions answered DA1 but not the
RGB query, so on xterm the color answer comes from `COLORTERM` or is unknown.

Late replies: a probe that times out is remembered on the session (`da_timed_out`). A DA or DCS
reply that then arrives is read by the input reader (`discard_da_replies`), removed from the keys,
and recorded in `late_da_replies` as `(probe, reply)`. `report()` shows it as `late: True` on that
record. A reply that arrives after `query_terminal`'s settle window is the case this covers; a
reply inside the window is the probe's answer, not a late one.

Echo of our requests: a terminal that does not answer a query may echo the request back, with or
without its control bytes (`ESC P + q …`, `P+q…`, `ESC [ c`). `common.strip_echoed_request(text,
request)` removes every such echo from unmatched input before the rest is queued as keys. The ESC
that opens the request, and the ESC or bare backslash that closes it, are optional in the match.

```python
parse_xtgettcap_reply(reply) -> dict | None   # {"valid", "name", "value"}
rgb_from_reply(parsed) -> bool | None
xtgettcap_request(name) -> str                # DCS + q <hex of name> ST
query_cap(name, timeout=None)                 # value, True, False, or None
```

`query_cap(name)` asks the running terminal for any capability by name over XTGETTCAP. It returns
the value as a str when the terminal gives one, `True` when the capability is present with no value,
`False` when the terminal says it is absent, and `None` when it does not answer for that name in
time. A reply for a different name is not the answer, so it gives `None`. `xtgettcap_request` raises
`ValueError` for a name that is empty or not printable ASCII.

For a static lookup (no terminal round trip), use terminfo instead:
`terminfo.load(term).get(cap)`. terminfo honours `$TERMINFO` first, then `~/.terminfo`,
`$TERMINFO_DIRS`, and the system directories.

## Usage

```python
from bbsengine6.io import terminal

w = terminal.columns()
h = terminal.lines()
terminal.title("Main menu")
```
