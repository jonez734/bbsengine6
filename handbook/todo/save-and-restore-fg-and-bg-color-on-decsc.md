# save and restore foreground, background and attributes on {decsc}/{decrc}

Visible bug. `{savecursor}`/`{decsc}` and `{restorecursor}`/`{decrc}` save and restore the
cursor, but not the colour. After a restore the text is drawn in whatever colour was written last,
not the colour that was active when the cursor was saved.

The bottom bar saves and restores the cursor around every redraw, so a caller's colour can
change when the bar repaints. Casino's status line and bottom bar show this.

## What the code does

- `_handle_decsc` (`py/src/bbsengine6/io/echo.py`) saves the cursor row and column, `wordwrap`,
  `has_color` and `hidden`.
- `_handle_decrc` restores only those same fields.
- `TerminalState` (`py/src/bbsengine6/io/common.py`) has no foreground, background or attribute
  fields, so the colour and `{attr}` state (bold, underline, reverse and similar) are never saved.

## Open

- [x] Add foreground, background and attribute fields to `TerminalState`
- [x] Save them in `_handle_decsc` and restore them in `_handle_decrc`
- [x] Decide whether `{savecursor}` emits the saved state as SGR on restore, or only records it
  internally (the restore must leave the terminal in the saved colour either way)
- [x] Make the bottom-bar redraw restore the caller's colour after it paints
- [x] Tests: set a colour and attribute, save, change colour, restore, and the colour matches the
  save
- [x] Test: a bottom-bar redraw between a save and a restore leaves the caller's colour unchanged

## Done when

- [x] `{decrc}` restores the saved foreground, background and attributes
- [x] The bottom bar redraw does not change the caller's colour
- [x] The new tests pass in the full bbsengine6 suite, with no new failures against the baseline

## Resolution

- `TerminalState.sgr` (`io/common.py`) records the SGR colour and attributes as escape text is
  written. The parser and emitter are in `io/sgr_state.py`.
- `{decsc}` saves the SGR state; `{decrc}` restores it and re-emits it, so the next text is drawn
  in the saved colour. `{savecursor}`/`{restorecursor}` do the same.
- The bottom bar no longer ends its paint with `{/all}`, which reset the caller's colour after the
  restore. The restore now leaves the caller's colour in place.
- Decision recorded: the restore re-emits SGR (the terminal shows the saved colour), not only the
  software state.
