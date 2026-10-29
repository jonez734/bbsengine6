# Command registry

`bbsengine6.commands` holds the names a shell or host program accepts, grouped by
tier. A shell (letteredolive) builds its command list with it, and a host program
(casino) builds its own list inside its own session. Both use the same rules for
matching, overriding and availability.

Status: the registry is implemented (`py/src/bbsengine6/commands.py`). Each interaction
holds its registry in an `Interaction` (`py/src/bbsengine6/interaction.py`); see below.

## Tiers

| Tier | Meaning | Removable | Overridable |
|---|---|---|---|
| `protected` | Always present. Added by the shell itself. | no | no, by name or alias |
| `default` | The shell's own command list. | yes | yes, by a session entry (extend mode only) |
| `session` | Added by a host for its session. | yes | yes, by another session entry |

`message` and `logout` are protected. `exit` is a default entry, so a host may replace
it (casino makes `exit` leave casino and return to the shell).

## Modes

A registry is created in one of two modes:

- **extend**: the shell's default list is loaded, and a session may override its entries.
- **replace**: the default list is never loaded. Only protected and session entries exist.
  Registering a default entry in this mode is an error (`CommandError`).

`use_default(entries)` loads a shell's default list. In replace mode it loads nothing.

## Registering

```python
registry.register(name, tier, spec=None, *, aliases=(), available=None) -> Entry
registry.unregister(name)
```

- `name` and `aliases` belong to one entry. Overriding a name replaces every alias of the
  old entry with the new entry's aliases, so nothing is left pointing at the old meaning.
- `spec` is whatever the caller uses to run the entry (for example `{"prg": "casino"}`);
  the registry does not interpret it.
- `available` is an optional predicate taking the session state. When it returns false
  the entry is hidden and takes no part in matching.
- An override is logged at debug level: `commands: session 'exit' overrides default 'exit'`.
- Unknown tier names raise `CommandError`.

## Matching

```python
kind, entry = registry.resolve(text, state)
```

`kind` is one of:

| Kind | Meaning | `entry` |
|---|---|---|
| `exact` | The text is an entry's name or alias, and the entry is available. | the entry |
| `unique` | Exactly one available entry has a name or alias starting with the text. | the entry |
| `ambiguous` | More than one available entry matches. Nothing runs. | `None` |
| `none` | No available entry matches (or the text is empty). | `None` |

Rules:

- An exact name or alias always wins over a prefix.
- An entry that is unavailable for the current state does not match at all. For example,
  with no seat, `h` does not resolve to `hit`, and `h` is not ambiguous either.
- `resolve` never returns the candidate list. Callers that need to show candidates call
  `candidates(prefix, state)`, which is for display only (tab completion and help).

## Visibility

`visible(state)` returns available entries sorted by name. Help and the menu use it.
Visibility is decided only by the availability predicate. The module's `access()` is not
called for visibility (see Launching).

## Launching

Commands are launched through `bbsengine6.module.run()` only. `run()` calls the module's
`access()` before `init`, `buildargs` and `main`, and stops with a message when the
check fails. The registry does not call `module.check()` directly.

## Subprocess commands

A full-screen program (for example `snake`, `robots`, `worm`) runs as a subprocess. It is
still a module command:

- The registry entry's `spec` names a small wrapper module. Its `main()` calls
  `bbsengine6.subprocess_command.run_child(argv)`, so the command is launched through
  `module.run()` and `access()` is checked.
- Subprocess entries are overridable like any default entry (a session may replace one by
  name, in extend mode).
- `run_child` first checks `TERM`. When it is unset, empty, or `dumb`, nothing starts and
  `SubprocessCommandError` is raised. The check is controlled per session by
  `subprocess_term_check` (default on).
- `run_child` leaves the shell's raw input session, runs the child with `subprocess.run`,
  and returns its exit status.
- Ctrl-C is a normal way out of a full-screen program (snake has no quit key). When the
  user presses it, `run_child` returns `INTERRUPTED_STATUS` (130, the shell convention for
  SIGINT) instead of raising `KeyboardInterrupt` into the caller. The screen is still
  redrawn.
- After the child exits, whatever happened, `redraw_all(bottom_buf)` restores the screen in
  this order: attribute and cursor reset, clear screen, scroll region and bottom bar, then
  the prompt line is marked dirty.
- The child clears the line the user was typing on. The text typed before the child is not
  kept by the launcher. The caller keeps it and passes it back to the next prompt as the
  positional `oldvalue` (`inputstring(prompt, typed)`), so the prompt redraws it and editing
  continues from it. (`oldvalue` is positional-only; the keyword form raises `TypeError`.)
  Known limit: a key typed in the short gap after the child exits and before the next prompt
  reads can be dropped (seen on a pty; not yet checked on a real terminal, and the cause is
  not confirmed). Callers should not depend on keys typed in that gap.

Status: `py/src/bbsengine6/subprocess_command.py` is implemented and tested
(`py/tests/test_subprocess_command.py`). No shipped wrapper module exists yet; letteredolive
and casino wire them in their own phases.

## Messages (planned, letteredolive)

These are the shell's messages for typed input, to be wired in the shell's dispatch:

- Unknown name: `command not found <name>` (one line, no list).
- Ambiguous prefix: `ambiguous command <prefix>` (one line, no list, nothing runs).

Candidates are shown only by tab completion (double Tab) and by the help key (F1).

## Interaction (per-context state)

`bbsengine6.interaction` holds the state one interaction keeps. It is named `interaction`
because `bbsengine6/session/` is already the login-session package.

- `current_session()` returns the interaction for the current context. Without a
  `use_session` call it is a module-level default, so existing code is unchanged.
- `new_session(mode, name)` makes a fresh interaction with an empty registry.
- `use_session(s)` makes `s` current inside a block, and restores the previous one on
  exit, including when the block raises. Blocks nest.
- Each thread, and each context, has its own current interaction. Registering a command
  in one interaction does not affect another.

Phase 3 moves the io state (input queue, terminal state, key table, and the rest) into the
same object. Until then an interaction holds only the registry.

## Known limits

- The registry is per object; a session is what holds one. Until the session container
  exists, a shell keeps one registry for the process.
- The predicate is evaluated on each `resolve`, `visible` and `candidates` call. Keep it
  cheap; it must not query a database on every keystroke.
