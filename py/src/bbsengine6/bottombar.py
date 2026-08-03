# bbsengine6.bottombar - General-purpose bottombar fragment registry.
#
# Centralizes the boilerplate that every BBS package (empyre, casino, bbsengine6
# startup/backend, ed, ...) used to repeat: a global list of fragments, lock
# management, register/unregister helpers, and the args/player stashing that
# fragment callables read at render time.
#
# Public surface:
#   class FragmentRegistry
#       register(item) -> item
#       unregister(item) -> bool
#       clear() -> None
#       render(**kwargs) -> str
#       set_context(args=None, player=None, pool=None) -> None
#       attributes: name, args, player, pool, lock
#       __contains__, __iter__, __len__
#
#   default_registry() -> FragmentRegistry
#       Process-global registry. Matches the pre-existing behavior of
#       bbsengine6.io.screen._bottombar_fragments.
#
#   setbottombar(args, buf, **kwargs) -> bool
#       Central shim: stashes args/player/pool on the default registry and
#       renders the bottom bar. Drop-in replacement for the per-package
#       setbottombar(args, buf, **kwargs) wrappers.
#
#   register_bottombar_fragment(item) / unregister_bottombar_fragment(item) /
#   clear_bottombar_fragments() -> None
#       Module-level convenience bound to default_registry() for back-compat
#       with the old bbsengine6.io.screen API. Honor the ContextVar
#       set_active_registry() if one is set (BED per-connection override).
#
#   registry_for(name) -> FragmentRegistry
#       Factory that returns a cached, named FragmentRegistry. The default
#       registry is cached under the key "default" and is the same object
#       as default_registry(). Per-package code (e.g. empyre.lib) can call
#       registry_for("empyre") to get a private registry without going
#       through the ContextVar.
#
#   set_context_for(name, **ctx) / render_for(name, **kwargs) -> None / str
#       Convenience wrappers that look up registry_for(name) and stash
#       context / render. BED-sink code that already has a name in hand
#       can use these without first calling registry_for(name).
#
#   set_active_registry(reg) -> token
#   reset_active_registry(token) -> None
#       ContextVar plumbing for BED per-connection setup/teardown. When
#       set, every module-level helper and every io.screen back-compat
#       shim routes to the supplied registry instead of the default.
#       Door mode (no ContextVar set) is unchanged.

import contextvars
import threading
from typing import Any, Callable, Iterable, List, Optional, Union

from .io.echo import echo, echo_traceback, rendered_length
from .io import terminal

FragmentItem = Union[str, Callable[..., Optional[str]]]


def _get_notification_status(args: Any = None, pool: Any = None, **kwargs) -> str:
    """Return the message status string, e.g. 'F2: messages (3)' or ''.

    Imported here (rather than at module load time) to avoid an import cycle
    with bbsengine6.member / bbsengine6.message, and to match the lazy-import
    behavior the old io.screen.get_notification_status already used.

    The `cached` value below is the last DB-derived unread count seen by
    this process for this moniker (sentinel -1 means "never read"). It is
    NOT a bed server-push cache in the current build: the bed subscription
    in bbsengine6.startup.message_subscription is only present in installed
    venv copies and is not wired into the live source tree, so the
    poll-while-idle loop in getch_str is what actually keeps this fresh.
    """
    try:
        from bbsengine6.member import _threadlocal

        moniker = getattr(_threadlocal, "moniker", None)
        if not moniker:
            return ""

        from bbsengine6 import message as message_module

        if not message_module.is_enabled():
            return ""

        # Last DB-derived count seen in this process; -1 sentinel = never read.
        cached = message_module.get_local_unread_count(moniker)
        if cached < 0:
            count = message_module.get_unread_count(
                moniker, args=args, pool=pool, **kwargs
            )
            message_module.set_local_unread_count(moniker, count or 0)
        else:
            count = cached
        if count and count > 0:
            return f"F2: messages ({count})"
    except Exception:
        echo_traceback("bbsengine6.bottombar._get_notification_status:")
    return ""


