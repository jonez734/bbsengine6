# bbsengine6.io.const Specification

## Overview

`const.py` defines the terminal control characters, default widths, and the defaults
for `inputstring()`. Other io modules import these names.

## Control characters

| Constant | Value | Description |
|----------|-------|-------------|
| `ESC` | `"\x1b"` | Escape |
| `CSI` | `ESC + "["` | Control Sequence Introducer (`\x1b[`) |
| `OSC` | `ESC + "]"` | Operating System Command (`\x1b]`) |
| `ST` | `ESC + "\\"` | String Terminator (ECMA-48) |
| `BEL` | `"\007"` | Bell |
| `ETX` | `"\x03"` | End of Text, Ctrl+C. `getch` raises `KeyboardInterrupt` on it. |
| `EOF` | `"\x04"` | End of transmission, Ctrl+D. `getch` raises `EOFError` on it. |

## Widths and output

| Constant | Value | Description |
|----------|-------|-------------|
| `FALLBACK_TERMINAL_WIDTH` | `100` | Width used when the terminal size cannot be read. `terminal.columns()` returns it. |
| `DEFAULT_PALETTE_NAME` | `"c64"` | Palette used when none is chosen. See `io_palette.md`. |
| `ECHO_END` | `"\n"` | Line ending `echo()` writes when `end` is not given. |

## inputstring defaults

| Constant | Value | Description |
|----------|-------|-------------|
| `INPUTSTRING_GETCH_TIMEOUT` | `0.015` | Seconds `inputstring()` waits for a key on each pass of its loop. |
| `INPUTSTRING_DEFAULT_HISTORY_SIZE` | `500` | Entries kept when `history=True`. Matches GNU readline. |
| `INPUTSTRING_DEFAULT_PAGESIZE` | `10` | Characters moved by PAGE UP and PAGE DOWN. |
| `INPUTSTRING_INSERT_MODE_INDICATOR` | `"[INS]"` | Mode marker shown in the bottom bar in insert mode. |
| `INPUTSTRING_OVERWRITE_MODE_INDICATOR` | `"[OVR]"` | Mode marker shown in the bottom bar in overwrite mode. |

The mode indicators are bottom-bar text, not input-line text. See `io_inputstring.md`.

## Not defined

`MAX_TERMINAL_WIDTH` appeared in an earlier version of this spec and in
`io/SPEC.md`. It is not defined in the package. The terminal width comes from
`terminal.columns()`, which reads the terminal and clamps to `BBSENGINE_MAX_WIDTH`
when that variable is set.

## Usage

```python
from bbsengine6.io.const import ESC, CSI, BEL
```
