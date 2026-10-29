# bbsengine6.io.getch Specification

## Overview

`getch.py` provides raw character input from the terminal with support for control keys and ANSI escape sequences. It handles key mapping and terminal mode management.

## Dependencies

- `common.py`: input stream management, raw session, DSR and mouse-state queries
- `keymap.py`: ANSI escape sequence to key name mapping
- `util.py`: logging
- `const.py`: constants (`ESC`, `ETX`, `EOF`)

## Public API

### Main Functions

```python
getch_str(timeout=1.0, debug=False, fire_events=True, check_notifications=True, idle=None, impl=None, **kwargs) -> str | None
getch_utf8(timeout=1.0, debug=False, fire_events=True, check_notifications=True, idle=None, impl=None, **kwargs) -> str | None
getch = getch_str  # alias exported from bbsengine6.io
```

Reads a single keypress and returns a key name or character.

Two readers share one implementation (`_getch_core`) and one key table
(`_proc_char`, `resolve_escape_sequence`). They differ only in how input is read:

- `getch_str()`: the byte-at-a-time reader. Existing behavior; the default.
- `getch_utf8()`: drains all available input and decodes characters in order.
  Emits key events with `source_func="getch_utf8"`; `getch_str()` emits `"getch_str"`.

Both must return the same key names for the same input. Neither is removed.

### Selecting the Default Reader

```python
set_getch_impl(name: str) -> None   # "str" or "utf8"; ValueError otherwise
get_getch_impl() -> str
```

`getch_str()` and `getch_utf8()` accept `impl=` per call. `impl=None` uses the
runtime default set by `set_getch_impl()` (initially `"str"`). These names are
exported from `bbsengine6.io`. The default is not changed to `"utf8"` yet.

**Parameters:**
- `timeout`: Seconds to wait for input (default: 1.0). If 0, returns immediately.
- `debug`: If True, log unknown escape sequences and return None (default: False)
- `fire_events`: If True, fire key events if dispatcher is running (default: True)
- `check_notifications`: If True, check for notifications and emit bell (default: True)
- `idle`: Optional callable called on idle (timeout) (default: None)
  - Called each time getch_str() times out waiting for input
- `impl`: `"str"` or `"utf8"` to choose the reader for this call (default: None, the runtime default)
  - Useful for updating status displays, checking notifications, etc.
- `**kwargs`: Additional arguments passed to notification handlers:
  - `args`: Application args namespace (for database connection if pool not provided)
  - `pool`: Database connection pool (alternative to args)
  - Other kwargs are passed through to notification checking

**Returns:**
- Key name string (e.g., `"KEY_UP"`, `"KEY_LEFT"`, `"KEY_ENTER"`, `"KEY_F2"`)
- Single character for regular input
- Raw escape sequence for unknown sequences (when `debug=False`)
- `None` if timeout occurred or unknown sequence (when `debug=True`)

**Raises:**
- `KeyboardInterrupt` on Ctrl+C
- `EOFError` on Ctrl+D

**Special Behavior - Notifications:**
- When pending notifications are detected, a system bell (`{bel}`) is emitted once per session
- When F2 key is pressed, `"KEY_F2"` is returned to the caller (caller can handle notifications if desired)
- Notification display (via `_show_pending_notifications()`) shows: urgency level, timestamp, recipient, and message
- Colors for notifications are configurable via echo vars: `message.criticalcolor`, `message.urgentcolor`, `message.importantcolor`, `message.routinecolor`, `message.datestampcolor`, `message.recipientcolor` (legacy `notify.*color` aliases still recognized for back-compat)
- Caller is responsible for displaying notifications after receiving F2 key event
- **Server-push read path:** notification counts are read from `bbsengine6.message.get_local_unread_count(moniker)`, populated by bed's `MessageService` via PostgreSQL `LISTEN`/`NOTIFY` on `engine_message_recipient` (triggers fire on `__message_recipient` INSERT/UPDATE in `sql/message.sql`). On a cold cache the first call falls back to a DB count via `message.get_unread_count()`. See `bed.api.message.MessageService` and `bbsengine6.startup.message_subscription` for the wiring.

---

## Key Mappings

### Control Characters

| Character | Key Name |
|-----------|----------|
| `\x01` (Ctrl+A) | `KEY_CTRL_A` |
| `\x05` (Ctrl+E) | `KEY_CTRL_E` |
| `\x08` (Backspace) | `KEY_BACKSPACE` |
| `\x0d` (Carriage Return) | `KEY_ENTER` |
| `\x09` (Tab) | `KEY_TAB` |
| `\x15` (Ctrl+U) | `KEY_CUTTOBOL` |
| `\x17` (Ctrl+W) | `KEY_CTRL_W` |
| `\x19` (Ctrl+Y) | `KEY_YANK` |
| `\x7f` (DEL) | `KEY_BACKSPACE` |

