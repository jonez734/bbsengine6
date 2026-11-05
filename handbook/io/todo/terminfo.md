# Pure-Python terminfo reader and member terminal type

Status: in progress (2026-11-04).

## Goal

Read the terminfo database from pure Python, with no `curses` and no `infocmp` at runtime.
Use it to decide whether a `TERM` value can drive a full-screen program, and to look up
capabilities for the screen code. Then wire it into the member terminal-type work in
`handbook/todo/terminal-type.md`.

## Decisions (from the owner)

1. Pure-Python parsing of compiled terminfo files.
2. Full capability lookup: booleans, numbers, strings, and extended capabilities.
3. Include the terminal-type work (resolution, child env, schema, console view).
4. Commit in the inner `bbsengine6/` repo only. No push. No meta-repo pointer bump, since
   `bbsengine6/` is not a submodule (AGENTS.md).

## Part A: `py/src/bbsengine6/io/terminfo.py`

### Lookup

Search order:

1. `$TERMINFO` (one directory).
2. `$TERMINFO_DIRS` (colon-separated). An empty entry means the system default list.
3. `~/.terminfo`.
4. `/etc/terminfo`, `/lib/terminfo`, `/usr/share/terminfo`, `/usr/lib/terminfo`.

In each directory, check `<c>/<name>` (the Linux layout) and `<hex(c)>/<name>` (the macOS
layout). The first existing regular file wins.

Names are validated before any path is built. An empty name, a name containing `/` or NUL,
or a name starting with `.` returns `None`. This prevents path traversal from `TERM`.

### Binary format

All integers are little-endian. Header is six 16-bit fields:

| Field | Meaning |
|-------|---------|
| magic | `0o432` (legacy, 16-bit numbers) or `0o1036` (extended, 32-bit numbers) |
| name_size | bytes of names section |
| bool_count | number of booleans |
| num_count | number of numbers |
| str_count | number of strings |
| str_size | bytes of string table |

Layout after the header:

1. Names (`name_size` bytes).
2. Booleans (`bool_count` bytes, one per capability).
3. Pad byte if the offset is odd, so numbers start on an even offset.
4. Numbers (`num_count` items, 2 or 4 bytes each). `0xFFFF` / `-1` means absent. `0xFFFE` / `-2` means cancelled.
5. String offsets (`str_count` items, 2 bytes each). `-1` absent, `-2` cancelled. Otherwise an offset into the string table.
6. String table (`str_size` bytes, each value NUL-terminated).

Extended section, present when the standard section ends on an even offset after any pad:

1. Five-field extended header: ext booleans, ext numbers, ext strings, ext string-table size,
   and the total offset count.
2. Extended booleans, pad, extended numbers, value offsets (ext strings), and name offsets for
   every extended capability (booleans, then numbers, then strings).
3. Extended string table.

The extended section is checked against files that `tic` generates in the tests. Where `tic`
is missing, those tests skip.

### Capability names

The names tables (`BOOL_CAPS`, `NUM_CAPS`, `STR_CAPS`) are generated from
`terminfo(5)` (`/usr/share/man/man5/terminfo.5.gz`). Each row gives the variable name, the
capname, and the termcap code, in index order. Index order matters because the binary file is
indexed by position.

Counts from this machine's man page: 37 booleans, 33 numbers, 394 strings. These are not the
44/39/414 numbers from memory earlier in the planning, so the tests do not hard-code them.
They compare the parsed result with `infocmp -1x` output for a sample of installed entries.

### API

| Function | Behavior |
|----------|----------|
| `find(name) -> Path or None` | First matching file, or `None`. |
| `load(name) -> Terminfo` | Parses the file. Raises `TerminfoError` if missing or corrupt. |
| `has_entry(name) -> bool` | `True` if `find` returns a path and `load` succeeds. Cached per name. |
| `clear_cache()` | Empties the cache (tests). |

`Terminfo` has:

- `name` (the requested name) and `path`.
- `bools`, `nums`, `strs` dicts keyed by capname (short name, for example `cols`, `cup`, `setaf`).
  Standard and extended capabilities are in the same dicts.
- `get(cap)` returns the value, or `None` if absent or cancelled. Strings are decoded as
  latin-1, so escape bytes survive. Padding markers such as `$<5>` are kept as written.

Keys in each dict use the capname, not the variable name.

### Errors

`TerminfoError` is raised for a bad magic number, a truncated file, an offset outside the
table, a non-NUL-terminated string, or a file that is not regular.

## Part B: terminal resolution (`io/terminal.py`)

`terminal.resolve(member) -> (value, source)`:

1. Client `TERM` from the environment, if `has_entry(TERM)` is true. Source `client`.
2. Otherwise the member's stored `terminaltype`, if set and `has_entry` is true. Source `stored`.
3. Otherwise `xterm`. Source `default`.

If the client `TERM` is set but has no terminfo entry, it is rejected with a notice that names
the rejected value and the value used. Empty, unset, and `dumb` are not rejected here; they
still refuse full-screen programs (Part C).

## Part C: integration

1. **Schema.** Add `"terminaltype" text NOT NULL DEFAULT 'xterm'` to `engine.__member` in
   `py/src/bbsengine6/sql/member.sql`. Add a migration file so existing databases upgrade. The
   migration default is `xterm`.
2. **Child environment.** `subprocess_command.run_child` takes the resolved value and sets
   `TERM` in the child `env`, instead of inheriting it. The existing `dumb`/empty refusal stays.
   The refusal message names the value in effect and how to set `TERM`.
3. **Session.** `session/lib.py` (the two `os.environ.get("TERM", ...)` sites) uses the resolved
   value.
4. **Console.** `console/member.py` `render_member` shows `Terminal type` with its source. The
   edit key accepts only values that pass `has_entry`. A sysop may override a member's value.
5. **Notices.** The fallback and refusal notices show the value and its source.

## Part D: tests (`py/tests/`)

- `test_terminfo.py`
  - `xterm` loads; sampled capabilities match `infocmp -1x` output.
  - An unknown name returns `None` from `find` and `False` from `has_entry`.
  - Names with `/`, NUL, or a leading `.` are rejected.
  - A hand-built legacy file parses under a temporary `TERMINFO`.
  - A file that `tic` compiles with extended capabilities parses, and its extended values match
    `infocmp -x`.
  - `TERMINFO_DIRS` with an empty entry falls back to the system list.
  - A corrupt magic number raises `TerminfoError`.
  - The cache returns the same object on a second call.
  - Where `curses` is available, a few capabilities match `curses.tigetstr`.
- `test_terminal_resolve.py`
  - Order: client, then stored, then `xterm`.
  - A client `TERM` overrides the stored value.
  - The fallback notice names the rejected and used values.
- Child environment: `run_child` passes the resolved `TERM` in `env`.
- Migration: the column default is `xterm`.
- Console: the view shows the source, the edit accepts only valid values, and the sysop override works.

## Part E: docs

- `handbook/todo/terminal-type.md`: status updated to reflect this work.
- `handbook/specs/io/`: a `terminfo` spec describing the API above.

## Commits (inner repo, no push)

1. `docs(io): plan for the pure-python terminfo reader`
2. `feat(io): pure-python terminfo reader` (module and tests)
3. `feat(io): resolve the terminal type from TERM, the member, and xterm`
4. `feat(subprocess): pass the resolved TERM to the child environment`
5. `feat(member): terminal type schema, migration, and console view`
6. `docs(io): terminfo spec and terminal-type status`

## Status

- Plan written.
- Part A: not started.
