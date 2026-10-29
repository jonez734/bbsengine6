# TODO: inputstring / getch rework

Goal: fix paste and mouse-selection problems in `inputstring()` in VTE (gnome-terminal) and xterm,
fix input-path bugs found in review, and add `getch_utf8()` alongside
`getch_str()` (both kept, sharing code).

Status key: `[x]` done in the tree and exercised in a pty or the test suite;
`[ ]` not done. Items marked "not done" were planned but not implemented.

## Decisions

- [x] `getch_str()` and `getch_utf8()` both remain available; neither is removed.
- [x] Shared logic (escape resolution, `_proc_char`, `_getch_core`) lives in common helpers.
- [x] Runtime selection: `set_getch_impl("str" | "utf8")` sets the default; per-call `impl=` overrides. Default stays `"str"`.
- [x] `source_func` is `"getch_str"` for the existing reader and `"getch_utf8"` for the new one.
- [x] `noneok` defaults to `True`. `noneok=False` reprompts on empty Enter. No caller edits required.
- [x] `filter` split: `allowed=` (per-character set) and `filter=` (regex, checked on Enter).
- [x] Mouse state: save on entry, restore on return/exception/Ctrl+C. DECRQM reply restores previous state; no reply restores "off".
- [ ] Module flag to disable mouse handling is present (`MOUSE_STATE_MANAGED`); no user-facing setting.
- [x] Cutover of the default to `"utf8"` is NOT part of this change.

## Phase 1: shared core (`py/src/bbsengine6/io/getch.py`)

- [x] Escape-sequence resolution shared by both readers (`resolve_escape_sequence`, `_escape_end`, `_read_escape_tail`, `_resolve_queued_escape`).
- [x] Shared wait/tty/notification core (`_getch_core`) used by `getch_str` and `getch_utf8`.
- [ ] Control-byte handling and event firing fully shared. (Partly: `_proc_char` is shared; control-byte filtering is not implemented.)

## Phase 2: readers

- [x] `getch_utf8()`: decodes characters from the stream; drains all available input before waiting. (Uses the text stream, not `os.read`/EAGAIN.)
- [x] `getch_utf8()`: ESC sequences resolved; split sequences are joined; a lone ESC followed by a key yields `KEY_ESC`.
- [x] `getch_utf8()`: bracketed paste `ESC[200~` ... `ESC[201~` emits one `PASTE:` key (commit `7bf0c29`). Implemented in the shared reader, so `getch_utf8()` and `getch_str()` both get it.
- [x] `getch_str()`: signature and return values unchanged.
- [x] Pre-wait drain of pending input before raw mode; Enter (`\n` from cooked mode) restored to `\r` in `drain_stream_to_queue`.
- [x] `get_dsr` and the mouse query keep typed keys (non-reply bytes are requeued).
- [ ] Unmapped control bytes dropped (both readers). (Not implemented.)
- [ ] Unknown CSI sequences consumed through final byte and dropped. (Partly: CSI sequences are consumed through their final byte; unknown ones are returned as raw text.)
- [x] Map `\x17` to `KEY_CTRL_W` and `\x19` to `KEY_YANK` in the reader (commit `89f8d4d`).

## Phase 3: selection and exports

- [x] `set_getch_impl()`, `get_getch_impl()`, and per-call `impl=` keyword.
- [x] Export `getch_utf8`, `set_getch_impl`, `get_getch_impl` from `io/__init__.py` (commit `f7c7356`).

## Phase 4: `inputstring()` (`py/src/bbsengine6/io/inputstring.py`)