class _LockedList(list):
    """A `list` subclass with a sibling lock for thread-safe bulk operations.

    Inherits from `list` so legacy code (and tests) that does
    `isinstance(x, list)` keeps working. Each instance carries a
    `threading.Lock` accessible via the `.lock` attribute that callers
    can hold around compound operations (snapshot, register-then-render,
    etc.).

    Note: the list-mutation methods inherited from `list` (`append`,
    `remove`, `clear`, ...) are *not* automatically locked — they are
    plain list ops, just like the original `_bottombar_fragments` list.
    The `FragmentRegistry` class locks around its own `register` /
    `unregister` / `clear` / `render` methods, which is the supported
    way to mutate the registry from multiple threads. The lock is also
    available for external callers that need to do compound operations
    atomically.
    """

    def __init__(self, iterable: Optional[Iterable[FragmentItem]] = None) -> None:
        super().__init__(iterable if iterable is not None else [])
        self.lock = threading.Lock()

    def snapshot(self) -> List[FragmentItem]:
        """Return a shallow copy of the list, taken under the lock."""
        with self.lock:
            return list(self)


class FragmentRegistry:
    """A thread-safe, named list of bottombar fragment items.

    Items are either str (rendered verbatim) or callable(**kwargs) -> str
    (invoked on every render, errors are caught and tracebacked). Items are
    joined with ' | ' and prefixed by the notification status when present.

    The registry also holds a small "context" — args, player, pool — that
    fragment callables may read. This is the same shape that the per-package
    setbottombar(args, buf, **kwargs) shims used to stash into module globals
    before calling screen.setbottombar; centralizing it removes a class of
    hidden-state bugs.

    The registry's `items` attribute is a `_LockedList`. It can be shared
    with legacy code that mutates it directly (e.g. the
    `bbsengine6.io.screen._bottombar_fragments` back-compat shim) — both
    code paths see the same data, protected by the same lock.
    """

    def __init__(
        self,
        name: str = "default",
        items: Optional[_LockedList] = None,
    ) -> None:
        self.name = name
        self.items: _LockedList = items if items is not None else _LockedList()
        self.lock = self.items.lock
        self.args: Any = None
        self.player: Any = None
        self.pool: Any = None

    def __contains__(self, item: FragmentItem) -> bool:
        return item in self.items

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def register(self, item: FragmentItem) -> FragmentItem:
        """Add an item if not already present. Returns the item unchanged.

        Args:
            item: str or callable(**kwargs) -> str.
        """
        with self.lock:
            if item not in self.items:
                self.items.append(item)
        return item

    def unregister(self, item: FragmentItem) -> bool:
        """Remove the first matching item. Returns True if removed."""
        with self.lock:
            if item in self.items:
                self.items.remove(item)
                return True
        return False

    def clear(self) -> None:
        """Remove every item from this registry."""
        with self.lock:
            self.items.clear()

    def set_context(
        self,
        args: Any = None,
        player: Any = None,
        pool: Any = None,
    ) -> None:
        """Stash args/player/pool so fragment callables can read them.

        These attributes are plain Python attributes — not part of the lock —
        because in practice the per-package setbottombar shim is the sole
        writer and fragments only read them at render time. If you need
        fully thread-safe context, set them once at startup and treat them
        as immutable thereafter, or wrap your own lock around writes.
        """
        if args is not None or not hasattr(self, "args") or self.args is None:
            self.args = args
        if player is not None:
            self.player = player
        if pool is not None:
            self.pool = pool

    def render(self, **kwargs) -> str:
        """Render every item in registration order, joined with ' | '.

        Callables receive **kwargs. The registry's args/player/pool are
        also passed as kwargs (without overwriting anything the caller
        already supplied), so existing fragments that read either style
        continue to work.
        """
        items_snapshot = self.items.snapshot()

        merged = dict(kwargs)
        if self.args is not None and "args" not in merged:
            merged["args"] = self.args
        if self.player is not None and "player" not in merged:
            merged["player"] = self.player
        if self.pool is not None and "pool" not in merged:
            merged["pool"] = self.pool

        parts: List[str] = []

        for item in items_snapshot:
            if callable(item):
                try:
                    result = item(**merged)
                    if result:
                        parts.append(str(result))
                except Exception:
                    echo_traceback(f"bbsengine6.bottombar.render({self.name}):")
            elif item:
                parts.append(str(item))

        notification = _get_notification_status(
            args=merged.get("args"),
            pool=merged.get("pool"),
        )
        if notification:
            parts.insert(0, notification)

        return " | ".join(parts)


