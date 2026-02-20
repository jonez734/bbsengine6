# asimov.io.terminal Specification

## Overview

`terminal.py` provides terminal size detection and utilities.

## Dependencies

- `const.py`: MAX_TERMINAL_WIDTH, FALLBACK_TERMINAL_WIDTH

## Functions

### `size() -> shutil.TerminalSize`

Returns terminal size as `shutil.TerminalSize`.

---

### `columns() -> int`

Returns terminal width in columns.

**Behavior:**
- Uses `shutil.get_terminal_size()`
- Falls back to `FALLBACK_TERMINAL_WIDTH` (100) on error
- Clamps to `MAX_TERMINAL_WIDTH` if set

---

### `lines() -> int`

Returns terminal height in lines.

---

### Aliases

- `width` = `columns`
- `height` = `lines`

## Usage

```python
from asimov.io import terminal

w = terminal.columns()
h = terminal.lines()
```
