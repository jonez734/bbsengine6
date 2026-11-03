# standardized finally clause in main — bbsengine6

Every program's `finally` on exit should call `bottombar.shutdown()`, and every program's setup
should call `bottombar.init()`. Neither should use the deprecated `screen.init()` shim or a private
once-per-process flag.

Contract (bbsengine6 `bottombar`):
- `init()` runs once per process, and sets the scroll region on a tty only.
- `shutdown()` shuts down object fragments first, then, only if `init()` ran, clears the bottom bar line,
  resets colors and margins (`{reset}`), and restores the cursor. It never raises and does nothing without
  a tty.
- Interrupt and EOF messages print `{/all}*INTR*` / `{/all}*EOF*` with no cursor restore in the text, so
  `shutdown()` restores the cursor after the message.

Verify by driving the program under a pty, interrupting it, and checking that the exit bytes end in this
order: color reset, message, bar-line clear, color reset, margin reset, cursor restore.

## Open

- [ ] `src/bbsengine6/console/tui.py`: its `finally` (around line 139) runs its own sequence. Switch it to `bottombar.shutdown()`, and its `**INTR**`/`**EOF**` messages to the `{/all}*INTR*` convention.
- [ ] `src/bbsengine6/ed/common/ui.py`: replace the private `_screen_initialized` guard with `bottombar.init()`.
- [ ] `src/bbsengine6/startup/__main__.py` and `src/bbsengine6/subprocess_command.py`: already call `bottombar.init()`. Confirm each has a matching `shutdown()` on exit.
- [ ] Remove the deprecated `bbsengine6.screen.init()` calls that remain in demos and scripts that a program can still run (not `build.*` directories).
- [ ] Keep the object-fragment contract documented in `handbook/specs/bottombar.md` in step with any change here.