_DEFAULT_REGISTRY: Optional[FragmentRegistry] = None
_REGISTRY_CACHE: dict = {}
_REGISTRY_CACHE_LOCK = threading.Lock()

# BED per-connection routing. When set, every module-level helper and
# every io.screen back-compat shim routes against this registry instead
# of the process-global default. Door mode leaves this at its default
# (None), preserving the pre-Phase-4a behavior bit-for-bit.
_active_registry: "contextvars.ContextVar[Optional[FragmentRegistry]]" = (
    contextvars.ContextVar(
        "bbsengine6.bottombar.active_registry", default=None
    )
)


def default_registry() -> FragmentRegistry:
    """Return the process-global FragmentRegistry, creating it on first use.

    The default registry is also cached in `_REGISTRY_CACHE` under the
    key "default" so `registry_for("default")` and `default_registry()`
    return the same object. This keeps `_REGISTRY_CACHE` and the
    `_DEFAULT_REGISTRY` global in sync.
    """
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        with _REGISTRY_CACHE_LOCK:
            if _DEFAULT_REGISTRY is None:
                reg = FragmentRegistry(name="default")
                _DEFAULT_REGISTRY = reg
                _REGISTRY_CACHE["default"] = reg
    return _DEFAULT_REGISTRY


def _resolve_registry(name: Optional[str] = None) -> FragmentRegistry:
    """Pick the registry to use for the current call.

    Priority:
      1. The ContextVar-set registry, if any (BED per-connection override).
      2. The named registry from the cache, if `name` is not None.
      3. default_registry().

    `registry_for(name)` bypasses this helper and the ContextVar: the
    name is always explicit.
    """
    active = _active_registry.get()
    if active is not None:
        return active
    if name is not None:
        with _REGISTRY_CACHE_LOCK:
            reg = _REGISTRY_CACHE.get(name)
            if reg is None:
                reg = FragmentRegistry(name=name)
                _REGISTRY_CACHE[name] = reg
            return reg
    return default_registry()


def registry_for(name: str) -> FragmentRegistry:
    """Return a cached FragmentRegistry for `name`.

    Always returns the same instance for the same `name` within this
    process. Bypasses the ContextVar — the name is explicit. The
    default registry is cached under the key "default" and is the same
    object as default_registry(); both are stored in `_REGISTRY_CACHE`
    so iterating the cache surfaces them too.
    """
    if name == "default":
        return default_registry()
    with _REGISTRY_CACHE_LOCK:
        reg = _REGISTRY_CACHE.get(name)
        if reg is None:
            reg = FragmentRegistry(name=name)
            _REGISTRY_CACHE[name] = reg
        return reg


def set_context_for(
    name: str,
    *,
    args: Any = None,
    player: Any = None,
    pool: Any = None,
) -> None:
    """Stash args/player/pool on registry_for(name)."""
    registry_for(name).set_context(args=args, player=player, pool=pool)


def render_for(name: str, **kwargs) -> str:
    """Render registry_for(name)."""
    return registry_for(name).render(**kwargs)


