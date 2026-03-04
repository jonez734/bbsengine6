# asimov.io echo() Command Reference

## Overview

The `echo()` function supports various formatting commands enclosed in curly braces `{}`. This document lists all available commands.

## Basic Usage

```python
from asimov.io import echo
echo("{red}Hello {bold}World{/bold}!{/red}")
```

---

## Colors

### Foreground Colors

| Command | Description |
|---------|-------------|
| `{black}` | Black text |
| `{red}` | Red text |
| `{green}` | Green text |
| `{yellow}` | Yellow text |
| `{blue}` | Blue text |
| `{magenta}` | Magenta text |
| `{cyan}` | Cyan text |
| `{white}` | White text |
| `{lightblack}` | Bright black (gray) |
| `{lightred}` | Bright red |
| `{lightgreen}` | Bright green |
| `{lightyellow}` | Bright yellow |
| `{lightblue}` | Bright blue |
| `{lightmagenta}` | Bright magenta |
| `{lightcyan}` | Bright cyan |
| `{lightwhite}` | Bright white |

### Background Colors

| Command | Description |
|---------|-------------|
| `{bgblack}` | Black background |
| `{bgred}` | Red background |
| `{bggreen}` | Green background |
| `{bgyellow}` | Yellow background |
| `{bgblue}` | Blue background |
| `{bgmagenta}` | Magenta background |
| `{bgcyan}` | Cyan background |
| `{bgwhite}` | White background |
| `{bglightgray}` | Light gray background |
| `{bgdarkgray}` | Dark gray background |

### Color Reset

| Command | Description |
|---------|-------------|
| `{/fgcolor}` | Reset foreground color |
| `{/bgcolor}` | Reset background color |
| `{/all}` | Reset all attributes |

---

## Text Attributes

| Command | Description |
|---------|-------------|
| `{bold}` | Bold text |
| `{italic}` | Italic text |
| `{underline}` | Underlined text |
| `{strike}` | Strikethrough text |
| `{inverse}` | Inverse video |
| `{code}` | Inverse video (same as inverse) |

Closing syntax: `{/bold}`, `{/italic}`, etc.

---

## Cursor Movement

| Command | Description |
|---------|-------------|
| `{cursorup}` or `{cup}` | Move cursor up (default 1) |
| `{cursorup:n}` | Move cursor up n lines |
| `{cursordown}` or `{cud}` | Move cursor down (default 1) |
| `{cursordown:n}` | Move cursor down n lines |
| `{cursorright}` or `{cuf}` | Move cursor right (default 1) |
| `{cursorright:n}` | Move cursor right n columns |
| `{cursorleft}` or `{cub}` | Move cursor left (default 1) |
| `{cursorleft:n}` | Move cursor left n columns |
| `{curpos:y,x}` | Move cursor to row y, column x |
| `{home}` | Move cursor to home position (1,1) |
| `{savecursor}` or `{decsc}` | Save cursor position |
| `{restorecursor}` or `{decrc}` | Restore cursor position |

---

## Screen Clearing

| Command | Description |
|---------|-------------|
| `{erasedisplay}` or `{ed}` | Clear entire screen |
| `{erasedisplay:tobottom}` | Clear from cursor to bottom |
| `{erasedisplay:totop}` | Clear from cursor to top |
| `{eraseline}` or `{el}` | Clear current line |
| `{eraseline:toend}` | Clear from cursor to end of line |
| `{eraseline:tobeginning}` | Clear from beginning to cursor |
| `{eraseline:all}` | Clear entire line |

---

## Special Characters

| Command | Description |
|---------|-------------|
| `{bell}` or `{bel}` | Sound bell/flash screen |
| `{bell:n}` | Bell n times |
| `{f6}` | Print n newlines (paginate) |
| `{f6:n}` | Print n newlines |
| `{wait:n}` | Wait n units (for text animation) |
| `{settitle:text}` | Set terminal title |

---

## Alternate Character Set (Box Drawing)

