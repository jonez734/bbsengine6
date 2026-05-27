# asimov.io.screen Specification

## Overview

`screen.py` provides screen-related utilities including scroll regions, bottom bars, and progress indicators.

## Dependencies

- `echo.py`: Terminal output
- `terminal.py`: Terminal size
- `const.py`: MAX_TERMINAL_WIDTH
- `util.py`: Logging

## Functions

### `init(args=None, topmargin=1, bottommargin=1)`

Initialize screen with scroll region.

- Sets cursor to top margin
- Configures scroll region from `topmargin` to `terminal_height - bottommargin`

---

### `updatebottombar(buf: str) -> None`

Render bottom bar on last terminal line without line wrapping.

---

### `setbottombar(left, right=None, **kwargs) -> bool`

Set bottom bar with left and right content.

**Parameters:**
- `left`: Left content (string or callable)
- `right`: Right content (string or callable)
- `**kwargs`: Passed to callable left/right

**Features:**
- Truncates left content with "..." if too long
- Calculates padding to fill terminal width

---

### `setarea(...)`

Alias for `setbottombar`.

---

### `popbottombar()` / `poparea()`

Pop and display previous bottom bar from stack.

---

### `updateprogress(iteration, total, fill="#")`

Display progress bar in bottom bar.

**Parameters:**
- `iteration`: Current iteration
- `total`: Total iterations
- `fill`: Fill character (default: "#")

---

### `get_notification_status(**kwargs) -> str`

Get notification status string for bottombar right side.

**Parameters:**
- `**kwargs`: Passed to `notify.count()` (supports `args`, `conn`, `pool`)

**Returns:**
- `"F2: notify (N)"` if notifications > 0, else empty string

## Known Issues

1. ~~Line 66 references `io.getterminalwidth()` which is undefined~~ (FIXED - now uses `terminal.width()`)
2. ~~`bottombarstack` global variable is used but never initialized~~ (FIXED - now initialized as empty list)
