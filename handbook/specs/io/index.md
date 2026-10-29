# bbsengine6.io specifications

`bbsengine6.io` is the terminal I/O package: line and key input, output with
inline formatting, palettes, and the terminal state they depend on. These specs
describe the modules as they are in `py/src/bbsengine6/io/`.

Specs in this folder were checked against the code. A spec that disagrees with the
code is a bug in the spec; say so in the commit that fixes it.

## Input

| Module | Spec | Status |
|---|---|---|
| `getch.py` | [getch.md](io_getch.md) | Live. Key reader, `getch_str` and `getch_utf8`. |
| `inputstring.py` | [inputstring.md](io_inputstring.md) | Live. Line editor. |
| `inputstring.py` (enhancements) | [inputstring_enhancements.md](io_inputstring_enhancements.md) | Live. Added behaviour, history and F-keys. |
| `inputboolean.py` | [inputboolean.md](io_inputboolean.md) | Live. Yes/no prompt. |
| `inputinteger.py` | [inputinteger.md](io_inputinteger.md) | Live. Integer prompt. |
| `inputchoice.py` | [inputchoice.md](io_inputchoice.md) | Live. Choice prompt. |
| `inputcompleter.py` | [inputcompleter.md](io_inputcompleter.md) | Live. Database-backed readline completer. **Has a known import defect; see its spec.** |
| `getstr.py` | [getstr.md](io_getstr.md) | Live. Plain string prompt. |

## Output

| Module | Spec | Status |
|---|---|---|
| `echo.py` | [echo.md](io_echo.md) | Live. Output with inline commands. |
| `echo.py` commands | [echo_commands.md](echo_commands.md) | Live. The command vocabulary. |
| `palette.py` | [palette.md](io_palette.md) | Live. Colour palettes. |
| `terminal.py` | [terminal.md](io_terminal.md) | Live. Terminal size and title. |

## Support

| Module | Spec | Status |
|---|---|---|
| `common.py` | [common.md](io_common.md) | Live. Streams, raw session, DSR and mouse-state queries. |
| `const.py` | [const.md](io_const.md) | Live. Terminal constants. |
| `keymap.py` | [keymap.md](io_keymap.md) | Live. Escape sequence to key name table. |
| `util.py` | [util.md](io_util.md) | Live. Logging helpers. |
| `events` (key event system) | [events.md](io_events.md) | Live. Key event bus and dispatcher, in `getch.py`. |
| `echovars.py` | [echovars.md](echovars.md) | **Deprecated.** Only used by deprecated `output.py`. Not documented further. |

## Deprecated modules

These modules say they are deprecated and are not used by live code. They are
marked here and left alone. They are not documented further, and removing them is a
separate change.

| Module | Replacement |
|---|---|
| `input.py` | `bbsengine6.io.inputstring` |
| `output.py` | `bbsengine6.io.echo` |
| `lib.py` | Used only by `output.py`. |
| `echovars.py` | Used only by `output.py`. |

## Outside the io package

| Spec | What it describes |
|---|---|
| [`../../../py/src/bbsengine6/io/specs/io_screen.spec`](../../../py/src/bbsengine6/io/specs/io_screen.spec) | `bbsengine6/screen.py`, a top-level module, not part of io. Left in place. Its title still says `asimov.io.screen`. |

## Design notes and records

| Record | What it covers |
|---|---|
| [BUGFIX_INPUTSTRING_KEY_ENTER.md](BUGFIX_INPUTSTRING_KEY_ENTER.md) | May 2026: `{curpos}` commands interfering with `getch` on Enter. |
| [BUGFIX_INPUTSTRING_KEY_ENTER_FINAL.md](BUGFIX_INPUTSTRING_KEY_ENTER_FINAL.md) | Final account of the Enter hang. |
| [BUGFIX_TERMINAL_STATE_LOCKING.md](BUGFIX_TERMINAL_STATE_LOCKING.md) | May 2026: `_terminal_state` race conditions. |
| [io_best_practices.md](io_best_practices.md) | Conventions for writing prompts and output in io. |

## Historical

[`../../../py/src/bbsengine6/io/SPEC.md`](../../../py/src/bbsengine6/io/SPEC.md) is
a pre-Phase-7 snapshot of the package layout. It is kept for reference. For the
current layout, use this index.
