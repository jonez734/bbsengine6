# asimov.io.getstr Specification

## Overview

`getstr.py` provides full line editing with insert/overwrite mode toggle.

## Dependencies

- `echo.py`: Terminal output (uses but doesn't import - see note)
- `getch.py`: Key input (uses but doesn't import - see note)

**Note:** This module uses `echo` and `getch` without explicit imports. They must be available in the caller's namespace.

## Public API

### Main Function

```python
def getstr(prompt: str = "") -> str
```

Reads a string from the user with full line editing.

**Parameters:**
- `prompt`: Prompt to display (default: "")

**Returns:**
- The entered string (without trailing newline)

## Features

### Editing Modes
- **Insert mode (INS)**: Characters are inserted at cursor
- **Overwrite mode (OVR)**: Characters replace existing characters

### Key Bindings

| Key | Action |
|-----|--------|
| Enter | Return input |
| Backspace | Delete character before cursor |
| Left | Move cursor left |
| Right | Move cursor right |
| Home | Jump to line start |
| End | Jump to line end |
| Insert | Toggle insert/overwrite mode |
| Other | Insert character |

## Notes

- Uses DECSC/DECRC to save/restore cursor position
- Displays "[INS]" or "[OVR]" indicator
- Requires `echo` and `getch` to be in scope (typically imported from `asimov.io`)