Ctrl+C (`\x03`) raises `KeyboardInterrupt` and Ctrl+D (`\x04`) raises `EOFError`;
they produce no key name. Any other control byte that is not in this table is
returned as its raw character.

`KEY_BELL` is not produced by this reader. Earlier versions of this table listed
it; no code path maps `\x07` to it.

### Bracketed Paste

When the terminal wraps a paste in `ESC[200~` ... `ESC[201~`, the reader collects
the text between the markers and returns it as one key, `"PASTE:<text>"`. Keys
after the end marker are returned individually. The body is read from the queue
first, then the stream, so a paste split across reads is kept whole. A paste with
no end marker returns what arrived after a short wait. A body is capped at 65536
characters (`PASTE_MAX`); the cap counts characters, not bytes.

`inputstring()` requests this mode with `ESC[?2004h` and turns it off on exit.
The reader recognises `ESC[200~` whenever it arrives. A terminal sends the markers only
in bracketed-paste mode, so a `PASTE:` key appears only while that mode is on.

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

### `_proc_char(char, debug=False, fire_events=True, source_func="getch_str") -> str | None`

Processes a single character and returns the appropriate key name. Shared by
both readers. `source_func` labels the key events it emits.

**Process:**
1. Fire a raw key event (if the dispatcher is running)
2. Check for control characters (Ctrl+A, Ctrl+C, etc.)
3. Handle ESC: gather the sequence with `_read_escape_tail()` and resolve it
   with `resolve_escape_sequence()`
4. Return plain character for regular input

### `resolve_escape_sequence(sequence, debug=False) -> str | None`

Maps a complete escape sequence to a `KEY_MAP` name. Unknown sequences return
the raw text, or `None` when `debug=True`. Used by both readers.

---

## Implementation Details

### Terminal Mode Management

Outside a raw session, each `getch` call:

1. Saves terminal settings with `termios.tcgetattr()`
2. Sets raw mode with `tty.setraw()`
3. Uses non-blocking I/O with `fcntl.fcntl()` while reading one key
4. Restores the original settings before returning

**Raw session (`begin_raw_session()` / `end_raw_session()`).** A caller that
edits a line (`inputstring()`) holds the tty in raw mode for the whole prompt.
While a session is active:

- `getch`, the DSR query, and the mouse-state query do not switch modes and do
  not restore cooked settings between keys. A key pressed between two reads is
  therefore never echoed (for example as `^[[C`).
- Keys already typed when the session starts are drained into `_input_queue`
  first; `tty.setraw()` would otherwise discard them.
- Output post-processing (`OPOST`) is turned back on after `tty.setraw()`, so `\n`
  is written as `\r\n` and Enter returns the cursor to column 0.
- `end_raw_session()` restores the saved settings. `inputstring()` calls it in
  `finally`, so it runs on return, exception, and Ctrl-C.

The session state lives in `io/common.py` (`_session_raw_fd`,
`_in_raw_session()`, `_restore_cooked()`). Both `getch.py` and `common.py` use
it, which avoids a circular import.

### Timeout Accuracy

- **Wall-clock timing**: Uses `time.time()` for elapsed time measurement
- **Precision**: ±10ms (was ±10% before refactoring)
- **Notification checks**: Every 100ms during idle waits
- **No busy-wait**: `select()` provides the blocking wait

### Escape Sequence Detection

A terminal can deliver one escape sequence (`ESC [ C`) in several reads, so
the reader does not stop at the first pause.

1. On ESC, `_read_escape_tail()` gathers the rest of the sequence. After each
   byte it waits up to `ESC_TAIL_WAIT` (50 ms) for the next one.
2. A CSI (`ESC [`) or SS3 (`ESC O`) sequence ends at its first final byte in
   `0x40-0x7e`. The sequence is bounded to 10 characters.
3. A lone ESC followed by a non-introducer character is the Escape key
   (`KEY_ESC`). The following character is put back on `_input_queue` so it is
   read as its own key.
4. A queued ESC is resolved from the queue in one step (`_resolve_queued_escape`),
   so a sequence drained before a prompt is not split.
5. The sequence is matched against `KEY_MAP` (sorted by length, longest first).
   Unknown sequences fall back to the raw text (or `None` when `debug=True`).

### Input Queue

- `_input_queue` in `common.py` holds keys read from the stream but not yet
  returned. Keys are returned in arrival order.
