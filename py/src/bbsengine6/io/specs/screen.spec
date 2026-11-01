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

- Moves the cursor up three rows from the next line, then saves the cursor with `{savecursor}`.
- Sets the scroll region to `topmargin` through `terminal.lines() - bottommargin`
  (DECSTBM), then restores the cursor with `{restorecursor}`.

Verified: `init(topmargin=2, bottommargin=1)` on a 24-row terminal sends `ESC[2;23r`.

`{savecursor}` sends a cursor-position query (DSR, `ESC[6n`) and waits for the reply, so
`init` needs a terminal or test harness that answers it.

### `updatebottombar(buf: str) -> None` (live)

Draws `buf` on the last terminal line, in the bottom-bar colour, without word wrap.
It saves and restores the cursor with `{savecursor}` / `{restorecursor}`, so it sends a
cursor-position query each time.

### `setbottombar(left, right=None, **kwargs)` (shim)

Delegates to `bottombar.setbottombar`. `left` and `right` may be strings or callables;
callables receive `**kwargs`. The left text is truncated with `...` when it does not fit,
and padding fills the rest of the row.

It returns `True`. An exception from the bottom-bar code propagates.

### `setarea(left, right=None, **kwargs)` (shim)

Alias for `setbottombar`. It emits the deprecation warning itself, then calls
`setbottombar`.

### `push` / `pop` (moved to `bottombar`)

`popbottombar`, `poparea`, and `bottombarstack` are removed. Use `bbsengine6.bottombar`:

- `bottombar.push(left=None, fragments=None)` saves the current left value and fragment
  items as one frame, installs the new ones, and repaints.
- `bottombar.pop(**kwargs) -> bool` restores the most recent frame and repaints. It
  returns `False` and does not repaint if nothing was pushed.

Frames hold the original values, so a callable `left` is called again on pop.

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
| `_default_registry` | The default `FragmentRegistry` from `bottombar.py`. |
| `_bottombar_fragments`, `_bottombar_fragments_lock` | Aliases of the default registry's list and lock, kept for callers that read them. They are the default registry only, not the per-connection registry. |

## Known issues

1. The shims are scheduled for removal ("will be removed in a future release"). Their
   removal date is not set.

Note: `init`, `updatebottombar`, and `updateprogress` use `{savecursor}`, which queries the
cursor position. On a terminal that does not reply it waits the full one-second timeout.

Fixed in the past and removed from this list: `io.getterminalwidth()` (now
`terminal.width()`), and the uninitialised `bottombarstack` (now an empty list).