- [x] Per-call keys restored on exit (commit `3f2e3c1`). Table is still one shared dict; concurrent prompts in threads are not supported.
- [ ] Working INSERT toggle, `[OVR]` indicator, real overwrite. (Not done.)
- [x] `PASTE` inserts as one operation: a bracketed paste arrives as one `PASTE:` key and is inserted through the paste-batch rules (commit `7bf0c29`).
- [x] Typed overflow beeps; a paste cut at `max_len` beeps once (commit `8d4ee1a`).
- [ ] Ctrl+W and Ctrl+Y wired through the per-call table. (Not done.)
- [x] `noneok` default `True` (`inputstring`, `io_inputstring.spec`).
- [x] `handbook/specs/io/io_inputstring.md` updated to the code (commit `4cb50db`).
- [x] `noneok=False`: empty Enter beeps and reprompts.
- [x] `allowed=` per-character set, on typing and paste; disallowed characters beep and are dropped.
- [x] `filter=` regex checked on Enter (whole buffer); a non-match beeps and reprompts.
- [x] `inputinteger` passes `allowed=` and `filter=`.
- [ ] Asimov wrapper (`asimov/src/asimov/io/inputstring.py`, `inputinteger.py`) updated to match. Not done: separate submodule, left unchanged on purpose. Its `noneok` default is still `False`.
- [ ] Update `py/tests/test_inputstring_filter_kwarg.py`. (Not done; the test now reads the body function for pops, which is the only change.)
- [x] `inputstring()` wraps `_inputstring_body()` with a raw session and mouse push/pop.
- [x] Dirty-redraw no longer runs under the non-reentrant `_current_stream_lock` (fixes a self-deadlock).

## Phase 5: mouse state

- [x] Query DECRQM (`ESC[?1000$p`, 1002, 1003, 1006) before editing.
- [x] Parse `ESC[?<mode>;<1|2|3|4>$y` replies.
- [x] Disable mouse tracking on entry; restore saved state on return, exception, and Ctrl+C.
- [x] No reply: restore to "off".
- [x] Module flag `MOUSE_STATE_MANAGED` to disable the feature.

## Phase 6: tests (`py/tests/`)

- [ ] Parity test: `getch_str()` and `getch_utf8()` return identical key names for the same input. (Not written.)
- [ ] Shared key table: ASCII, multi-byte UTF-8, ESC sequences, bracketed paste, control bytes. (Partly: ESC sequences and UTF-8 covered by probes only.)
- [ ] Runtime default and per-call `impl=` override. (Not written.)
- [ ] Pty tests: burst paste, bracketed paste, ESC followed by text, control bytes. (Burst and ESC covered by probes, not by tests in the tree.)
- [x] Pty tests: `\x17`/`\x19`, typed and paste overflow beep, bracketed paste, key restore (`test_inputstring_editing.py`). INSERT toggle not tested.
- [x] Pty tests: `noneok=False` reprompt, `allowed=`, `filter=`, `inputinteger` (`test_inputstring_validation.py`, 10 tests).
- [x] Pty tests: mouse state restored on normal return, exception, and fallback (`test_inputstring_mouse_state.py`, 4 tests). Ctrl+C path not tested.
- [x] `test_inputstring_*`, `test_getch_*`, and `test_echo_*` green (69 tests).
- [x] Full `py/tests` run: no new failures against baseline. Remaining failures are Postgres-dependent and cannot run in the sandbox.

## Phase 7: verification and git

- [x] Manual check of arrow keys in local gnome-terminal (VTE): KEY_LEFT and KEY_RIGHT without leaks (reported by user).
- [ ] Manual check in local gnome-terminal (VTE): click-drag selection and middle-click paste. (Not confirmed.)
- [ ] Manual check in xterm: no regressions. (Not confirmed.)
- [x] Commit `bbsengine6/` changes, including `py/src/bbsengine6/_version.py`: commit `20d0d30` on `main`. Not pushed.
- [ ] Pointer bump: not applicable. `bbsengine6` is tracked as regular files in the meta-repo and is not in `.gitmodules`, so `scripts/bump-submodule-pointers.sh` has no gitlink to update (AGENTS.md). Meta-repo `bbsengine6/` changes are left uncommitted by design. User pushes.

## Phase 9: documentation