| Command | Character | Description |
|---------|-----------|-------------|
| `{ulcorner}` | ┌ | Upper left corner |
| `{urcorner}` | ┐ | Upper right corner |
| `{llcorner}` | └ | Lower left corner |
| `{lrcorner}` | ┘ | Lower right corner |
| `{hline}` | ─ | Horizontal line |
| `{vline}` | │ | Vertical line |
| `{ttee}` | ┬ | T tee (top) |
| `{btee}` | ┴ | T tee (bottom) |
| `{ltee}` | ┤ | T tee (left) |
| `{rtee}` | ├ | T tee (right) |
| `{plus}` | ┼ | Plus/cross |
| `{diamond}` | ◆ | Diamond |
| `{bullet}` | • | Bullet |
| `{degree}` | ° | Degree symbol |
| `{pluminus}` | ± | Plus/minus |
| `{arrow}` | → | Arrow |

### Double-line Box Drawing

| Command | Character |
|---------|-----------|
| `{dblhline}` | ═ |
| `{dblvline}` | ║ |
| `{dblul}` | ╔ |
| `{dblur}` | ╗ |
| `{dblll}` | ╚ |
| `{dbllr}` | ╝ |

---

## Emoji

> **Note:** This table shows a sample of available emojis. The full list is defined in `echo.py`. Use tab-completion in your editor to discover all available emojis.

You can also register custom emojis at runtime:

```python
from asimov.io import register_emojis
register_emojis({"horse": "\\U0001F40E", "grain": "\\U0001F33E"})
echo(":horse: :grain:")
```

| Command | Emoji | Description |
|---------|-------|-------------|
| `{grin}` | 😀 | Grinning face | `\U0001f600` |
| `{smile}` | 🙂 | Smiling face | `\U0001f642` |
| `{rofl}` | 🤪 | Rolling on floor laughing | `\U0001f923` |
| `{wink}` | 😉 | Winking face | `\U0001f609` |
| `{thinking}` | 🤔 | Thinking face | `\U0001f914` |
| `{sunglasses}` | 😎 | Sunglasses face | `\U0001f60e` |
| `{thumbup}` | 👍 | Thumbs up | `\U0001f44d` |
| `{thumbdown}` | 👎 | Thumbs down | `\U0001f44e` |
| `{fire}` | 🔥 | Fire | `\U0001f525` |
| `{sun}` | ☀ | Sun | `\U00026000` |
| `{moon}` | 🌙 | Moon | `\U0001f319` |
| `{star}` | ⭐ | Star | `\U0001f31f` |
| `{heart}` | ❤️ | Red heart | `\U00002764` |
| `{check}` | ✅ | Check mark | `\U00002705` |
| `{x}` | ❌ | X mark | `\U0000274e` |

---

## Variables

You can define custom variables for reuse:

```python
from asimov.io.echo import setvar, getvar
setvar("title", "{bold}{blue}My Title{/all}")
echo("{title}")
```

Built-in variables:
- `{cls}` - Clear screen and go home
- `{home}` - Move to home position
- `{level.debug}` - Debug log prefix color
- `{level.warning}` - Warning log prefix color
- `{level.error}` - Error log prefix color
- `{level.ok}` - Success/OK log prefix color
- `{level.info}` - Info log prefix color

---

## Log Level Prefixes

Use with `echo(..., level="debug")` etc:

```python
echo("message", level="debug")   # Uses {level.debug} prefix
echo("message", level="warning") # Uses {level.warning} prefix
echo("message", level="error")   # Uses {level.error} prefix
echo("message", level="ok")      # Uses {level.ok} prefix
echo("message", level="info")    # Uses {level.info} prefix
```

---

## RGB Colors

| Command | Description |
|---------|-------------|
| `{rgb:#RRGGBB}` | Foreground RGB color |
| `{bg_rgb:#RRGGBB}` | Background RGB color |

Example: `{rgb:#FF0000}` = bright red foreground

---

## Literal Braces

| Command | Description |
|---------|-------------|
| `{{` | Literal open brace `{` |
| `}}` | Literal close brace `}` |

Use these when you need to output a literal brace character without triggering command parsing.

Example:
```python
echo("Use {{ and }} for literal braces")
# Output: Use { and } for literal braces
```

---

## Notes

- Commands are case-insensitive
- All commands can be nested (colors + attributes)
- Use `{/all}` to reset all formatting when done
