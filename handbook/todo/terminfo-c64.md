# Terminfo/termcap entry for the Commodore 64

## Problem

No terminfo entry exists for a Commodore 64 terminal. Checked on the development host
(2026-11-11): `c64`, `c128`, `commodore`, `petscii`, `cbm`, `vic20`, and `c64-40col` are all
missing from `/usr/share/terminfo`, and no installed entry name matches them.

Without an entry, `terminal.report()` cannot give the C64 the 16-colour level. Its `color` is
`None`, because the level comes from terminfo's `colors` count and the palette table in
`io/palette.py` is not a terminal type. A C64 terminal also cannot be recognised by `TERM` for
the `resolve()` fallback, so it is treated as an unknown type.

## Facts that shape the work

- The C64 palette (`io/palette.py`, `c64_palette`) is a colour table. It names 38 entries: the 16
  classic colours, their background variants, and a few extras. Terminfo does not describe it.
- The level ladder in `report()` is driven by terminfo's `colors` number: 16 gives `"16"`. An
  entry with `colors#16` therefore gives a C64-class terminal the `"16"` level with no code change.
- A C64 is a PETSCII terminal. Its control codes are not ANSI, so an ANSI-only entry would
  misdraw the screen. The entry must describe the terminal the member actually uses, which depends
  on the emulator (for example a PETSCII-to-ANSI gateway, or a native C64 terminal program).
- Terminfo has no standard way to say "PETSCII". Any entry is a convention, and the name chosen
  must not collide with a real entry.

## Decisions to make first

1. **Which terminal.** The `TERM` name and the actual emulator. Until this is known, the entry
   cannot be written correctly. Candidates: a PETSCII gateway that speaks ANSI (then an entry
   based on `vt100` or `ansi` with `colors#16` is enough), or a native C64 that needs its own
   control sequences.
2. **Name.** A new name, such as `c64-ansi` or `petscii`, rather than reusing `c64`, which some
   older systems may use for something else.
3. **Where it is installed.** The owner's `~/.terminfo` for a test, or `/usr/share/terminfo` for
   the host. The deploy host needs it too, since `terminal.report()` runs on the server for bed
   members.

## Work

1. **Write the entry source** (`terminfo` source format), in the bbsengine6 repo under
   `py/src/bbsengine6/io/data/terminfo/`. Set `colors#16`, `pairs#256` only if the terminal really
   accepts it, and the cursor and clear capabilities the screen code uses (`cup`, `clear`, `el`,
   `sgr0`, `setaf`/`setab` for the 16 colours).
2. **Compile it** with `tic -o <dir> <file>`, and install the compiled file where the lookup
   finds it (see `handbook/io/todo/terminfo.md` for the search order: `$TERMINFO`, `~/.terminfo`, the
   system directories). Do not rely on a system install alone, since a deploy host may not have it.
3. **Check the level.** A `TERM` set to the new name gives `report()["color"] == "16"`, and a
   test pins it (`py/tests/test_terminal_report.py`, using the compiled entry).
4. **Check the palette.** The 16 colours the entry names match `c64_palette`'s first 16 entries,
   in the same order, so `{rgb:}` and the `colors` index agree.
5. **Document the name** in `handbook/specs/io/io_terminal.md` next to the 16-colour level.
6. **Do not add** a `c64` entry to the blocklist or the DECRQM list. The C64 terminal's DA1 reply
   is not known yet; check it first (see the DECRQM gate in `io_common.md`).

## Verification

- `infocmp -A <dir> <name>` shows the entry, with `colors#16`.
- `report()` on that `TERM` gives `color == "16"` and `source == "unknown"` (no truecolor claim).
- On the real C64 terminal, the prompt, the box drawing, and the colour names render. This needs
  a person at the terminal; no automated test can show it.

## Out of scope

- A PETSCII character set or graphics mode in the engine. This note is only about the terminfo
  entry and the 16-colour level.
- Changing the palette table, which is already correct for the 16 classic colours.
