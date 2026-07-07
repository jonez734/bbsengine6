# ed.spec - Visual Editor Specification

## Overview

A terminal-based visual editor built on bbsengine6.io for editing text files in a BBS environment. Supports visual mode (full-screen editing) with line wrapping, justification, and read-only lines.

## Package Structure

```
ed/
├── __init__.py           # Package exports, mode dispatch
├── common/               # Shared code - all editor modes
│   ├── __init__.py
│   ├── state.py          # Dataclasses: BufferLine, EditorBuffer, EditorState, Justify
│   ├── buffer.py         # Buffer manipulation functions
│   ├── fileops.py        # File I/O operations
│   ├── ui.py             # Shared UI: init_screen, help, notifications, bottombar
│   └── keys.py           # Key registry + common handlers
├── visual/               # Visual editor mode
│   ├── __init__.py
│   ├── keys.py           # Visual-specific key handlers
│   └── render.py         # Full-screen rendering
└── line/                 # Line editor mode (Image BBS-style)
    └── __init__.py       # Main line editor implementation
```

## Dataclasses (common/state.py)

```python
class Justify(Enum):
    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()

@dataclass
class BufferLine:
    text: str                    # Line content (may end with "{f6}" for hard return)
    justify: Justify = Justify.LEFT
    read_only: bool = False
    soft_wrap: bool = True        # True=wrapped at width, False=hard return
    group_id: int | None = None  # Original line number for wrapped continuations

@dataclass
class EditorBuffer:
    lines: list[BufferLine] = field(default_factory=list)

@dataclass
class EditorState:
    filepath: str | None = None
    buffer: EditorBuffer = field(default_factory=EditorBuffer)
    cursor_x: int = 0              # Column position (0-based)
    cursor_y: int = 0              # Line position (0-based)
    scroll_offset: int = 0        # Vertical scroll position
    modified: bool = False        # Needs save indicator
    ctrl_k_mode: bool = False      # After Ctrl-K pressed
    width: int = 0                 # Terminal width
    height: int = 0                # Terminal height
```

## Key Registry (common/keys.py)

### Registry Pattern
- Global `KEY_ACTIONS: dict[str, list[Callable]]` - key name -> list of handlers
- `register_key_handler(key, handler)` - modes register their handlers
- `handle_key(ch, state) -> EditorState` - dispatch to registered handlers

### Handler Signature
```python
def handler(state: EditorState) -> EditorState:
    # Return modified state, or state unchanged if not applicable
    return state
```

### Common Handlers (registered in common/keys.py init)
| Key | Action |
|-----|--------|
| KEY_F1 | Show help, redraw editor |
| KEY_F2 | Show notifications, redraw editor |
| KEY_CTRL_K | Toggle ctrl_k_mode |
| ctrl_k + 'x' | Exit (prompt if modified) |
| Regular chars | Insert at cursor via buffer.insert_char() |

### Visual-Specific Handlers (registered in visual/keys.py)
| Key | Action |
|-----|--------|
| KEY_UP | cursor_y -= 1, clamp cursor_x |
| KEY_DOWN | cursor_y += 1, clamp cursor_x |
| KEY_LEFT | cursor_x -= 1; if cursor_x == 0 and cursor_y > 0: unwrap with previous |
| KEY_RIGHT | cursor_x += 1; if at terminal width: word wrap |
| KEY_HOME | cursor_x = 0 |
| KEY_END | cursor_x = len(line) |
| KEY_PAGEUP | scroll_offset -= height |
| KEY_PAGEDOWN | scroll_offset += height |
| KEY_BACKSPACE | Delete char before cursor; if at col 0: unwrap |
| KEY_DELETE | Delete char at cursor |
| KEY_ENTER | Split line at cursor: add "{f6}", new line, cursor_x=0, cursor_y+=1 |

## Buffer Functions (common/buffer.py)

### insert_char(state, char) -> state
- Insert character at cursor position in current line
- If cursor_y out of bounds: append new BufferLine
- If cursor_x at terminal width: call wrap_line() first
- If line is soft-wrapped: call recalculate_wrap()
- Set modified = True

### delete_char(state) -> state
- Delete character at cursor position
- If line is soft-wrapped: call recalculate_wrap()
- Set modified = True

### backspace(state) -> state
- Delete character before cursor
- If cursor_x == 0 and cursor_y > 0: call unwrap_line()
- Set modified = True

### wrap_line(state) -> state
- Called when cursor_x reaches terminal width
- Find last space in current line
- Split at space: before -> current line, after -> new BufferLine
- Set soft_wrap=True, group_id = original line number
- Cursor moves to start of new line (cursor_x=0, cursor_y+=1)
- Set modified = True

### unwrap_line(state) -> state
- Called when cursor_x == 0 and KEY_LEFT pressed, or BACKSPACE at col 0
- Join current line with previous line
- Remove current line from buffer
- cursor_y -= 1, cursor_x = len(previous_line)
- Set modified = True

### split_line(state) -> state
- KEY_ENTER handler
- Current line: text[:cursor_x] + "{f6}"
- New line: BufferLine(text=text[cursor_x:], soft_wrap=False)
- cursor_x = 0, cursor_y += 1
- Set modified = True

