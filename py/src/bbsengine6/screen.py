# screen.py - Canonical module for screen positioning and the bottombar
# back-compat surface area.
#
# @since 20260429 - Originally a thin re-export shim over bbsengine6.io.screen.
# @since 20260825 - Promoted to canonical. bbsengine6.io.screen is now a
# pre-registered alias for this module (see bbsengine6/io/__init__.py),
# so every access path (bbsengine6.screen, bbsengine6.io.screen,
# from-import, mock.patch, monkeypatch.setattr) lands on the same module
# object.
#
# The setarea / setbottombar / register_bottombar_fragment / etc. API
# here is a back-compat shim over bbsengine6.bottombar. New code should
# import directly from bbsengine6.bottombar.

from .io.echo import echo, echo_traceback, rendered_length
from .io import terminal
from . import bottombar as _bottombar_mod

import threading
import warnings
from typing import List


def _warn_shim_deprecated(name: str) -> None:
    """Emit a DeprecationWarning for back-compat shim entry points.

    The bottombar-fragment API (setarea, setbottombar,
    register_bottombar_fragment, unregister_bottombar_fragment,
    clear_bottombar_fragments, _render_bottombar_fragments,
    get_notification_status, init) is a back-compat shim. New code should
    import directly from bbsengine6.bottombar.
    """
    warnings.warn(
        f"bbsengine6.screen.{name} is a back-compat shim; "
        f"import from bbsengine6.bottombar instead.",
        DeprecationWarning,
        stacklevel=3,
    )


# Back-compat aliases onto the default registry's underlying list and lock.
# These are read by callers (and tests) that still touch
# `screen._bottombar_fragments` directly. They intentionally point at the
# *default* registry, not the ContextVar-routed one — door mode is the
# only mode that ever reads this alias. Per-connection routing goes
# through the shim functions below, which call
# `_bottombar_mod._resolve_registry()`.
_default_registry = _bottombar_mod.default_registry()
_bottombar_fragments = _default_registry.items
_bottombar_fragments_lock = _default_registry.lock

bottombarstack = []
_bottombarstack_lock = threading.Lock()


# ------------------------
# screen related functions
# ------------------------


def init(args=None, topmargin=1, bottommargin=1):
    """Initialize the screen scrolling region.

    Back-compat shim — call from bbsengine6.bottombar if you need it from
    new code. Emits DeprecationWarning.
    """
    _warn_shim_deprecated("init")
    echo("{f6:3}{cursorup:3}", end="", flush=True)
    h = terminal.lines() - bottommargin
    echo("{savecursor}", end="")
    echo("{decstbm:%s,%s}" % (topmargin, h), end="")
    echo("{restorecursor}", flush=True, end="")
    return


def updatebottombar(buf: str) -> None:
    """Render the bottom bar on the last terminal line without line wrapping."""
    echo(
        "{savecursor}{bottombarcolor}{curpos:%d,0}%s{restorecursor}"
        % (terminal.lines(), buf),
        wordwrap=False,
        end="",
        flush=True,
    )
    return


# ---- Fragment registry back-compat shims --------------------------------


def register_bottombar_fragment(item):
    """Back-compat shim — delegates to bbsengine6.bottombar.

    Deprecated: import bbsengine6.bottombar.register_bottombar_fragment
    directly. The shim will be removed in a future release.
    """
    _warn_shim_deprecated("register_bottombar_fragment")
    return _bottombar_mod.register_bottombar_fragment(item)


def unregister_bottombar_fragment(item):
    """Back-compat shim — delegates to bbsengine6.bottombar.

    Deprecated: import bbsengine6.bottombar.unregister_bottombar_fragment
    directly. The shim will be removed in a future release.
    """
    _warn_shim_deprecated("unregister_bottombar_fragment")
    return _bottombar_mod.unregister_bottombar_fragment(item)


