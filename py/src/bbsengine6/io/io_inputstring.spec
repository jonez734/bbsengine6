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
inputstring(prompt="> ", oldString="", **kwargs) -> str
```

Returns the input string.

**Parameters:**
- `prompt`: String to display before input (default: `"> "`)
- `oldString`: Pre-fill input with existing value
- `max_len`: Maximum input length (default: 255)
- `max_width`: Display width for scrolling (default: 80)
- `mask`: If set, mask input (e.g., `mask="*"` for password)
- `completer`: Callback for tab completion: `completer(buffer, curpos, **kwargs) -> list[str]`
- `verify`: Callback for input validation: `verify(args, buffer, **kwargs) -> bool`
- `args`: Arguments passed to verify callback
- `noneok`: Allow empty input (default: False)
- `**kwargs`: Additional arguments are passed to the `completer` callback.


---

### Key Mapping Functions

```python
add_key_mapping(key_string, action_lambda)
remove_key_mapping(key_string)
```

Register/remove custom key handlers.

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
| `KEY_F1` | Help (stub) |
| `KEY_ENTER` | Accept input |
| `KEY_TAB` | Tab completion |

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

The `handle_tab_manager` function processes tab completion and handles potential scrolling:

1. First tab: Show common prefix of matches
2. Second tab on same matches: Print all matches
3. Single match: Insert match automatically
4. No matches: Bell sound
5. Tab on single match (no other options): Bell sound

**Scrolling Logic:**
When matches are printed, the terminal may scroll. `handle_tab_manager` detects this and updates `start_row` to ensure `redraw_line` draws at the correct screen position.

**Callback signature:**
```python
def completer(buffer, curpos, **kwargs) -> list[str]
```

Returns list of possible completions for the current word.

**Behavior:**
- The completer receives the current word (not prefix) as the first argument, OR an empty string if no word is present.
- Additional `**kwargs` passed to `inputstring` are forwarded to the completer.
- Returns list of matching strings


## Input Verification

The `verify` callback is called when Enter is pressed:

```python
def verify(args, buffer, **kwargs) -> bool
```

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

## Known Issues / TODOs

1. ~~`get_current_word()` is a stub~~ - now properly finds word at cursor position using alphanumeric boundaries
2. ~~Some echo calls use inconsistent escaping~~ (FIXED - standardized to `"{command}"` for static commands)