def set_active_registry(reg: Optional[FragmentRegistry]):
    """Set the per-connection active registry. Returns a token suitable
    for reset_active_registry().

    Intended for BED connection setup. Door mode (no ContextVar set)
    is unaffected.
    """
    return _active_registry.set(reg)


def reset_active_registry(token) -> None:
    """Reset the per-connection active registry to the ContextVar default."""
    _active_registry.reset(token)


def register_bottombar_fragment(item: FragmentItem) -> FragmentItem:
    """Register an item on the active registry. Returns the item unchanged.

    Routes through the ContextVar if one is set (BED per-connection),
    otherwise the default registry.
    """
    return _resolve_registry().register(item)


def unregister_bottombar_fragment(item: FragmentItem) -> bool:
    """Unregister an item from the active registry.

    Routes through the ContextVar if one is set, otherwise the default
    registry.
    """
    return _resolve_registry().unregister(item)


def clear_bottombar_fragments() -> None:
    """Remove every item from the active registry.

    Routes through the ContextVar if one is set, otherwise the default
    registry.
    """
    _resolve_registry().clear()


def setbottombar(args: Any, buf: str, **kwargs) -> bool:
    """Central setbottombar shim used by every BBS package.

    Stashes args/player/pool on the default registry, then renders the
    bottom bar with `buf` on the left and the registered fragments on
    the right (truncating the left with "..." if it doesn't fit).

    Args:
        args: Application argparse.Namespace, propagated to fragments and
            to the notification subsystem so they can resolve their DB
            connection. May be None.
        buf: Left-side text to display.
        **kwargs: Forwarded to fragment callables. Recognized keys:
            player, pool — stored on the default registry if provided.

    Returns:
        True (matches the previous bbsengine6.io.screen.setbottombar contract).
    """
    registry = _resolve_registry()
    player = kwargs.get("player", None)
    pool = kwargs.get("pool", None)
    registry.set_context(args=args, player=player, pool=pool)

    return _render_bottombar(registry, left=buf, right=None, **kwargs)


def _render_bottombar(
    registry: FragmentRegistry,
    left: Any,
    right: Any = None,
    **kwargs,
) -> bool:
    """Lay out `left` and `right` on the bottom bar and emit it.

    If `right` is None and the registry has fragments, the right side is
    rendered from the registry. If `right` is callable it is invoked with
    **kwargs. Strings are used verbatim.

    The truncation/padding math is unchanged from the original
    bbsengine6.io.screen.setbottombar implementation so the visual output
    is identical.
    """
    terminalwidth = terminal.width() - 2

    if callable(left) is True:
        left_buf = left(**kwargs)
    else:
        left_buf = left

    if right is None:
        right_buf = registry.render(**kwargs) if len(registry) else ""
    elif callable(right) is True:
        right_buf = right(**kwargs)
    else:
        right_buf = right

    if right_buf is None:
        right_buf = ""

    left_len = rendered_length(left_buf)
    right_len = rendered_length(right_buf)
    max_left_len = terminalwidth - right_len
    if left_len > max_left_len:
        truncate_to = max(0, max_left_len - 5)
        left_buf = left_buf[:truncate_to] + "..."
        left_len = rendered_length(left_buf)
    padding = " " * max(0, terminalwidth - left_len - right_len)
    echo(
        f"{{savecursor}}{{bottombarcolor}}{{curpos:{terminal.lines()},0}}"
        f"{left_buf}{padding}{right_buf}{{/all}}{{restorecursor}}",
        wordwrap=False,
        end="",
        flush=True,
    )
    return True


__all__ = [
    "FragmentRegistry",
    "_LockedList",
    "default_registry",
    "registry_for",
    "set_context_for",
    "render_for",
    "set_active_registry",
    "reset_active_registry",
    "register_bottombar_fragment",
    "unregister_bottombar_fragment",
    "clear_bottombar_fragments",
    "setbottombar",
]
