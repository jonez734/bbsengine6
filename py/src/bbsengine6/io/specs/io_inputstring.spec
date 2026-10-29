# asimov.io.inputstring Specification

## Overview

`inputstring.py` is a terminal-based line input module with cursor editing, cut/yank, and tab completion. It provides a readline-like editing experience within the terminal.

## Dependencies

- `echo.py`: Terminal output with command processing
- `getch.py`: Raw character input
- `common.py`: Terminal state and cursor position
- `terminal.py`: Terminal size detection
- `util.py`: Logging

## Global State

- `yank_buffer`: Clipboard for cut/yank operations
- `KEY_ACTIONS`: Dictionary mapping key names to handler functions

## Completer Class

```python
class Completer:
    """Callable class for tab completion."""
    
    def __init__(self, get_matches=None, **kwargs):
        """Initialize with optional get_matches function and kwargs.
        
        Args:
            get_matches: Function that takes prefix and returns list of matches.
            **kwargs: Arbitrary parameters (e.g., conn, pool) passed to get_matches.
        """
        
    def get_matches(self, prefix, **kwargs):
        """Override this in subclass to provide completions.
        
        Args:
            prefix: The text prefix to match against.
            **kwargs: Additional parameters (e.g., conn, pool) passed from inputstring.
            
        Returns:
            List of matching strings.
        """
        
    def __call__(self, buffer, curpos, **kwargs) -> list[str]:
        """Called by inputstring to get completions."""
```

### Usage Examples

**Database-backed (override get_matches):**
```python
class PlayerCompleter(Completer):
    def get_matches(self, prefix, **kwargs):  # noqa: PLE
        return db.query("SELECT name FROM players WHERE name LIKE ?", prefix + "%", **kwargs)

inputstring("Select player: ", completer=PlayerCompleter(conn=db_conn))
```

**Function passed to constructor with kwargs:**
```python
def name_completer(prefix, conn=None):
    return db.query("...", prefix, conn)

inputstring("Name: ", completer=Completer(name_completer, conn=db_conn))

```

## Public API

### Main Function

```python
inputstring(prompt="> ", oldvalue="", /, history=False, pagesize=10, beep_on_error=True,
            f1_help=None, help=None, function_key_handlers=None, **kwargs) -> str
```

Reads one line with line editing. Returns the entered text. `prompt` and
`oldvalue` are positional-only.

**Parameters:**
- `prompt`: String to display before input (default: `"> "`)
- `oldvalue`: Pre-fill the buffer with this value (default: `""`)
- `history`: Enable UP/DOWN history for this call (default: False)
- `pagesize`: Characters jumped by PAGE UP / PAGE DOWN (default: 10)
- `beep_on_error`: Beep on errors such as Delete at end of line (default: True)
- `f1_help`: Help text (str) or callable returning it, shown on F1 (default: None)
- `help`: Alias for `f1_help`
- `function_key_handlers`: Dict mapping `KEY_F2`..`KEY_F12` to handlers
- `max_len`: Maximum input length (default: 255, via `**kwargs`)
- `max_width`: Display width for scrolling (default: 80, via `**kwargs`)
- `mask`: If set, mask input (e.g., `mask="*"` for password)
- `completer`: Tab completion callback; see Tab Completion
- `verify`: Validation callback `verify(buffer, **kwargs) -> bool`, run on Enter
- `args`: Application args namespace (passed to verify and completer)
- `pool`: Database connection pool (passed to completer via kwargs)
- `insert_tabs`: If True, a tab inside pasted text is inserted as `\t`
  (for an editor). Default False: a pasted tab is shown as a space. A typed Tab
  is always completion, regardless of this flag.
- `noneok`: Allow empty input (default: `True`). With `noneok=False`, Enter on an
  empty line beeps and reprompts; the caller gets input only once something is typed.
- `allowed`: String of characters accepted while typing and pasting (default: `None`,
  no restriction). Any other character beeps and is dropped.
- `filter`: Regular expression the whole buffer must match on Enter (default: `None`).
  A non-matching value beeps and reprompts, as a failed `verify` does. The pattern is
  checked on Enter only, not per keystroke, so a partial value such as `-` can be typed.
  An invalid pattern raises `re.error` from the call; the terminal is restored first.
- `**kwargs`: Remaining arguments are passed to the `completer` callback.

**Terminal state during the call:**
- The tty is held in raw mode for the whole prompt (`begin_raw_session()`), and
  restored on return, exception, and Ctrl-C (see `io_getch.spec`).
- The terminal's mouse-reporting modes (1000, 1002, 1003, 1006) are queried
  (DECRQM) before editing. Only modes the terminal reports as on are turned off
  for the prompt, and only those are turned back on at exit. A mode with no reply
  is never written, so a tab that had mouse tracking enabled keeps it.
  `common.MOUSE_STATE_MANAGED = False` disables this.

