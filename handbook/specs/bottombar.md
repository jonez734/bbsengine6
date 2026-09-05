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

## Contents

- [Public API](#public-api)
- [Fragment types](#fragment-types)
- [Lifecycle](#lifecycle)
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

`setbottombar` is the drop-in replacement for the old
`bbsengine6.io.screen.setbottombar`. It accepts the same args and
kwargs, returns `True` to match the previous contract.

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
