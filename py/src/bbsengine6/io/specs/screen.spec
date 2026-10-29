# bbsengine6.screen Specification

## Overview

`screen.py` is the canonical module for screen positioning and the bottom bar. The
bottom bar's logic lives in `bbsengine6.bottombar`. `screen.py` keeps the older API
(`init`, `setbottombar`, `setarea`, the fragment functions) as back-compat shims that
delegate to `bottombar.py`, plus two functions that have no shim: `updatebottombar`
and `updateprogress`.

New code should import from `bbsengine6.bottombar`. Callers that import
`bbsengine6.screen` (or `bbsengine6.io.screen`, which is a pre-registered alias of
this module) keep working.

## Status of each function

| Function | Status | Emits DeprecationWarning |
|---|---|---|
| `init` | shim | yes |
| `updatebottombar` | live | no |
| `setbottombar` | shim | yes |
| `setarea` | shim, alias of `setbottombar` | yes |
| `popbottombar` / `poparea` | live, see below | no |
| `updateprogress` | live | no |
| `get_notification_status` | shim | yes |
| `clear_bottombar_fragments` | shim | yes |
| `register_bottombar_fragment` | shim | yes |
| `unregister_bottombar_fragment` | shim | yes |
| `_render_bottombar_fragments` | shim (private) | yes |

The warning is a `DeprecationWarning` naming `bbsengine6.screen.<name>`. It is raised
on every call, not once.

## Dependencies

- `io/echo.py`: output, `echo_traceback`, `rendered_length`
- `io/terminal.py`: `lines()` and `width()`
- `bottombar.py`: the registry and rendering the shims delegate to

## Functions

### `init(args=None, topmargin=1, bottommargin=1)` (shim)

Sets a scroll region that leaves `topmargin` rows above it and `bottommargin` rows
below it for the bottom bar.

- Moves the cursor up three rows from the next line, then saves the cursor with ESC 7.
- Sets the scroll region to `topmargin` through `terminal.lines() - bottommargin`
  (DECSTBM), then restores the cursor with ESC 8.

Verified: `init(topmargin=2, bottommargin=1)` on a 24-row terminal sends `ESC[2;23r`.

The cursor is saved and restored with the terminal's own ESC 7 / ESC 8, so `init`
sends no cursor-position query and does not wait for a reply.

### `updatebottombar(buf: str) -> None` (live)

Draws `buf` on the last terminal line, in the bottom-bar colour, without word wrap.
It saves and restores the cursor with ESC 7 / ESC 8 and sends no cursor-position query.

### `setbottombar(left, right=None, **kwargs)` (shim)

Delegates to `bottombar.setbottombar`. `left` and `right` may be strings or callables;
callables receive `**kwargs`. The left text is truncated with `...` when it does not fit,
and padding fills the rest of the row.

It returns `True`. An exception from the bottom-bar code propagates.

### `setarea(left, right=None, **kwargs)` (shim)

Alias for `setbottombar`. It emits the deprecation warning itself, then calls
`setbottombar`.

### `popbottombar()` / `poparea()` (live)

Pops a string from `bottombarstack` and draws it as the bottom bar. If the stack is
empty it does nothing.

**Nothing in the package pushes onto `bottombarstack`.** `setbottombar` does not save
the previous bar. Verified: two `setbottombar` calls leave the stack empty, and
`popbottombar()` then has no effect. The stack is a public list, so a caller may push
onto it directly; no code in the repository does.

### `updateprogress(iteration, total, fill="#")` (live)

Draws a text progress bar on the bottom bar:

- Width is `terminal.width() - 20`. On an 80-column terminal the bar is 60 characters.
- The bar is filled with `fill` up to the completed fraction, then `.` for the rest.
- The percentage is shown as a whole number.

Verified: `updateprogress(3, 10)` on an 80-column terminal draws a 60-character bar.

### `get_notification_status(**kwargs) -> str` (shim)

Delegates to `bottombar._get_notification_status(args=, pool=)`.

Returns `"F2: messages (N)"` when the moniker has N > 0 unread messages, and `""`
otherwise, including when messaging is disabled or no moniker is set. Any exception
is reported through `echo_traceback` and an empty string is returned.

**Read path.** The function reads the process-local cache
`message.get_local_unread_count(moniker)`. A value below 0 means "never read"; the
function then calls `message.get_unread_count(moniker, args=, pool=)` and stores the
result with `set_local_unread_count`.

**Correction to earlier text:** the cache is not filled by bed's server-push
notifications in the live source tree. The `bottombar` docstring says the bed
subscription (`bbsengine6.startup.message_subscription`) is present only in installed
copies. In the source tree the cache is refreshed by the poll in `getch`, not by
`LISTEN`/`NOTIFY`.

## Module state

| Name | Description |
|---|---|
| `bottombarstack` | Public list read by `popbottombar`. Empty unless a caller appends to it. |
| `_bottombarstack_lock` | Guards `bottombarstack`. |
| `_default_registry` | The default `FragmentRegistry` from `bottombar.py`. |
| `_bottombar_fragments`, `_bottombar_fragments_lock` | Aliases of the default registry's list and lock, kept for callers that read them. They are the default registry only, not the per-connection registry. |

## Known issues

1. `popbottombar` has no producer in the package (see above). It is a no-op in practice.
2. The shims are scheduled for removal ("will be removed in a future release"). Their
   removal date is not set.

Fixed: `init`, `updatebottombar`, and `updateprogress` no longer query the terminal for
the cursor position. They used `{savecursor}`, which waited the full one-second timeout
on a terminal that does not reply. They now use ESC 7 / ESC 8 (verified: no DSR query,
under 0.01 s for all three).

Fixed in the past and removed from this list: `io.getterminalwidth()` (now
`terminal.width()`), and the uninitialised `bottombarstack` (now an empty list).
