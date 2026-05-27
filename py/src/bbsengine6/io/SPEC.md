# bbsengine6.io Specification

## Overview

`bbsengine6.io` is the terminal I/O module for bbsengine6. It provides rich terminal output with ANSI escape codes, input handling, color palettes, and terminal utilities.

## Package Structure

```
io/
├── __init__.py              # Public API exports
├── _version.py              # Version info
├── const.py                 # Terminal constants
├── terminal.py              # Terminal size utilities
├── common.py                # Token and I/O primitives
├── echovars.py              # Echo variables
├── echo.py                  # Main echo function with formatting
├── palette.py               # Color palettes
├── util.py                  # Logging utilities
├── keymap.py                # Key mappings
├── lib.py                   # Library utilities
├── screen.py                # Screen utilities
├── getch.py                 # Character input
├── getstr.py                # String input
├── input.py                 # [DEPRECATED] Input handling - use inputstring.py
├── inputstring.py           # String input
├── inputinteger.py          # Integer input
├── inputboolean.py          # Boolean input
├── inputchoice.py           # Choice input
├── output.py                # [DEPRECATED] Use echo.py instead
└── specs/                   # Specification files
```

> **Note:** `output.py` is deprecated. Use `echo.py` instead.
> **Note:** `input.py` is deprecated. Use `inputstring.py` instead.

## Module Specifications

### const.py

Terminal constants:

| Constant | Value | Description |
|----------|-------|-------------|
| `ESC` | `"\x1b"` | Escape character |
| `CSI` | `f"{ESC}["` | Control Sequence Introducer |
| `OSC` | `f"{ESC}]"` | Operating System Command |
| `BEL` | `"\007"` | Bell character |
| `ETX` | `'\x03'` | End of Text (Ctrl-C) |
| `EOF` | `'\x04'` | End of File (Ctrl-D) |
| `MAX_TERMINAL_WIDTH` | `None` | Maximum terminal width (None = auto) |
| `FALLBACK_TERMINAL_WIDTH` | `100` | Fallback width |
| `DEFAULT_PALETTE_NAME` | `"c64"` | Default color palette |
| `ECHO_END` | `"\n"` | Default line ending |

### terminal.py

Terminal size utilities:

| Function | Signature | Description |
|----------|-----------|-------------|
| `size` | `() -> os.terminal_size` | Get terminal size |
| `columns` | `() -> int` | Get terminal width |
| `width` | `() -> int` | Alias for columns |
| `lines` | `() -> int` | Get terminal height |
| `height` | `() -> int` | Alias for lines |

### common.py

Common I/O primitives:

**Classes:**
- `Token` - Dataclass for parsed tokens (kind, value, args, kwargs, text, repeat, raw)
- `TerminalState` - Dataclass for terminal state

**Functions:**

| Function | Signature | Description |
|----------|-----------|-------------|
| `set_output_stream` | `(stream)` | Set output stream |
| `set_input_stream` | `(stream)` | Set input stream |
| `write_current_output_stream` | `(s, flush=False)` | Write to output stream |
| `read_current_input_stream` | `(size=1) -> str` | Read from input stream |
| `get_cursor_position` | `() -> tuple[int, int]` | Get cursor position (row, col) |

### echo.py

Main echo function with rich formatting and runtime variables:

**Functions:**

| Function | Signature | Description |
|----------|-----------|-------------|
| `echo` | `(text, level='info', flush=False, end='\\n', wordwrap=True)` | Output formatted text |
| `echo_traceback` | `(msg='')` | Output traceback |
| `rendered_length` | `(text) -> int` | Calculate rendered length |
| `setvar` | `(name, value)` | Set runtime variable |
| `getvar` | `(name, default=None)` | Get runtime variable |
| `register_emoji` | `(name, value)` | Register custom emoji |
| `register_emojis` | `(emojis: dict)` | Register multiple emojis |

### echovars.py

Runtime variables for echo:

| Variable | Description |
|----------|-------------|
| `ECHOPREFIX` | Prefix for echo output |
| `ECHOENABLED` | Whether echo is enabled |
| `ECHOSTDERR` | Output to stderr |

**Echo Commands:**
The echo function supports these formatting commands:
- Color commands: `{red}`, `{green}`, `{blue}`, `{white}`, `{black}`, etc.
- Background colors: `{bgred}`, `{bggreen}`, etc.
- Style commands: `{bold}`, `{italic}`, `{underline}`, etc.
- Cursor commands: `{home}`, `{curpos:x,y}`, `{cup}`, `{cuu}`, `{cud}`, etc.
- Erase commands: `{erasedisplay}`, `{eraseline}`
- Bell: `{bell}`, `{bel}`
- RGB colors: `{rgb:r,g,b}`
- Reset: `{reset}`, `{/all}`
- Variables: `{var:<name>}` or `{<name>}`
- Emojis: `:name:`

### output.py

> **DEPRECATED:** This module was removed. Use `echo.py` instead.

Output stream handling:

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_current_output_stream` | `() -> file` | Get current output stream |
| `set_output_stream` | `(stream)` | Set output stream |

### palette.py

Color palettes:

| Function | Signature | Description |
|----------|-----------|-------------|
| `c64_palette` | `() -> dict` | Commodore 64 palette |
| `get_current_palette` | `() -> dict` | Get current palette |
| `get_palette_entry` | `(name) -> tuple` | Get palette entry |
| `rgb` | `(r, g, b) -> str` | Create RGB color string |

### getch.py

Character input (non-blocking):

| Function | Signature | Description |
|----------|-----------|-------------|
| `getch` | `() -> str` | Get single character |
| `getch_nonblocking` | `() -> Optional[str]` | Non-blocking getch |

### getstr.py

String input with editing:

| Function | Signature | Description |
|----------|-----------|-------------|
| `getstr` | `(prompt='', default='', history=None)` | Get string with editing |
| `getline` | `(prompt='')` | Simple line input |

### input.py

> **DEPRECATED:** Use `inputstring.py` instead. This module is not used.

General input handling:

| Function | Signature | Description |
|----------|-----------|-------------|
| `input` | `(prompt='')` | Basic input |
| `readline` | `() -> str` | Read line |

### inputstring.py

String input with validation:

| Function | Signature | Description |
|----------|-----------|-------------|
| `InputString` | `class` | String input with validation |

### inputinteger.py

Integer input:

| Function | Signature | Description |
|----------|-----------|-------------|
| `InputInteger` | `class` | Integer input with bounds |

### inputboolean.py

Boolean input:

| Function | Signature | Description |
|----------|-----------|-------------|
| `InputBoolean` | `class` | Yes/no input |

### inputchoice.py

Choice selection:

| Function | Signature | Description |
|----------|-----------|-------------|
| `InputChoice` | `class` | Multiple choice selection |

### keymap.py

Keyboard mapping:

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_key_name` | `(key_code) -> str` | Get key name |
| `parse_key` | `(s) -> int` | Parse key string |

## Usage Examples

### Basic Output

```python
from asimov import io

io.echo("Hello, World!")
io.echo("{red}This is red{/all}")
io.echo("{bold}Bold text{/all}")
io.echo("{bgblue}{white}Blue background{/all}")
```

### Input

```python
from asimov.io import getch, getstr

# Single character
c = getch()

# String input
name = getstr("Enter name: ")
```

### Terminal Size

```python
from asimov.io import terminal

width = terminal.columns()
height = terminal.lines()
print(f"Terminal is {width}x{height}")
```

### Color Palettes

```python
from asimov.io import palette

# Use C64 palette
palette.get_palette_entry("blue")

# RGB color
rgb = palette.rgb(255, 0, 0)
io.echo(f"{rgb}Red text")
```

### Cursor Movement

```python
io.echo("{home}")           # Move to home position
io.echo("{curpos:10,20}")   # Move to row 10, col 20
io.echo("{eraseline}")      # Clear current line
```