- [x] `handbook/specs/io/io_getch.md` updated: two readers, `impl=` and selector, raw session, escape tail, input queue, fix history (commit `e25a747`).
- [x] `handbook/specs/io/io_inputstring.md` updated: real signature and parameters, key table, tab rules, paste batching, mouse state, key-mapping restore, known issues (commit `4cb50db`).
- [x] Plan items not built are listed as known issues in the spec rather than described as done.

## Phase 8: tab completion (added after the initial plan)

- [x] A typed Tab completes an unambiguous prefix in the first word.
- [x] Completer receives the word under the cursor (io_inputstring.spec contract), so the second word completes.
- [x] Tab, Tab on an empty word lists every completion; the buffer is unchanged.
- [x] A Tab updates completion state and does not fall into the insert branch (which cleared it).
- [x] A paste batch never takes a trailing Tab (that Tab is completion); Backspace stops the batch so the key path deletes.
- [x] Shared key registry: `remove_key_mapping` restores the handler an override replaced (editor no longer erases defaults).
- [x] `insert_tabs=True` keeps pasted tabs as tab characters for a future editor.
- [x] `tests/tab_complete_check.py` (12 cases; `--interactive` for a manual prompt) and `test_inputstring_tab_complete.py`.
- [ ] Verified in local gnome-terminal (user).

## Phase 10: input rules (noneok, filter, allowed)

- [x] `noneok` controls empty Enter; default accepts, `noneok=False` reprompts.
- [x] `allowed` drops disallowed characters on typing and paste (beep, once per paste).
- [x] `filter` is a whole-buffer regex checked on Enter; not applied per keystroke.
- [x] `inputinteger` passes `allowed` and its regex; letters are dropped, invalid values reprompt.
- [x] Enter at the head of a paste batch is a command: it waits for the key path, so these rules apply to it.
- [x] Key handlers run outside `_key_actions_lock` (handlers write to the terminal).
- [ ] Asimov's separate `inputstring`/`inputinteger` copy: not changed (other submodule).
- [ ] `inputinteger` list entry (`1 2`): the regex still validates a single value. Not changed.

## Phase 11: editing keys, overflow, bracketed paste

- [x] Ctrl-W / Ctrl-Y reach the key table (`89f8d4d`). Verified in gnome-terminal (user).
- [x] Typed overflow beeps; overflow in a paste beeps once (`8d4ee1a`).
- [x] Bracketed paste: `ESC[?2004h` for the prompt; body returned as one `PASTE:` key; newline ends the entry (`7bf0c29`).
- [x] Per-call key handlers are restored on exit (`3f2e3c1`).
- [ ] INSERT toggle and `[OVR]` overwrite: not verified by a test.
- [ ] Asimov copy: unchanged (other submodule).
- [ ] Concurrent prompts in different threads: not supported; the key table and the terminal are shared.

## Phase 12: long paste display

- [x] A paste scrolls the window so the cursor stays visible (`94641ec`).
- [x] Text window fits the row after the prompt and INS/OVR indicator (`8f71dd6`).
- [x] `max_width` defaults to `terminal.columns()` instead of 80 (`8f71dd6`).
- [x] Regression test for the 149-character paste at 80 columns, width pinned (`test_inputstring_editing.py`).
- [x] Reported paste verified: full text returned; the drawn row stays on row 1.
- [ ] Confirm Ctrl-Shift-V in gnome-terminal (user).

## Phase 13: prompt layout in the terminal

- [x] First frame draws the prompt with its INS indicator (`cf5e605`).
- [x] Word-wrap disabled on every input-line draw (`f340e8a`). Stray line breaks in the scrolled window are gone in the scroll capture.
- [x] User confirms in gnome-terminal: layout and scrolling work much better.
- [ ] 4-character cursor offset from the prompt: not reproduced in the emulator; not confirmed fixed.

## Phase 14: mouse drag while the prompt waits

