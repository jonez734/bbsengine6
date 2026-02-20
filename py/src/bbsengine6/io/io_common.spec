# asimov.io.common Specification

## Overview

`common.py` provides core utilities for terminal I/O including stream management, cursor position queries, and terminal state tracking.

## Dependencies

- Standard library: `os`, `re`, `sys`, `tty`, `fcntl`, `termios`, `threading`, `collections`
- `const.py`: MAX_TERMINAL_WIDTH, BEL, ESC
- `terminal.py`: Terminal size detection

## Data Classes

### `Token`

Represents a parsed token from input text.

| Field | Type | Description |
|-------|------|-------------|
| `kind` | str | Token type (WORD, WHITESPACE, F6, RGB, etc.) |
| `value` | str | Literal string or command |
| `args` | List | Positional arguments |
| `kwargs` | Dict | Keyword arguments |
| `text` | str | Processed text (e.g., `\n` for `{f6}`) |
| `repeat` | int | Repeat count |
| `raw` | str | Raw input that generated token |

---

### `TerminalState`

Tracks current terminal state.

| Field | Type | Description |
|-------|------|-------------|
| `cursor_row` | int | Current cursor row |
| `cursor_col` | int | Current cursor column |
| `wordwrap` | bool | Word wrap enabled |
| `has_color` | bool | Color support |
| `hidden` | bool | Cursor hidden |
| `width` | int | Terminal width |
| `acs` | bool | Alternate Character Set mode |
| `raw` | bool | Raw mode |
| `decdhl` | bool | Double-height line |
| `decdwl` | bool | Double-width line |

## Global State

| Variable | Type | Description |
|----------|------|-------------|
| `_current_input_stream` | file | Input stream (default: stdin) |
| `_current_output_stream` | file | Output stream (default: stdout) |
| `_current_stream_lock` | threading.Lock | Thread-safe lock for I/O |
| `_input_queue` | deque | Buffered input characters |
| `_terminal_state` | TerminalState | Current terminal state |
| `_terminal_state_stack` | list | Stack for save/restore |
| `_input_dirty` | bool | Flag for input refresh needed |

## Functions

### Stream Management

```python
set_output_stream(stream)
set_input_stream(stream)
write_current_output_stream(s, flush=False)
read_current_input_stream(size=1) -> str
```

### Terminal Queries

```python
get_cursor_position(timeout=1.0) -> tuple[int, int]
```

Returns current cursor position as (row, col).

---

```python
get_terminal_status() -> bool | None
```

Returns terminal ready status:
- `True`: OK (ESC[0n)
- `False`: Error (ESC[3n)
- `None`: Unknown

---

```python
get_dsr(mode="curpos", timeout=1.0) -> tuple[int, int] | str
```

Device Status Report - queries terminal for status.

---

```python
drain_stream_to_queue(stream, queue)
```

Read all available characters from stream into queue (non-blocking).

## Usage

```python
from asimov.io.common import (
    Token, TerminalState, _terminal_state,
    get_cursor_position, set_input_stream
)
```