- Before waiting, `_getch_core` drains all available input from the stream into
  the queue (`drain_stream_to_queue`). A character that the text wrapper has
  already buffered is invisible to `select()`, so draining is what makes it
  visible to the next call.
- `drain_stream_to_queue()` maps a cooked-mode newline back to `\r`. The tty
  turns Enter into `\n` (ICRNL) in cooked mode, and the key table expects
  `\r` (`KEY_ENTER`).
- The DSR and mouse-state queries keep typed input: bytes that are not a reply
  are put back on the queue, not discarded.

### Notification Integration

- Before waiting for input, checks for pending notifications (queue + database)
- If notifications exist, emits bell once per session via `{bel}` command
- F2 key returns `"KEY_F2"` to caller (caller decides how to handle)
- Helper function `_show_pending_notifications()` available for caller to display notifications
- Uses thread-local storage from `bbsengine6.member` to auto-detect current user
- Gracefully disables if notification modules unavailable

### Event System (Threading-Based)

- **EventDispatcher**: Background thread manages keyboard event dispatch
- **Synchronization**: Uses `threading.Condition` for efficient waits (no busy-loop)
- **Signal mechanism**: `push_event()` immediately signals waiting dispatcher thread
- **Handler registration**: Via `register_key_event_handler(name, callback, filter_fn)`
- **Event queue**: Public `queue.Queue` available via `get_event_queue()`
- **No CPU waste**: Dispatcher sleeps until notified or 100ms timeout

---

## Performance Characteristics

### Input Thread (Main)
- **Before event system**: Unchanged
- **With event system enabled**: ~1-2µs overhead (queue append)
- **Impact**: Negligible; non-blocking

### Event Dispatcher Thread
- **Idle**: Sleeps until signaled (no busy-wait)
- **CPU usage**: ~0.1% (was ~5% before refactoring)
- **Response time**: < 1ms from event push to handler execution
- **Callback timeout**: Can run handlers with execution timeout if enabled
- **Idle callback**: Optional `idle` callable invoked on timeout for status updates

---

## Known Issues / TODOs

1. `KEY_MAP` is minimal - many escape sequences not supported
2. No support for modified keys (Shift+, Ctrl+, Alt+ variants)
3. No support for application cursor keys (DECCKM mode)
4. Unknown escape sequences: with `debug=False` (default), returns raw sequence; with `debug=True`, logs and returns `None`
5. Unmapped control bytes (other than the keys in the key tables) are not filtered by `getch`; `inputstring()` drops them from paste text
6. A `PASTE:` key carries its text in the key name. Callers that compare key names against
   a fixed set must treat any value starting with `PASTE:` as text.

---

## Recent Improvements (Refactoring)

### Phase 3: Threading.Condition for Event Dispatcher
- Replaced busy-wait with proper condition variable synchronization
- CPU idle: ~5% → ~0.1%

### Phase 4: Wall-Clock Timeout Accuracy  
- Timeout measured using `time.time()` instead of summing intervals
- Accuracy: ±10% → ±10ms

### Phase 6: Removed Recursive getch_str() Call
- Simplified notification handling
- F2 key returns to caller for handling
- No unbounded recursion or nested locks

### Phase 7: Code Clarity & Documentation
- Module-level documentation of threading model
- Enhanced docstrings for getch_str() and _proc_char()
- Better comments for escape sequence parsing

### Phase 8: Lock Management Improvements (May 2026)
- Fixed critical deadlock in getch_str() where lock was held during select()
- Lock is now released during select() to allow other threads (like echo) to proceed
- Lock is only held for:
  1. Checking input queue
  2. Getting file descriptor and terminal settings
  3. Setting terminal raw mode
  4. Reading character from input stream
  5. Restoring terminal settings in finally block
- This fix resolves hang when inputstring() calls echo() during getch() wait
- Result: KEY_ENTER and other keys now properly handled in inputstring()

### Keyboard Input Fixes (bbsengine6, 2026)

- **Keys echoed between reads (`^[[C`)**: the tty was restored to cooked mode after
  every `getch`. Fixed by the raw session (see Terminal Mode Management).
- **Split escape sequences**: a sequence arriving in pieces left its tail as text.
  Fixed by `_read_escape_tail()`.
- **Keys dropped before raw mode**: `tty.setraw()` discards pending input. Fixed by
  draining into `_input_queue` before the mode switch.
- **Enter as `\n`**: cooked-mode Enter is mapped back to `\r` (see Input Queue).
- **Lock held during redraw**: a non-reentrant lock was held while `echo()`
  re-acquired it. Handled in `inputstring()`, not in `getch`.

