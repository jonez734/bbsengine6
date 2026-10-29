# bbsengine6.io.common Specification

## Overview

`common.py` holds the shared I/O state for the io package: the input and output
streams and their lock, the input queue, the terminal state, and the terminal queries
(cursor position, status). It also holds the raw-session and mode-switching helpers
that `getch`, `inputstring` and the bottom bar use.

Most names here are private (leading underscore) and are used only inside io. The
public ones are listed in this spec.

## Dependencies

- Standard library: `os`, `re`, `sys`, `select`, `tty`, `fcntl`, `termios`,
  `threading`, `collections`, `time`
- `const.py`: `ESC`, `CSI`, `DEFAULT_INDENT_CHAR`
- `terminal.py`: terminal size

## Data classes

### `Token`

A parsed token from echo input. Fields: `kind` (str, e.g. `WORD`, `F6`, `RGB`),
`value` (the literal text or command), `args` (list), `kwargs` (dict), `text` (the
processed text, such as `\n` for `{f6}`), `repeat` (int, default 1), `raw` (the input
that produced it).

### `TerminalState`

The software copy of the terminal's state, used by `echo()`.

| Field | Default | Description |
|-------|---------|-------------|
| `cursor_row`, `cursor_col` | 1, 1 | Cursor position as `echo()` last placed it |
| `wordwrap` | `True` | Word wrap |
| `has_color` | `True` | Colour output |
| `hidden` | `False` | Cursor hidden |
| `width` | 100 | Width used by `echo()` |
| `acs` | `False` | Alternate character set (box drawing) |
| `raw` | `False` | Commands treated as text |
| `decdhl`, `decdwl` | `False` | Double-height and double-width lines |
| `indent` | 0 | Indent width for `{indent:n}` |
| `indent_char` | `" "` | Indent character |

`cursor_row` and `cursor_col` follow `{curpos}` commands. They do not follow raw
ANSI cursor movements (`ESC [ n ; m H` written with `raw=True`), so a raw move makes
them stale.

## Global state

| Name | Type | Description |
|------|------|-------------|
| `_current_input_stream` | file | Input stream (default `sys.stdin`) |
| `_current_output_stream` | file | Output stream (default `sys.stdout`) |
| `_current_stream_lock` | `threading.Lock` | Serialises stream reads and writes. Not reentrant. |
| `_terminal_state_lock` | `threading.Lock` | Guards `_terminal_state` |
| `_terminal_state` | `TerminalState` | Current software terminal state |
| `_terminal_state_stack` | list | Saved states for `{decsc}` / `{decrc}` |
| `_terminal_state_stack_enabled` | bool | `False`: one save slot, restore does not pop |
| `_input_queue` | deque | Keys read but not yet returned to a caller |
| `_input_queue_lock` | `threading.Lock` | Guards `_input_queue` |
| `_session_raw_fd` | int or None | The fd held in raw mode by a raw session |

`_input_dirty` is not in this module. It is a global of `inputstring.py`.

## Public functions

### Streams

```python
set_output_stream(stream)
set_input_stream(stream)
write_current_output_stream(s, flush=False)
read_current_input_stream(size=1) -> str
```

Set or use the streams that every io function reads and writes. Tests and tools set
a pseudo-terminal stream here.

### Cursor position

```python
get_cursor_position(timeout=1.0) -> tuple[int, int]
```

Asks the terminal for its cursor position (DSR `ESC [ 6 n`) and returns `(row, col)`,
1-based.

**Raises `TimeoutError`** if no reply arrives within `timeout` seconds. A terminal that
does not answer the query makes every caller wait the full timeout. Observed: 0.50 s
with `timeout=0.5` and no reply.

`{decsc}` and `inputstring()`'s first draw both call this. See `io_echo.md`.

### Status

```python
get_terminal_status() -> bool | None
```

DSR status query (`ESC [ 5 n`):
- `True`: the terminal replied `ESC [ 0 n` (ready)
- `False`: the terminal replied `ESC [ 3 n` (malfunction)
- `None`: any other reply, or no reply

### Device status reports

```python
get_dsr(mode="curpos", timeout=1.0) -> tuple[int, int] | str
```

The general query behind `get_cursor_position` and `get_terminal_status`.

### Input queue

```python
drain_stream_to_queue(stream, queue)
```

Reads every character the stream can give without blocking, into `queue`, in order.
A cooked-mode newline (`\n`, from Enter under ICRNL) is stored as `\r`, which is the
key the reader expects for Enter.

## Raw sessions

```python
begin_raw_session() -> None
end_raw_session() -> None
```

`begin_raw_session()` drains pending input into `_input_queue`, then puts the input
tty in raw mode and keeps the saved settings. `end_raw_session()` restores them.

Raw mode is `tty.setraw()` with output post-processing (`OPOST`) turned back on. `setraw()`
clears `OPOST`, which stops the tty turning `\n` into `\r\n`; without it, a bare `\n` (the
`{f6}` newline, and so the Enter key) moves the cursor down without returning to column 0.
Input stays raw.

While a session is open, `getch`, the DSR query, and the mouse-state query do not
switch modes and do not restore cooked settings between keys. This is why a key
pressed between reads is not echoed (`^[[C`). `inputstring()` opens a session in its
wrapper and closes it in `finally`.

Calling `begin_raw_session()` when the input is not a terminal does nothing.

## Bracketed paste

```python
BRACKETED_PASTE_MANAGED = True
bracketed_paste_on() -> bool
bracketed_paste_off(enabled: bool) -> None
```

`bracketed_paste_on()` writes `ESC [ ? 2004 h` and returns `True`. `bracketed_paste_off`
writes `ESC [ ? 2004 l` if `enabled` is true. With `BRACKETED_PASTE_MANAGED = False`,
`bracketed_paste_on()` writes nothing and returns `False`.

## Mouse state

```python
MOUSE_MODES = (1000, 1002, 1003, 1006)
MOUSE_STATE_MANAGED = True
mouse_state_push() -> dict[int, bool] | None
mouse_state_pop(saved) -> None
```

Mouse reporting makes the terminal send button and motion events to the application,
which stops it selecting text on click-drag. `inputstring()` turns the four modes off
for the prompt and restores them after.

- `mouse_state_push()` asks the terminal for each mode (`ESC [ ? mode $ p`), then
  resets **all four** modes, whatever the replies said. It returns the replies, with
  `None` for a mode that gave no reply.
- `mouse_state_pop(saved)` sets back only the modes that were reported on.
- `MOUSE_STATE_MANAGED = False` skips both.

A mode that gave no reply is left off after the prompt, not restored. VTE was observed
to reply "reset" (`2`) for all four modes during a prompt.

### Tracing

`BBSENGINE_MOUSE_TRACE=<file>` appends the raw query replies, each mode write, and the
restore to `<file>`. It is off by default and is for diagnosis.

## Usage

```python
from bbsengine6.io.common import get_cursor_position, set_input_stream
```
