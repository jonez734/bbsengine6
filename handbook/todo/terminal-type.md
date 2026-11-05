# Terminal type for members

## Problem

A member's terminal type is not stored anywhere. The session sets `useragent` from the `TERM`
environment variable in two places (`py/src/bbsengine6/session/lib.py`, with defaults `NEEDINFO`
and `xterm`), and `subprocess_command.run_child` reads `TERM` directly to refuse `dumb` or empty
values. A full-screen program (for example the bsd-games `trek` and `hack`) can break confusingly
when `TERM` names an entry the server does not have, and a member with no `TERM` gets a refusal
with no way to fix it.

## Decisions

- **Override order.** `TERM` from the client wins when it passes the terminfo check. Otherwise the
  member's stored `terminaltype` is used. Otherwise `xterm`.
- **Unknown `TERM`.** A `TERM` with no terminfo entry falls back, with one notice that names the
  rejected value and the value used. It does not refuse.
- **`dumb` and empty.** These still refuse for full-screen programs, since none of them can run.
  The refusal message names the value in effect and how to set `TERM`.
- **Stored values.** The edit key in `console.member` accepts only values that pass the terminfo
  check. The sysop can override a member's value.
- **Every display shows its source**: `client`, `stored`, or `default`.

## Work

1. **Resolution helper.** `terminal.resolve(member)` returns `(value, source)`. Order: `TERM` if it
   passes terminfo, then the stored `terminaltype`, then `xterm`.
2. **Terminfo check.** Use `curses.setupterm` on a scratch fd or `infocmp`. Cache the result per
   value.
3. **Schema.** A migration adds `"terminaltype" text NOT NULL DEFAULT 'xterm'` to `engine.__member`
   (`py/src/bbsengine6/sql/member.sql` for the create statement, plus a new migration file so
   existing databases upgrade).
4. **Explicit child environment.** `subprocess_command.run_child` sets `TERM` in the child's `env`
   from the resolved value, instead of inheriting it.
5. **Sources shown.** The session `useragent`, the fallback and refusal notices, and the console
   member view show the value and its source.
6. **`console.member`.** Show `Terminal type` with its source in `render_member`. Add an edit key
   that accepts only values that pass the terminfo check, and a sysop override.
7. **Tests.**
   - terminfo check for a known and an unknown name;
   - resolution order, including a client `TERM` overriding the stored value;
   - the fallback notice text;
   - the explicit child environment;
   - the migration default is `xterm`;
   - the console view and edit, and the sysop override.

## Status

Implemented (2026-11-04), in the commits listed in `handbook/io/todo/terminfo.md`:
resolution (`io/terminal.resolve`), the child `TERM` (`subprocess_command.run_child`), the
session `useragent`, the `engine.__member.terminaltype` column and migration, and the console
`[Y]` view and edit. Not done: a sysop-only override distinct from the edit key, and telnet TTYPE.

---

## Telnet TTYPE negotiation

Out of scope for the work above. Telnet's TTYPE option carries the client's terminal type, which is
more reliable than a `TERM` variable. It only helps if the connection layer exposes the negotiated
value to the session. This needs a check of the transport before any design.

### Status

Open. Not started.
