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

## Usage

```python
from bbsengine6.io import terminal

w = terminal.columns()
h = terminal.lines()
terminal.title("Main menu")
```
