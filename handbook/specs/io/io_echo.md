# bbsengine6.io.echo Specification

## Overview

`echo.py` is a terminal output module that provides enhanced text rendering with inline commands, colors, cursor control, and formatting. It processes text containing curly-brace commands (e.g., `{yellow}`, `{f6}`, `{curpos:10,5}`) and converts them to terminal control sequences.

## Core Architecture

### Token System

The module uses a **token-based pipeline**:

1. **Tokenization** (`tokenize()`): Parses input text into `Token` objects
2. **Handling** (`_handle_*` functions): Transform tokens into output strings
3. **Writing** (`_write_token()`): Writes processed output to stream

### Token Types

| Kind | Description |
|------|-------------|
| `WORD` | Regular text content |
| `WHITESPACE` | Spaces, tabs, newlines |
| `COMMAND` | Curly-brace commands like `{yellow}`, `{f6}` |
| `EMOJI` | Colon-wrapped emoji like `:smile:` |
| `F6` | Hard newline (`\n`) |
| `COLOR` | ANSI color sequence |
| `ATTR` | Text attributes (bold, italic, etc.) |
| `ACS` | Alternate Character Set (box-drawing) |
| `UNKNOWN` | Fallback for unrecognized input |

### Command Syntax

```
{command}
{command:arg1,arg2}
{command:key=value}
{/command}  (for closing attributes)
```

## Features

### 1. Color Palettes

- **ANSI palette**: Standard 8 colors + 8 light colors
- **C64 palette**: Commodore 64 color scheme (default)
- Background colors via `bg` prefix: `{bggray}`, `{bgwhite}`, etc.
- RGB colors: `{rgb:#RRGGBB}` or `{rgb:fg,255,0}`

### 2. Text Attributes

| Command | Effect |
|---------|--------|
| `{bold}` | Bold text |
| `{italic}` | Italic text |
| `{underline}` | Underlined text |
| `{strike}` | Strikethrough |
| `{inverse}` | Inverse video |
| `{/bold}` | Close attribute |

### 3. Cursor Control

| Command | Description |
|---------|-------------|
| `{curpos:y,x}` | Move cursor to row y, column x |
| `{cup:n}` | Move cursor up n rows |
| `{cud:n}` | Move cursor down n rows |
| `{cuf:n}` | Move cursor forward n columns |
| `{cub:n}` | Move cursor back n columns |
| `{home}` | Move cursor to home (1,1) |
| `{cha:n}` | Cursor horizontal absolute (column n) |
| `{savecursor}` / `{decsc}` | Save cursor position |
| `{restorecursor}` / `{decrc}` | Restore cursor position |

`{decsc}` asks the terminal for its position before it saves it (a DSR query,
with a one-second timeout; see `io_common.md`). Each save therefore waits for a
reply. `{decrc}` restores the saved position without a query. The bottom bar avoids
this cost by emitting the terminal's own ESC 7 / ESC 8 instead.

### 4. Display Control

| Command | Description |
|---------|-------------|
| `{erasedisplay}` / `{ed}` | Clear the display |
| `{cls}` | Runtime variable, not a command: expands to `{erasedisplay}{home}` |
| `{eraseline}` / `{elo}` | Erase the current line |
| `{bell}` / `{bel}` | Sound the terminal bell |

### 5. Scroll Regions

| Command | Description |
|---------|-------------|
| `{decstbm:top,bottom}` | Set scroll region |

### 6. ACS Characters (Box Drawing)

Box-drawing characters using DEC Alternate Character Set:

- `{ulcorner}`, `{urcorner}`, `{llcorner}`, `{lrcorner}`
- `{hline}`, `{vline}`
- `{ttee}`, `{btee}`, `{ltee}`, `{rtee}`, `{plus}`
- `{diamond}`, `{bullet}`, etc.

### 7. Runtime Variables

```python
setvar("myname", "{bold}John{/bold}")
echo("Hello {myname}")  # Expands to Hello John (bold)
```

Predefined variables in `_skin` dict for UI theming.

### 8. Emojis

Colon-wrapped emoji names: `:smile:`, `:fire:`, `:warning:`, etc. (100+ emojis defined)

### 9. Unicode Symbols

- `{arrow}`, `{arrow_left}`, `{arrow_up}`, `{arrow_down}`
- `{dblhline}`, `{dblvline}`, etc.

### 10. Fullwidth Text

| Command | Description |
|---------|-------------|
| `{fullwidth}` | Enable double-width text (alias of `{decdhl}`) |
| `{/fullwidth}` | Disable double-width text |

### 11. Window Title

`terminal.title(t)` sets the window title. **There is no `{settitle}` command:**
`echo("{settitle:My Window}")` writes the literal text `{settitle:My Window}` to the
terminal. Use `terminal.title()` to set the title.

## Public API

### Functions

```python
echo(text="", *, flush=True, end=ECHO_END, width=None, wordwrap=True, raw=False, palette=None, level=None)
```

Print text with command processing.

---

```python
echo_iter(text, width=None, wordwrap=True, palette=None, vars=None, raw=False)
```

Generator yielding tokens for rendering.

---

```python
echo_file(filepath, page_size=20, raw=False, wordwrap=True, end="")
```

Print file contents with paging.

---

```python
rendered_length(text, **kwargs) -> int
```

Calculate rendered text length (excluding control sequences).

---

```python
echo_traceback(message="Traceback (most recent call last):", level="error")
```

Print exception traceback with formatting.

---

```python
setvar(name, value)
setoption(opt, value)
getvar(name, default=None)
getoption(opt, default=None)
```

## Configuration

### Global State

- `_terminal_state`: Current cursor position, wordwrap, color state, ACS mode
- `_terminal_state_stack`: Stack for save/restore cursor
- `_terminal_state_stack_enabled`: If False (default), save/restore uses VT sequences (ESC 7/8) and behaves as single slot (peek, don't pop). If True, uses Python stack (pop on restore).
- `_runtime_vars`: User-defined variables
- `_current_palette`: Active color palette

### Options

- `wordwrap`: Enable/disable word wrapping
- `raw`: If True, treat commands as literal text

## Dependencies

- `common.py`: Token class, stream management, terminal state
- `palette.py`: Color definitions (ANSI, C64)
- `const.py`: Terminal constants (ESC, CSI, BEL, etc.)
- `terminal.py`: Terminal size detection

## Known defects

- `{settitle:...}` is documented in earlier versions of this spec. It is not
  implemented; the text is written as-is. `terminal.title()` is the working call.
- The `{decsc}` query described above makes each save slow when the terminal does not
  answer. The bottom bar was changed for this; `{decsc}` callers were not.

The earlier debug-print and dead-code items were fixed in the module and are no longer
open; they are removed from this list.