- [x] Cause: the prompt loop re-sent the cursor position on every wait timeout (about 65 times a second while idle). `inputboolean()` does not run that loop, and it drags fine (`92a1924`).
- [x] Fix: the cursor is placed only when the line is redrawn or the cursor column changes. Idle output is now one-time setup only.
- [x] Mouse push resets all four managed modes on entry; the exit restores the ones reported on (`1a1338d`).
- [x] `BBSENGINE_MOUSE_TRACE=<file>` logs query replies and writes (off by default).
- [x] User confirms drag works in gnome-terminal.

## Phase 15: io specifications

- [x] Specs moved to `handbook/specs/io/` (`git mv`), with an index. Legacy modules
  `input.py`, `output.py`, `lib.py` and `echovars.py` are marked deprecated and left alone.
- [x] Each live module's spec checked against its code and corrected: getch, inputstring,
  inputstring enhancements, inputboolean, inputinteger, inputchoice, getstr, inputcompleter
  (new), echo, echo_commands, palette, terminal, common, const, keymap, util, events,
  echovars, best practices.
- [x] Defects found while checking are recorded in the specs, not fixed: `inputcompleter`
  import error; `getstr` insert toggle tests `KEY_IC`; `inputchoice` return annotation
  promises a list (`inputinteger`); `{settitle}` does not exist; events do not fire during
  `inputstring()`.
- [x] Handbook index links the io folder; TODO and comment references point at the new paths.
- [x] `io_screen.spec` renamed to `screen.spec` and rewritten against `screen.py`. It stays in
  `py/src/bbsengine6/io/specs/` because `screen.py` is outside io. No `asimov` references remain.

## Version

- [x] Version bumped to `0.4.0.dev` (`py/Makefile` and `_version.py`).

## Phases 0 and 1: command registry

- [x] Phase 0: plan confirmed; names recorded (tiers protected/default/session; messages
  `command not found <name>` and `ambiguous command <prefix>`); `subprocess_term_check` default on.
- [x] Phase 1: `bbsengine6/commands.py` registry, committed with its tests (`bff28cb`).
- [x] Replace mode loads no default entries; registering one is refused. Found in review:
  replace mode previously held the default list.
- [x] Spec: `handbook/specs/commands.md`, linked from the specs index.

## Phase 2: interaction container

- [x] `bbsengine6/interaction.py`: `Interaction` holds the command registry; `current_session()`,
  `new_session()`, `use_session()` over a ContextVar with a module default. Named `interaction`
  because `bbsengine6/session/` is the login-session package.
- [x] Tests: default is used without a block; `use_session` restores, including after an
  exception; nested blocks; registries do not leak between interactions or into the default;
  each thread sees its own.
- [ ] Phase 3: move io state into the interaction (in progress).
  - [x] Read-through mechanism (`install_read_through`): module names become properties over the
    current interaction; module keeps its globals dict (`1fb02a3`).
  - [x] `io/common.py`: input queue, streams, terminal state and stack, dirty flag (`8e2f3ca`).
    Verified: no new failures in the full suite; zoidoffice, murdermotel and casino io tests
    match their recorded baselines.
  - [x] `io/echo.py`: raw mode, previous token, first-line flag, runtime vars, options (commit below).
  - [x] `io/inputstring.py`: key table, saved-handler map, yank buffer, snapshot stack, INS/OVR
    fragment state (commit below). Also fixes a split-brain: the prompt loop read
    `_input_dirty` by value from `common`, so its writes never reached the interaction.
    Built-in keys live in `_BUILTIN_KEY_ACTIONS` and are copied per interaction on first use.
    Verified: full suite at baseline (63 failed, 2283 passed; two baseline failures now pass);
    ed tests green; zoidoffice and casino io tests match baseline; murdermotel errors identical
    on clean HEAD (missing `murdermotel.player` table).
  - [ ] `io/getch.py` (impl selector, bottom-bar status).
  - [ ] `bottombar.py` / `screen.py` (registry, bar stack).

