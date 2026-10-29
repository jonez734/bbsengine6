# bbsengine6.io.getstr Specification

> **DEPRECATED.** Use `bbsengine6.io.inputstring()` instead. `getstr` is not exported from
> `bbsengine6.io`, nothing in bbsengine6 calls it, and importing `bbsengine6.io.getstr`
> emits a `DeprecationWarning`. It is documented here as it is and is not being extended.

## Overview

`getstr.py` reads a line with cursor movement, backspace, and an insert/overwrite
toggle. It is a simpler line reader than `inputstring()`.

**Status:** the module is not exported from `bbsengine6.io` (`__init__.py` does not
import it), and nothing in the repository's code or tests imports it. Callers should
use `inputstring()`. This spec documents the module as it is, including a defect in
the insert toggle.

## Dependencies

- `echo.py`: output, and `{decsc}` / `{decrc}` for saving and restoring the cursor
- `getch.py`: key input (`getch_str`)

Both are imported explicitly at the top of the module.

## Public API

```python
def getstr(prompt: str = "") -> str
```

Reads a string from the user.

**Parameters:**
- `prompt`: text printed before the input (default: `""`)

**Returns:**
- The entered text, without the line end

## Key bindings

| Key | Action |
|-----|--------|
| Enter (`\r`, `\n`, `KEY_ENTER`) | Return the text |
| Backspace (`KEY_BACKSPACE`) | Delete the character before the cursor |
| Left / Right | Move the cursor |
| Home / End | Move to the start or end of the text |
| Any other key | Insert it (insert mode), or replace the character under the cursor (overwrite mode) |

## Known defect: the insert toggle never runs

The module tests for `KEY_IC` to toggle insert and overwrite. `getch` produces
`KEY_INSERT` for the Insert key (`ESC [ 2 ~`), not `KEY_IC`, so the branch is never
taken. Pressing Insert then inserts the text `KEY_INSERT` into the buffer.

Reproduced with `getstr`: typing `ab`, Insert, `c`, then Enter returns
`abKEY_INSERTc`. The fix is to test for `KEY_INSERT`. It is recorded here and not
made in this pass.

## Other differences from the earlier spec

- The earlier spec said the module relied on `echo` and `getch` being in the caller's
  namespace. It imports both itself.
- The indicator (`[INS]` / `[OVR]`) is drawn on the input line. It is not the
  bottom-bar fragment that `inputstring()` uses. The bottom-bar call is commented
  out in the module.
- The `KEY_DC` (delete) branch is commented out, so the Delete key does nothing.

## Notes

- `getstr` writes the cursor position with `{decsc}`. That asks the terminal for its
  position and waits for a reply. See `io_common.md` for the query and its timeout.