**Concurrency:** the module-level key table `KEY_ACTIONS` is shared by all
callers. Key handlers are looked up under `_key_actions_lock`. A redraw runs
outside `_current_stream_lock` because `echo()` takes that lock.


---

### Key Mapping Functions

```python
add_key_mapping(key_string, action_lambda)
remove_key_mapping(key_string)
```

`add_key_mapping()` replaces the handler for a key in the shared `KEY_ACTIONS`
table and records the handler it replaced. `remove_key_mapping()` undoes the most
recent add for that key by restoring the earlier handler. If the key had no
handler before the add, the key is removed. This lets an editor take over
`KEY_LEFT`, `KEY_BACKSPACE`, and others and give them back, so later prompts keep
the defaults.

---

### Helper Functions

```python
move_cursor(row, col)
```

Move cursor to specified position.

---

```python
get_current_word(buffer, curpos) -> (prefix, word_start, word_end)
```

Find the word at the current cursor position.

**Returns:**
- `prefix`: Text before the word
- `word_start`: Starting index of the word
- `word_end`: Ending index of the word

Words are defined as alphanumeric sequences (`\w+`).

---

```python
common_prefix(matches) -> str
```

Return the common prefix of a list of strings.

---

## Key Bindings

| Key | Action |
|-----|--------|
| `KEY_LEFT` | Move cursor left |
| `KEY_RIGHT` | Move cursor right |
| `KEY_HOME` / `Ctrl+A` | Move to line start |
| `KEY_END` / `Ctrl+E` | Move to line end |
| `KEY_BACKSPACE` | Delete character before cursor |
| `KEY_CTRL_W` | Cut previous word (Ctrl+W) |
| `KEY_CUTTOBOL` | Cut to beginning of line |
| `KEY_YANK` | Paste from yank buffer |
| `KEY_F1` | Show `f1_help` inline |
| `KEY_ENTER` | Accept input |
| `KEY_TAB` | Tab completion (see Tab Completion) |

`KEY_INSERT` toggles insert and overwrite mode; overwrite mode shows the `[OVR]`
indicator. The toggle is local to each call. `KEY_YANK` is registered, but no byte
in the reader produces it yet (Ctrl+Y is `\x19`, not mapped in `getch.py`).

## Handler Functions

All handlers follow the signature:
```python
def handler(buffer, curpos, scroll_offset, max_width) -> (buffer, curpos, scroll_offset)
```

### Built-in Handlers

- `handle_left`: Move cursor left (bell if at start)
- `handle_right`: Move cursor right (bell if at end)
- `handle_home`: Jump to line start
- `handle_end`: Jump to line end
- `handle_backspace`: Delete character before cursor
- `handle_cuttobol`: Cut from cursor to beginning of line
- `handle_cutpreviousword`: Cut previous word (word boundary: `\w`)
- `handle_yank`: Paste yank buffer at cursor
- `handle_help`: Stub handler (logs trace)
- `handle_key_enter`: Process Enter key with optional verification

## Display Functions

```python
redraw_line(prompt, buffer, max_len, start_row, start_col, curpos, scroll_offset, max_width, mask=None)
```

Clear and redraw the input line. Handles both regular and masked input.

---

```python
print_matches(matches) -> int
```

Print tab completion matches in columns. Returns number of lines printed.

## Tab Completion

`handle_tab_manager` processes Tab. Its behavior, by word under the cursor:

- **Non-empty word, one match**: the word is replaced by the match.
- **Non-empty word, several matches**: the buffer is unchanged; the matches are
  listed on a second press of Tab on the same word.
- **Non-empty word, no matches**: bell; the buffer is unchanged.
- **Empty word**: Tab lists every completion. A further Tab on the same list
  rings the bell.
- **Repeated Tab on a single match**: bell.

A Tab only updates completion state; it does not reach the character-insert
branch, which clears that state.

A typed Tab is one keypress and always goes to completion. Tab inside pasted
text is handled by the paste path (see Paste Input).

**Scrolling Logic:**
When matches are printed, the terminal may scroll. `handle_tab_manager` detects this and updates `start_row` to ensure `redraw_line` draws at the correct screen position.

**Callback signature:**
```python
def completer(word, curpos=..., **kwargs) -> list[str]
```

**Behavior:**
- The completer receives the **word under the cursor**, not the whole line. For
  a second word, `hello ban` + Tab passes `ban`, and the result is `hello banana`.
  The word is `""` when the cursor is not on a word.
- `curpos` is passed by keyword.
- Additional `**kwargs` passed to `inputstring` are forwarded to the completer.
- Returns the list of matching strings (replacement words for the word under the cursor).
- The test script `tests/tab_complete_check.py` checks these cases on a pty.