### recalculate_wrap(state, line_index) -> state
- Recalculate word wrap for group of soft-wrapped lines starting at line_index
- Re-number: base line keeps original group_id, continuations get 'a', 'b', etc.
- Update cursor_y to stay on same visual line if possible
- Set modified = True

## File Operations (common/fileops.py)

### load_file(filepath) -> EditorBuffer
- Read file content
- Split into lines (strip trailing newlines)
- Create BufferLine for each line (soft_wrap=False, group_id=None)
- Return EditorBuffer

### save_file(state) -> bool
- Write buffer.lines to state.filepath
- Strip "{f6}" from line endings when saving (they're for display only)
- Handle read-only lines: skip or error
- Return True on success

### prompt_save(state) -> bool
- Prompt user: "Save changes? (Y/n)"
- If yes: call save_file()
- Return True if saved or user chose not to save, False if cancelled

## UI Functions (common/ui.py)

### init_screen() -> None
- Call io.screen.init() if not already initialized
- Set state.width = io.terminal.width()
- Set state.height = io.terminal.height()

### show_help() -> None
- Display help text
- Keys: arrows navigate, Enter splits, F1 help, F2 messages, Ctrl+K x exits

### show_notifications(moniker) -> None
- Call notify.show_pending_notifications(moniker) or similar
- Screen is cleared during display
- Caller (keys.py) handles redraw after return

### exit_prompt(state) -> bool
- If not modified: return True (exit allowed)
- Prompt: "File modified. Save? (Y/n/c)"
- Y: save and exit -> return True
- n: discard and exit -> return True
- c: cancel -> return False

### Bottombar Fragment
- Callable returning: `f"{filepath or '(new file)'}{' * ' if modified else ''} | F1:Help"`
- Registered via bbsengine6.bottombar.register_bottombar_fragment()
- Notification status auto-prepended via get_notification_status()

## Rendering (visual/render.py)

### render(state, **kwargs) -> None
- Clear screen with io.echo("{home}{clear}", end="", flush=True)
- Set scrolling region
- For each visible line (respecting scroll_offset):
  - Apply justify (left/center/right within width)
  - Render line number + continuation marker
  - Output via io.echo()
- Position cursor at (cursor_y - scroll_offset, cursor_x)
- Update bottombar

### render_line(line, width) -> str
- Apply justify:
  - LEFT: text.ljust(width)
  - CENTER: text.center(width)
  - RIGHT: text.rjust(width)
- Return formatted string

### Line Numbering
- group_id = None: display as "N: " (1-based)
- group_id = n, soft_wrap = True: display as "Na: ", "Nb: ", etc. (continuation)
- group_id = n, soft_wrap = False, n > 0: display as "N: " (hard return)

## Line Editor (line/__init__.py)

### Overview
C64 Image BBS 3.0-style line-based editor. User enters line numbers or "." commands to edit text.

### Usage
```python
from bbsengine6.ed import run
result = run(args, moniker, mode="line", filepath=None, input_func=mock_input, test_mode=True)
```

### Input Modes
1. **Line Number Mode**: Enter a number to edit that specific line
2. **Command Mode**: Enter "." followed by a command letter
3. **New Line Mode**: Press KEY_ENTER to add a new empty line

### Commands (prefixed with ".")
| Command | Description |
|---------|-------------|
| `.h` | Show help |
| `.e` | Edit line (prompts for line number) |
| `.x` | Exit (prompts if modified) |
| `.s` | Save (prompts for filename if new) |
| `.l` | List all lines with numbers |
| `.i` | Insert new line at specified position |
| `.d` | Delete line(s) - single number or range (e.g., "1-5") |
| `.r` | Read file into buffer |
| `.n` | New - clear buffer (prompts if modified) |

### Test Mode
The line editor supports test mode via `test_mode=True` and `input_func` parameters:
- `test_mode=True` skips screen initialization
- `input_func` provides mock input for automated testing

### Key Behaviors
- Empty line added via KEY_ENTER sets modified flag
- Exit command prompts to save if modified
- Edit command replaces line content
- List command displays all lines with 1-based numbering

## API (ed/__init__.py)

### Entry Point
```python
def run(args, moniker, mode="visual") -> str | None:
    """Main editor entry point.
    
    Args:
        args: Application args (for screen.init, etc.)
        moniker: Current user moniker (for notifications)
        mode: "visual" or "line"
    
    Returns:
        Edited content as string, or None on cancel
    """
```

### Backward-Compatible API (for module system)

See `module.spec` for the complete module ABI specification.

## Encoding Requirements

- No UTF-8 characters directly in source code
- Use io.echo_commands for emojis/colors
- Example: `:smile:`, `{green}`, etc.

## Screen Dimensions

- Editor width: io.terminal.width() characters
- Editor height: io.terminal.height() lines
- Word wrap at width (not MAX_WIDTH constant)

## Notifications

- Bottombar auto-shows "F2: notify (N)" via get_notification_status()
- KEY_F2 triggers notification display
- After F2 returns: editor redraws (screen cleared and re-rendered)

## Soft Wrap Behavior

- Default: soft_wrap = True
- Wrapped lines display with continuation markers (1a, 1b, etc.)
- Editing any line in wrapped group triggers recalculate_wrap()
- Recalculate_wrap() also updates group_id numbering

## Read-Only Lines

- BufferLine.read_only = True prevents editing
- Key handlers check read_only and beep if attempted
- save_file() skips or errors on read-only lines