def _render_bottombar_fragments(**kwargs) -> str:
    """Back-compat shim — delegates to bbsengine6.bottombar.

    Resolves the active registry through the bottombar ContextVar (BED
    per-connection override) or the named cache, falling back to the
    default registry. Calls `get_notification_status` (this module's
    function) so existing tests that
    `patch("bbsengine6.screen.get_notification_status")` keep working.

    Deprecated: import bbsengine6.bottombar.render_for(name) or
    bbsengine6.bottombar.default_registry().render() directly. The shim
    will be removed in a future release.
    """
    _warn_shim_deprecated("_render_bottombar_fragments")
    registry = _bottombar_mod._resolve_registry()

    merged = dict(kwargs)
    if registry.args is not None and "args" not in merged:
        merged["args"] = registry.args
    if registry.player is not None and "player" not in merged:
        merged["player"] = registry.player
    if registry.pool is not None and "pool" not in merged:
        merged["pool"] = registry.pool

    items_snapshot = registry.items.snapshot()

    parts: List[str] = []

    for item in items_snapshot:
        if callable(item):
            try:
                result = item(**merged)
                if result:
                    parts.append(str(result))
            except Exception:
                echo_traceback("bbsengine6.screen._render_bottombar_fragments:")
        elif item:
            parts.append(str(item))

    notification_status = get_notification_status(**kwargs)
    if notification_status:
        parts.insert(0, notification_status)

    return " | ".join(parts)


def setbottombar(left, right=None, **kwargs):
    """Back-compat shim — delegates to bbsengine6.bottombar.

    Preserves the original signature (left, right=None, **kwargs) used by
    callers like bbsengine6/console/lib.py and bbsengine6/demo_bottombar_stack.py
    that pass an explicit `right=...` callable or string. When `right` is
    None, the registered fragments are used (unchanged).

    Emits the result via the local `updatebottombar()` (not via
    bbsengine6.bottombar) so existing test code that does
    `patch("bbsengine6.screen.updatebottombar")` keeps working.

    Deprecated: call bbsengine6.bottombar.setbottombar(args, left) instead.
    The shim will be removed in a future release.
    """
    _warn_shim_deprecated("setbottombar")
    terminalwidth = terminal.width() - 2

    if callable(left) is True:
        left_buf = left(**kwargs)
    else:
        left_buf = left

    registry = _bottombar_mod._resolve_registry()
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
        left_buf = left_buf[: max_left_len - 5] + "..."
    padding = " " * (terminalwidth - left_len - right_len)
    updatebottombar("{bottombarcolor}%s%s%s{/all}" % (left_buf, padding, right_buf))
    return True


def setarea(left, right=None, **kwargs):
    """Render the bottom-bar / status line.

    Back-compat alias for ``setbottombar``. Re-exported for legacy
    zoidoffice callers (client.lib, staff.lib, project.lib,
    project/unclaim.py, etc.) and any test that patches
    ``bbsengine6.screen.setarea``. New code should call
    ``setbottombar`` directly.

    Emits DeprecationWarning on every call to nudge migration.

    Exceptions in the underlying ``setbottombar`` propagate — this is a
    direct delegation, not a swallowed-exception wrapper.
    """
    _warn_shim_deprecated("setarea")
    return setbottombar(left, right, **kwargs)


def get_notification_status(**kwargs) -> str:
    """Get notification status string for bottombar right side.

    Back-compat shim — delegates to bbsengine6.bottombar._get_notification_status.
    """
    _warn_shim_deprecated("get_notification_status")
    args = kwargs.get("args", None)
    pool = kwargs.get("pool", None)
    return _bottombar_mod._get_notification_status(args=args, pool=pool, **kwargs)


def clear_bottombar_fragments() -> None:
    """Back-compat shim — delegates to bbsengine6.bottombar.

    Deprecated: import bbsengine6.bottombar.clear_bottombar_fragments
    directly. The shim will be removed in a future release.
    """
    _warn_shim_deprecated("clear_bottombar_fragments")
    _bottombar_mod.clear_bottombar_fragments()


def popbottombar():
    with _bottombarstack_lock:
        if not bottombarstack:
            return
        buf = bottombarstack.pop()
    if buf != "":
        updatebottombar("{var:areacolor}%s{/all}" % buf)
    return


poparea = popbottombar


def updateprogress(iteration, total, fill="#"):
    """Back-compat shim — renders a text-mode progress bar on the bottombar."""
    terminalwidth = terminal.width()
    decimals = 0
    length = terminalwidth - 20
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = length * iteration // total
    bar = fill * filledLength + "." * (length - filledLength)
    buf = (
        "{var:labelcolor}Progress [{var:valuecolor}%3s%%{var:labelcolor}]: "
        "[%s]{/fgcolor}"
    ) % (percent, bar)
    updatebottombar(buf)
    return


__all__ = [
    "init",
    "updatebottombar",
    "setbottombar",
    "setarea",
    "popbottombar",
    "poparea",
    "get_notification_status",
    "updateprogress",
    "bottombarstack",
    "register_bottombar_fragment",
    "unregister_bottombar_fragment",
    "clear_bottombar_fragments",
    "_render_bottombar_fragments",
]
