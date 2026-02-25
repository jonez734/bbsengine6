# asimov.io.getch Specification

## Overview

`getch.py` provides raw character input from the terminal with support for control keys and ANSI escape sequences. It handles key mapping and terminal mode management.

## Dependencies

- `common.py`: Input stream management
- `keymap.py`: ANSI escape sequence to key name mapping
- `util.py`: Loggingconst.py`: Constants utilities
- ` (ESC, ETX, EOF)

## Public API

### Main Function

```python
getch_str(timeout: float | None = None, debug: bool = False, **kwargs) -> str | None
```

Reads a single keypress and returns a key name or character.

**Parameters:**
- `timeout`: Seconds to wait for input. If `None` (default), blocks indefinitely. If 0, returns immediately.
- `debug`: If True, log unknown escape sequences and return None (default: False)
- `**kwargs`: Additional arguments (reserved)

**Returns:**
- Key name string (e.g., `"KEY_UP"`, `"KEY_LEFT"`, `"KEY_ENTER"`)
- Single character for regular input
- Raw escape sequence for unknown sequences (when `debug=False`)
- `None` if timeout occurred or unknown sequence (when `debug=True`)

**Raises:**
- `KeyboardInterrupt` on Ctrl+C
- `EOFError` on Ctrl+D

---

## Key Mappings

### Control Characters

| Character | Key Name |
|-----------|----------|
| `\x01` (Ctrl+A) | `KEY_CTRL_A` |
| `\x05` (Ctrl+E) | `KEY_CTRL_E` |
| `\x07` (Ctrl+G, BEL) | `KEY_BELL` |
| `\x08` (Backspace) | `KEY_BACKSPACE` |
| `\x0d` (Carriage Return) | `KEY_ENTER` |
| `\x09` (Tab) | `KEY_TAB` |
| `\x15` (Ctrl+U) | `KEY_CUTTOBOL` |
| `\x7f` (DEL) | `KEY_BACKSPACE` |

### Escape Sequences (from keymap.py)

| Sequence | Key Name |
|----------|----------|
| `\x1b[A` | `KEY_UP` |
| `\x1b[B` | `KEY_DOWN` |
| `\x1b[C` | `KEY_RIGHT` |
| `\x1b[D` | `KEY_LEFT` |
| `\x1b[H` | `KEY_HOME` |
| `\x1b[F` | `KEY_END` |
| `\x1b[2~` | `KEY_INSERT` |
| `\x1b[3~` | `KEY_DELETE` |
| `\x1b[5~` | `KEY_PAGEUP` |
| `\x1b[6~` | `KEY_PAGEDOWN` |
| `\x1bOP` | `KEY_F1` |
| `\x1bOQ` | `KEY_F2` |
| `\x1bOR` | `KEY_F3` |
| `\x1bOS` | `KEY_F4` |
| `\x1b[15~` | `KEY_F5` |
| `\x1b[17~` | `KEY_F6` |
| `\x1b[18~` | `KEY_F7` |
| `\x1b[19~` | `KEY_F8` |
| `\x1b[20~` | `KEY_F9` |
| `\x1b[21~` | `KEY_F10` |
| `\x1b[23~` | `KEY_F11` |
| `\x1b[24~` | `KEY_F12` |

### Plain Keys

- Single character bytes (printable ASCII) are returned as-is

---

## Internal Functions

### `_proc_char(char: str) -> str`

Processes a single character and returns the appropriate key name.

**Process:**
1. Check for control characters (Ctrl+A, Ctrl+C, etc.)
2. Handle ESC (Escape) to detect extended sequences
3. Return plain character for regular input

---

## Implementation Details

### Terminal Mode Management

1. Saves terminal settings with `termios.tcgetattr()`
2. Sets raw/cbreak mode with `tty.setraw()`
3. Uses non-blocking I/O with `fcntl.fcntl()` 
4. Restores original settings in `finally` block

### Escape Sequence Detection

1. When ESC is detected, reads up to 10 additional bytes
2. Stops reading on `BlockingIOError` (no more data)
3. Matches against `KEY_MAP` (sorted by length, longest first)
4. Falls back to `UNKNOWN:<repr(sequence)>` for unknown sequences

### Input Queue

- Uses `_input_queue` from `common.py` for buffered input
- Checks queue first before doing blocking read

---

## Known Issues / TODOs

1. `KEY_MAP` is minimal - many escape sequences not supported
2. No support for modified keys (Shift+, Ctrl+, Alt+ variants)
3. No support for application cursor keys (DECCKM mode)
4. Unknown escape sequences: with `debug=False` (default), returns raw sequence; with `debug=True`, logs and returns `None`
