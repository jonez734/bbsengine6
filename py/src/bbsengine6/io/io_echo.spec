# asimov.io.echo Specification

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

### 4. Display Control

| Command | Description |
|---------|-------------|
| `{cls}` / `{erasedisplay}` | Clear screen |
| `{eraseline}` | Erase current line |
| `{bell}` / `{bel}` | Sound terminal bell |

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
| `{fullwidth}` | Enable double-width text |
| `{/fullwidth}` | Disable double-width text |

### 11. Window Title

```python
echo("{settitle:My Window}")  # Sets terminal window title
```

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

## Known Issues / TODOs

1. ~~Line 50 has a typo: `"{bgblue}{white]"` should be `"{bgblue}{white}"`~~ (FIXED)
2. ~~`_handle_ed()` has debug print statement~~ (FIXED - commented out)
3. ~~`_handle_literalopen()` has debug print~~ (FIXED - commented out)
4. ~~Dead code in `_handle_box()`~~ (FIXED - removed)
5. ~~`_decdhl` global variable referenced but never properly initialized~~ (FIXED - now uses `_terminal_state.decdhl`)
