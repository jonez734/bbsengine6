# bbsengine6.io.getstr Specification

> **DEPRECATED. Unused.** Use `bbsengine6.io.inputstring()` instead. `getstr` is not
> exported from `bbsengine6.io`, nothing in the workspace imports it, and importing
> `bbsengine6.io.getstr` emits a `DeprecationWarning`. It is kept for history and is not
> being extended.

## Overview

`getstr.py` reads a line with cursor movement, backspace, and an insert/overwrite
toggle. It is a simpler line reader than `inputstring()`, which replaced it.

**Status:**
- Not exported from `bbsengine6.io` (`__init__.py` does not import it).
- No bbsengine6 code, test, or consuming project (`casino`, `empyre`, `bed`, `zoid6`,
  `teos`, `mistermcfeely`, `murdermotel`, `backuptools`, `getdate_next`,
  `letteredolive`) imports it.
- The only callers are in `asimov`, which has its own `io` package and does not use
  `bbsengine6.io.getstr`.

This spec documents the module as it is, including a defect in the insert toggle.

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
`KEY_INSERT` for the Insert key (`ESC [ 2 ~`, mapped in `keymap.py`), not `KEY_IC`, so
the branch is never taken. Pressing Insert then inserts the text `KEY_INSERT` into the
buffer.

Reproduced on a pseudo-terminal: typing `ab`, Insert, `c`, then Enter returns
`abKEY_INSERTc`. The fix is to test for `KEY_INSERT`. It is recorded here and not made
in this pass, since the module is unused.

## Indicator

The `[INS]` / `[OVR]` indicator is drawn on the input line by `draw_line()`. It is not
a bottom-bar fragment. The helper `update_bottombar()` is called but does nothing: its
only statement is a commented-out `setbottombar(...)`, so the bottom bar is never
painted. (`inputstring()`, by contrast, paints the bar; see `bottombar.md`.)

## Other behavior

- The `KEY_DC` (delete) branch is commented out, so the Delete key does nothing.
- `getstr` writes the cursor position with `{decsc}`, which asks the terminal for its
  position and waits for a reply (see `io_common.md` for the query and its timeout).

## Notes

- Replace callers with `inputstring()`. Do not extend this module.
- Removing the module is a separate decision; this spec documents it while it exists.