## Paste Input

A paste delivers several characters at once. When two or more keys are queued,
`_take_paste_burst()` takes the leading run of text and inserts it as text:

- Printable characters are inserted literally. A newline or carriage return ends
  the entry, as Enter does.
- A tab is paste text only when printable text follows it in the queue. A Tab
  with nothing but Tabs (or nothing) after it is left for completion, so a typed
  Tab or double Tab still completes.
- Backspace (`\x7f`, `\x08`) stops the batch and runs as a key.
- Other control bytes are dropped from paste text.
- An escape sequence at the head of the queue is a real key; it is not batched.
- Paste text is truncated at `max_len`.

Pasted tabs become a space unless `insert_tabs=True`.

## Input Verification

The `verify` callback is called when Enter is pressed:

```python
def verify(buffer, **kwargs) -> bool
```

- `buffer`: The current input string
- `kwargs`: Contains `args`, `pool`, and other optional params passed to `inputstring()`
- Return `True` to accept input
- Return `False` to reject (bell sounds, input remains)
- Can raise exception to handle errors

## Display Logic

The main loop manages display:

1. Check `_input_dirty` flag → refresh if needed
2. Compare display string → update if changed
3. Position cursor
4. Read key input
5. Process through handlers
6. Update scroll offset

### Scroll Handling

- Input scrolls horizontally when `curpos >= scroll_offset + max_width`
- Scroll offset adjusts to keep cursor visible

## Recent Fixes (bbsengine6, 2026)

- **Empty Enter**: `noneok` now controls it (default accepts; `noneok=False` reprompts).
- **`filter` and `allowed`**: implemented as documented in Public API.
- **Enter in a paste batch**: an Enter at the head of a batch is a command and waits
  for the key path, so `noneok` and `filter` apply to it. Text typed after a rejected
  Enter is kept.
- **Key handler run under a lock**: handlers now run outside `_key_actions_lock`;
  they write to the terminal, which takes another lock.

- **Arrow keys leaked as `^[[D`**: fixed by the raw session (tty stays raw during the prompt).
- **Click-drag selection broken in the prompt tab**: mouse modes were reset even when
  the terminal did not answer DECRQM. Now only modes reported on are changed.
- **Pasted characters dropped, Tab and Ctrl-A in paste**: the paste batch inserts text
  literally (see Paste Input).
- **Second-word completion**: the completer receives the word under the cursor.
- **Double Tab on empty input printed nothing**: a Tab fell into the insert branch and
  cleared completion state. Fixed; a double Tab lists all completions.
- **Default key handlers lost after an editor session**: `remove_key_mapping()` now
  restores the handler an override replaced.
- **Self-deadlock on redraw**: a redraw ran under `_current_stream_lock` and `echo()`
  re-acquired it. The redraw now runs outside the lock.

## Recent Fixes (May 2026)

### Lock Contention with getch()
- **Problem**: Lock was acquired immediately before `getch()` call, causing contention
- **Solution**: Removed unnecessary lock acquisition right before `getch()`
- **Result**: `getch()` can now properly manage locks without external interference

### Cursor Positioning Echo Codes
- **Problem**: `{curpos:...}` escape codes in echo() were interfering with getch() input processing
- **Solution**: Replaced `{curpos:...}` echo calls with raw ANSI escape sequences (CSI codes)
- **Benefit**: Avoids echo's command processing which was consuming input or corrupting terminal state
- **Result**: KEY_ENTER and all key processing now works correctly in inputstring()

## Known Issues / TODOs

0. **Not built from the plan** (documented so the gaps are visible):
   - Per-call key table: `KEY_ACTIONS` is still shared (see Concurrency).
   - Bracketed paste (`ESC[200~`) is not recognized; pastes are detected by burst only.
   - Typed-overflow beep and an explicit `PASTE` event are not implemented.
   - Ctrl+Y (`\x19`) is not mapped to `KEY_YANK` in the reader; Ctrl+W (`\x17`) is not mapped to `KEY_CTRL_W` either.
   - Asimov has its own copy of `inputstring` and `inputinteger`
     (`asimov/src/asimov/io/`). It is a separate submodule and is not updated here;
     its `noneok` default is still `False`, and it ignores `filter` and `allowed`.
   - `inputinteger` validates a single integer. Its regex does not accept a list of
     values (`1 2`), although the function can return a list.
1. ~~`get_current_word()` is a stub~~ - now properly finds word at cursor position using alphanumeric boundaries
2. ~~Some echo calls use inconsistent escaping~~ (FIXED - standardized to `"{command}"` for static commands)
3. ~~Lock contention between inputstring() and getch()~~ (FIXED - removed unnecessary lock acquisition)
4. ~~Cursor positioning interfering with input~~ (FIXED - use raw ANSI codes instead of echo commands)
