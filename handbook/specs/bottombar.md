# bbsengine6.bottombar — fragment registry

> **Status:** canonical. Phase 4a complete; Phase 5b (wire push to
> thin clients) is future work tracked in
> `bbsengine6/TODO-BOTTOMBAR.md`.

`bbsengine6.bottombar` is a thread-safe, per-package fragment
registry that centralizes the boilerplate every BBS package
(empyre, casino, bed bank, ed, …) used to repeat for the bottom
status bar. Fragments can be strings, lists of strings, or
callables; the registry renders them joined with `" | "` and
prepends the unread-notification status when the message system
is enabled.

**Known issue.** The unread count shown in the notification status can lag
behind the database. The count is cached per process and the cache is not
refreshed while the session is idle, so a message sent after login may not
appear until the cache is cleared. Tests for the refresh are in
`py/tests/test_notification_cache_refresh.py` (marked xfail). A fix that
re-reads the count on every redraw was tried and reverted: it caused suite-wide
regressions and its cause is not yet identified.

## Contents

- [Public API](#public-api)
- [Fragment types](#fragment-types)
- [Lifecycle](#lifecycle)
- [Object fragments](#object-fragments)
- [Shutdown](#shutdown)
- [Prompts and the MODE fragment](#prompts-and-the-mode-fragment)
- [Registry resolution](#registry-resolution)
- [Per-connection routing](#per-connection-routing)
- [Notification fragment](#notification-fragment)
- [Phase 5b (future)](#phase-5b-future)

## Public API

### Class: `FragmentRegistry`

```python
class FragmentRegistry:
    name: str
    items: _LockedList              # list subclass with .lock
    args: Any | None
    player: Any | None
    pool: Any | None

    def __contains__(item) -> bool
    def __iter__() -> Iterator[FragmentItem]
    def __len__() -> int

    def register(item: FragmentItem) -> FragmentItem
    def unregister(item: FragmentItem) -> bool
    def clear() -> None
    def set_context(args=None, player=None, pool=None) -> None
    def render(**kwargs) -> str
```

| Method                          | Notes                                                                                   |
|---------------------------------|-----------------------------------------------------------------------------------------|
| `register(item)`                | Append if not already present; idempotent. Returns the item unchanged                    |
| `unregister(item)`              | Remove the first matching item; returns `True` if removed                               |
| `clear()`                       | Remove every item                                                                        |
| `set_context(...)`              | Stash `args`, `player`, `pool` so fragment callables can read them at render time       |
| `render(**kwargs)`              | Render every item in registration order, joined with `" | "`; prepends the notification fragment when non-empty |

### Module-level functions

| Function                          | Signature                                                | Notes                                                                |
|-----------------------------------|----------------------------------------------------------|----------------------------------------------------------------------|
| `default_registry()`              | `() -> FragmentRegistry`                                 | Process-global registry, cached under `_REGISTRY_CACHE["default"]`   |
| `registry_for(name)`              | `(str) -> FragmentRegistry`                              | Cached per-name registry; bypasses the ContextVar                    |
| `set_context_for(name, *, args, player, pool)` |                                       | Stash context on `registry_for(name)`                                |
| `render_for(name, **kwargs)`      | `(str) -> str`                                           | Render `registry_for(name)`                                           |
| `set_active_registry(reg)`        | `(FragmentRegistry | None) -> Token`                     | Set the ContextVar; returns a token for `reset_active_registry()`     |
| `reset_active_registry(token)`    | `(Token) -> None`                                        | Reset the ContextVar to its default                                   |
| `register_bottombar_fragment(item)` |                                                      | Routes through the ContextVar if set, else the default registry       |
| `unregister_bottombar_fragment(item)` |                                                    | (same routing)                                                         |
| `clear_bottombar_fragments()`     |                                                          | (same routing)                                                         |
| `setbottombar(args, buf, **kwargs)` | `(Any, str) -> bool`                                   | Central shim: stash context, render with `buf` on the left            |
| `init(args=None, topmargin=1, bottommargin=1)` | `(Any, int, int) -> None`                   | Set the scroll region so the bar stays on the last line. Call once per screen, before the first `setbottombar`. Replaces `bbsengine6.screen.init` (deprecated shim) |
| `is_initialized()` | `() -> bool` | True between `init()` and `shutdown()` |
| `shutdown()` | `() -> None` | Restore the terminal on exit: shut down object fragments, then clear the bar line, reset colors and margins, restore the cursor. Never raises. See [Shutdown](#shutdown) |
| `push(left=None, fragments=None)` | `(Any, Iterable) -> None`                        | Save left and fragments as one frame, install new values (`None` keeps, `[]` clears), repaint |
| `pop(**kwargs)`                   | `(**kwargs) -> bool`                             | Restore the top frame and repaint. Returns `False` and does not repaint if empty |

### Push and pop

`push` and `pop` save and restore the bar state of the active registry (or the
ContextVar-routed one in BED):

```python
bottombar.push(left="Lobby", fragments=["F1: help"])  # save, install, repaint
...
bottombar.pop()                                       # restore previous, repaint
```

- Frames store the original values: the `left` str or callable, and a copy of the
  fragment items. Rendered output is not stored.
- A callable `left` is called again on pop, so its value is fresh.
- `push()` with no arguments saves a frame and repaints the current values.
- Stacks are per registry, guarded by the registry lock.
- `popbottombar` / `poparea` / `bottombarstack` are removed; use these instead.

`setbottombar` is the drop-in replacement for the old
`bbsengine6.io.screen.setbottombar`. It accepts the same args and
kwargs, returns `True` to match the previous contract.

### Scroll region: `init`

`init` owns the terminal scroll-region setup. Callers use it instead of
the deprecated `bbsengine6.screen.init`, which emits a `DeprecationWarning`
and delegates to nothing new. The console entry, the editor's
`init_screen`, and `startup/__main__.py` all call `bottombar.init`.

`init` runs once per process. A second call before `shutdown()` does nothing, so
a tool can call it from several entry points safely. It sets the flag only when
the scroll region is actually set (a tty), so a non-tty run stays a no-op and a
later call on a tty still works. `shutdown()` clears the flag, so a later `init()`
in the same process runs again.

Callers should not keep their own once-per-process flags. Call `bottombar.init()`
and let this module own the state.

### Type alias

```python
FragmentItem = Union[str, Callable[..., Optional[str]]]
```

A fragment is either a string (rendered verbatim) or a callable
that takes any kwargs and returns a string (or `None`).

## Fragment types

`FragmentItem` accepts three runtime shapes:

| Runtime form        | Behavior                                                                |
|---------------------|-------------------------------------------------------------------------|
| `str`               | Rendered verbatim via `str(item)`                                       |
| `Callable[..., str]`| Invoked with the merged kwargs; result coerced via `str(result)`; traceback caught |
| Object with `render()` | See [Object fragments](#object-fragments). Optional `init(**kwargs)` runs lazily on the first render; optional `shutdown()` runs when the fragment leaves the bar or the screen is restored |
| List of fragments   | (Historical; the modern API is `register` one item at a time. The previous list-of-strings contract is preserved by registering each string as its own item, which the renderer joins with `" | "`.) |

The rendered output is always `" | ".join(parts)` with the
notification fragment (if any) prepended.

## Lifecycle

```
setbottombar(args, "In casino lobby", **kwargs)
  │
  ├─ registry = _resolve_registry()
  ├─ registry.set_context(args=args, player=..., pool=...)
  └─ _render_bottombar(registry, left="In casino lobby", right=None, **kwargs)
       │
       ├─ left_buf = left(**kwargs) if callable else left
       ├─ right_buf = registry.render(**kwargs) if len(registry) else ""
       ├─ truncate left if needed (terminalwidth - right_len - 5)
       └─ echo ANSI bottom bar with savecursor / curpos / restorecursor
```

The bottombar is always emitted to the **default** terminal. The
truncation math is unchanged from the legacy `io.screen.setbottombar`
implementation so door-mode output is byte-for-byte identical.

## Object fragments

A fragment may be an object with a `render(**kwargs)` method instead of a bare
callable. It may also define two optional hooks:

```python
class TableFragment:
    def init(self, **kwargs):      # optional: acquire resources; kwargs carries args/pool/player
        self.conn = kwargs["pool"].getconn()
    def render(self, **kwargs):    # required: return a string or None
        return f"table: {self.count}"
    def shutdown(self):            # optional: release what init() acquired
        self.pool.putconn(self.conn)

bottombar.register_bottombar_fragment(TableFragment())
```

- **Lazy init.** `register()` only adds the item. `init()` runs on the first `render()`,
  not at registration, so a fragment that is registered but never painted costs nothing.
- **Failure policy.** If `init()` raises, the error is reported once and the fragment
  is skipped for the rest of the process. It is not retried on every repaint, which
  would flood the log.
- **Teardown.** `unregister()` calls `shutdown()` on an initialized fragment, and so
  does `clear()` for every initialized fragment in the registry.
- **Failure isolation.** Each `shutdown()` runs inside try/except. A raising fragment is
  reported and the others still run.
- **Plain callables and strings** are unchanged: no init, no shutdown.

Rules for fragment authors:

1. **Borrow the pool, do not open connections.** Use the `pool` the registry passes in
   through `init()` and `render()`. Do not call `database.connect()` from a fragment.
2. **Do not start threads.** A fragment returns a string from state it already holds.
   Work that needs a thread or I/O runs elsewhere and writes its result into that state.
3. **Keep `init()` small.** The first `init()` runs on the first redraw, so a slow
   `init()` delays that redraw. Defer heavy work.

## Shutdown

`shutdown()` is the exit counterpart to `init()`. A tool calls it from a `finally`
block so the terminal is restored on every exit path, including an exception.

Order, when the screen was initialized:

1. Shut down every initialized object fragment in every registry this process knows
   about. Fragment teardown runs even when `init()` never set the screen, because a
   fragment's resources do not depend on the screen.
2. Clear the bottom bar line: `{savecursor}{curpos:<bottom>,0}{el}`.
3. Reset colors and margins: `{reset}` emits SGR 0 and then the margin reset.
4. Restore the cursor: `{restorecursor}`.
5. Clear the initialized flag.

The screen steps (2 to 5) run only when `init()` set the flag, so an exit before setup
emits no escape sequences. They also skip without a tty. `shutdown()` never raises.

Put it in a `finally` and do not add a separate cleanup path:

```python
def main():
    bottombar.init()
    try:
        run()
    except KeyboardInterrupt:
        io.echo("{/all}*INTR*")
    finally:
        bottombar.shutdown()
```

Interrupt and EOF messages print `{/all}*INTR*` (or `*EOF*`) with no cursor restore in
the text. `shutdown()` restores the cursor after the message, so the message lands on
the screen in default colors.

## Prompts and the MODE fragment

`inputstring()` shows the insert/overwrite mode as a fragment in the bottom bar. While a
prompt is active, it repaints the bar at three points:

1. when the prompt starts (after the prompt text is drawn);
2. when INSERT is pressed (the mode changes);
3. when the prompt ends (the fragment is removed).

Pass `bottombar=False` to `inputstring()` to skip all three paints. The mode is still
tracked and editing is unchanged. The default is `True`, which keeps the bar updated
during prompts.

```python
inputstring("name: ", "", bottombar=False)   # the bar is not repainted
inputpassword("password: ", bottombar=False) # same; inputpassword passes kwargs through
```

`bottombar=False` controls only whether the bar is painted. It does not change what the
prompt returns, and it does not register or unregister the fragment differently.

Use it when a prompt's colors must not be overwritten by a bar repaint. letteredolive's
login prompts use it for this reason.

The bar's own update uses `{savecursor}` and `{restorecursor}`. `{savecursor}` queries the
cursor position first, so each bar update waits for the terminal's reply.

## Registry resolution

`_resolve_registry(name=None)` picks the registry for a given call:

1. The ContextVar-set registry (`_active_registry.get()`), if any —
   this is the BED per-connection override.
2. The named registry from `_REGISTRY_CACHE`, if `name` is not None.
3. `default_registry()`.

`registry_for(name)` skips step 1 — the name is explicit. This is
the canonical entry point for per-package code that wants a
dedicated registry (e.g. `casino.lib._casino_registry =
bottombar.registry_for("casino")`).

The default registry is cached under the key `"default"`; both
`registry_for("default")` and `default_registry()` return the same
object.

## Per-connection routing

The `_active_registry` ContextVar (`bbsengine6.bottombar.active_registry`,
default `None`) routes module-level helpers (`register_*`,
`unregister_*`, `clear_*`, `setbottombar`) to a per-connection
registry when one is set:

```python
reg = FragmentRegistry(name=f"conn-{session_id}")
token = set_active_registry(reg)
try:
    # Every register_/unregister_/clear_/setbottombar call lands here.
    register_bottombar_fragment(_host_fragment)
    setbottombar(args, "casino", **kwargs)
finally:
    reset_active_registry(token)
```

Door mode never sets the ContextVar — the default registry is
used and the behavior matches the pre-Phase-4a contract bit-for-bit.

## Notification fragment

`_get_notification_status(args, pool, **kwargs)` returns a string
like `"F2: messages (3)"` when the current moniker has unread
messages, or `""` when there are none. The fragment is prepended
to `right` on every render when non-empty.

Lookup order:

1. `bbsengine6.member._threadlocal.moniker` — the current session's
   moniker (set by bed on connect).
2. `bbsengine6.message.is_enabled()` — if False, returns `""`.
3. `bbsengine6.message.get_local_unread_count(moniker)` — the
   in-process cache. `-1` means "never read" → falls through to a
   `get_unread_count(moniker, ...)` DB read and seeds the cache.
4. Otherwise returns the cached count, formatted as
   `"F2: messages (N)"`.

The `KEY_F2` binding in `io/getch.py` reads the same source, so
the bottombar count and the F2 hotkey stay in sync.

### Terminal bell

The bell is rung from `io/getch.py`, not the bottombar, and rings only
when the unread count **rises**:

- `BellBaseline` keeps, per moniker and per process, the unread count the
  last bell was based on. A bell rings only when the count is greater than
  that baseline. Repeated checks with the same count never ring, so a
  message that stays unread does not ring every poll.
- A drop in the count lowers the baseline, so a later rise rings again
  (3 -> 1 -> 2 rings on the rise to 2).
- A reconnect starts the baseline at zero, so the first unread count rings once.
- `BellWindow` (default 5 s; bed's `notify.bell_window_seconds`, applied with `set_bell_window_seconds`) still
  collapses a burst of rises into one bell.

Three call sites use one helper, `_emit_bell_for(baseline, moniker, count)`:
the pre-wait check on each `getch`, the idle poll (every 2 s without a bed
push), and the wake path when the local cache changes. Each passes the
count it has just read.

## Phase 5b (future)

`bbsengine6/TODO-BOTTOMBAR.md` tracks the wire-push phase. The
shape:

- `render_structured(registry, left, **kwargs) -> dict` returns
  `{"left": str, "right": List[str], "separator": " | ",
  "left_priority": "truncate", "ts": iso}` with MCI-substituted
  fragment strings (so the thin client can do its own width
  math).
- `to_echo_payload(registry, left, **kwargs) -> dict` strips the
  envelope-owned fields (`ts` / `request_id` / `seq`) and produces
  the `echo.payload` shape used by the `echo{stream:"bottombar"}`
  wire frame.
- The thin client (`bed/client/bottombar.py`) receives the
  `echo` envelope and runs the layout step (width measurement,
  truncation, padding, cursor positioning) locally.
- Door mode (no ContextVar, no websocket) is unchanged;
  `py/tests/test_bottombar.py` and `py/tests/test_screen.py` stay
  green as the byte-for-byte parity gate.

Per-package fragments already migrated to the registry:
- `bbsengine6.bottombar.registry_for("casino")` (casino)
- `bbsengine6.bottombar.registry_for("bed")` (bed bank)

Per-package fragments pending migration:
- empyre (currently constructs `FragmentRegistry(name="empyre")`
  directly — one-line swap to `registry_for("empyre")`).
- mistermcfeely (postoffice), murdermotel, zoid6 — see
  `bbsengine6/TODO-BOTTOMBAR.md` §"Other packages".
