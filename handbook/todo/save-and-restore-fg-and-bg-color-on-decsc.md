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

- [ ] Add foreground, background and attribute fields to `TerminalState`
- [ ] Save them in `_handle_decsc` and restore them in `_handle_decrc`
- [ ] Decide whether `{savecursor}` emits the saved state as SGR on restore, or only records it
  internally (the restore must leave the terminal in the saved colour either way)
- [ ] Make the bottom-bar redraw restore the caller's colour after it paints
- [ ] Tests: set a colour and attribute, save, change colour, restore, and the colour matches the
  save
- [ ] Test: a bottom-bar redraw between a save and a restore leaves the caller's colour unchanged

## Done when

- [ ] `{decrc}` restores the saved foreground, background and attributes
- [ ] The bottom bar redraw does not change the caller's colour
- [ ] The new tests pass in the full bbsengine6 suite, with no new failures against the baseline
