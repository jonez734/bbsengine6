# asimov.io.palette Specification

## Overview

`palette.py` provides color palette management for terminal output. Supports ANSI and C64 (Commodore 64) color palettes.

## Dependencies

- `common.py`: Token class
- `const.py`: CSI, DEFAULT_PALETTE_NAME

## Palettes

### ANSI Palette

| Color Name | Code |
|------------|------|
| black | `\x1b[30m` |
| red | `\x1b[31m` |
| green | `\x1b[32m` |
| yellow | `\x1b[33m` |
| blue | `\x1b[34m` |
| magenta | `\x1b[35m` |
| cyan | `\x1b[36m` |
| white | `\x1b[37m` |
| lightblack | `\x1b[90m` |
| lightred | `\x1b[91m` |
| lightgreen | `\x1b[92m` |
| lightyellow | `\x1b[93m` |
| lightblue | `\x1b[94m` |
| lightmagenta | `\x1b[95m` |
| lightcyan | `\x1b[96m` |
| lightwhite | `\x1b[97m` |

### C64 Palette

Uses 24-bit RGB escape sequences. Includes background variants (e.g., `bgblack`, `bgwhite`).

## Functions

### `rgb(fgbg, triplet) -> str`

Returns ANSI SGR sequence for foreground (38) or background (48).

**Parameters:**
- `fgbg`: 38 for foreground, 48 for background
- `triplet`: RGB as `#RRGGBB` or `(r,g,b)`

---

### `darken(prefix, rgb, percentage) -> str`

Returns darkened version of a color.

**Parameters:**
- `prefix`: 38 or 48
- `rgb`: Color spec (`#RRGGBB` or `(r,g,b)`)
- `percentage`: Darkening factor 0.0-1.0

---

### `set_palette(palette_name)`

Sets the current palette globally.

**Parameters:**
- `palette_name`: "ansi" or "c64"

---

### `get_palette(name=DEFAULT_PALETTE_NAME)`

Returns a palette dictionary by name.

---

### `get_current_palette()`

Returns the current active palette.

---

### `get_palette_entry(name)`

Returns ANSI sequence for a color name from current palette.

---

### `make_bg(palette)`

Creates background color variants by replacing "38" with "48".

## Global State

- `_current_palette`: Active palette (initialized from DEFAULT_PALETTE_NAME)
